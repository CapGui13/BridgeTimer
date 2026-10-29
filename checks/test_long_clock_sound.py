"""Test real delivered countdown and audio code with a controlled monotonic clock.

This file only tests the application. It MUST NOT rewrite timer.html.
Clock jumps and audio calls are injected in the disposable browser page.
"""
from pathlib import Path
import os
import shutil
from playwright.sync_api import sync_playwright

html=(Path(__file__).resolve().parents[1]/"timer.html").read_text(encoding="utf-8")
html=html.replace("localStorage","bridgeAuditStorage").replace(
 "</style></head><body>", """</style><script>const bridgeAuditStorage={data:{},
 getItem(k){return this.data[k]??null},setItem(k,v){this.data[k]=v},
 removeItem(k){delete this.data[k]}};</script></head><body>""",1)

SETUP="""() => {
 if(st.running)pause();clearInterval(st.interval);st.interval=null;
 st.started=true;showTimer();
 Object.assign(s,{mode:'4',positions:2,hours:4,minutes:0,seconds:0,
   between:0,sound:false,warnEnabled:false,boardProgressNotice:false});
 q4a(1,false);st.running=false;st.endAt=null;render();
 window.__simMon=10000;window.__simWall=1000000;
 Object.defineProperty(performance,'now',{configurable:true,value:()=>__simMon});
 Date.now=()=>__simWall;
 window.__advance=(ms,wallMs=ms)=>{
   __simMon+=ms;__simWall+=wallMs;tick()
 };
 window.__state=()=>({phase:st.phase,pos:st.pos,
   remaining:st.remaining,running:st.running,endAt:st.endAt});
}"""
MOCK="""() => {
 window.__audioLog={freqs:[],stops:[],gains:[],resumes:0};
 window.AudioContext=class {
   constructor(){this.state='suspended';this.currentTime=12;this.destination={}}
   resume(){__audioLog.resumes++;this.state='running';return Promise.resolve()}
   createOscillator(){return {
     frequency:{value:0},connect(){},disconnect(){},
     start(){__audioLog.freqs.push(this.frequency.value)},
     stop(t){__audioLog.stops.push(t)}
   }}
   createGain(){return {gain:{
     setValueAtTime(v){__audioLog.gains.push(v)},
     exponentialRampToValueAtTime(){}
   },connect(){},disconnect(){}}}
 };
 audioCtx=null;
}"""

def four_hours(p):
 p.evaluate(SETUP)
 p.evaluate("start();clearInterval(st.interval);st.interval=null")
 for milliseconds,remaining in [(3600000,10800),(7200000,3600),(3599000,1)]:
  p.evaluate("__advance(arguments[0])", milliseconds) if False else p.evaluate("ms=>__advance(ms)",milliseconds)
  a=p.evaluate("__state()")
  assert a["running"] and abs(a["remaining"]-remaining)<.01,a
 p.evaluate("__advance(1000)")
 a=p.evaluate("__state()")
 assert a["phase"]=="roundEnd" and a["remaining"]==0 and not a["running"],a

def pause_long_gap(p):
 p.evaluate(SETUP)
 p.evaluate("start();clearInterval(st.interval);st.interval=null;__advance(4800000);pause()")
 a=p.evaluate("__state()")
 assert not a["running"] and abs(a["remaining"]-9600)<.01,a
 p.evaluate("__advance(12*3600000)")
 b=p.evaluate("__state()")
 assert b["remaining"]==a["remaining"],b
 p.evaluate("start();clearInterval(st.interval);st.interval=null;__advance(3600000)")
 c=p.evaluate("__state()")
 assert c["running"] and abs(c["remaining"]-6000)<.01,c

def suspension_catchup(p):
 p.evaluate(SETUP)
 p.evaluate("""Object.assign(s,{mode:'2',positions:5,hours:0,minutes:2,
 seconds:0,between:10,jumpRound:0});
 q4a(1,false);start();clearInterval(st.interval);st.interval=null;
 __advance(2*120000+2*10000+125000)""")
 a=p.evaluate("__state()")
 assert a["pos"]==3 and a["phase"]=="break" and abs(a["remaining"]-5)<.01,a

def wall_clock_changes(p):
 p.evaluate(SETUP)
 p.evaluate("start();clearInterval(st.interval);st.interval=null;__advance(120000,20*3600000)")
 a=p.evaluate("__state()")
 assert a["running"] and abs(a["remaining"]-14280)<.01,a
 p.evaluate("__advance(60000,-25*3600000)")
 b=p.evaluate("__state()")
 assert b["running"] and abs(b["remaining"]-14220)<.01,b

def second_alignment(p):
 p.evaluate(SETUP)
 p.evaluate("st.remaining=120;__simWall=1000450;start();clearInterval(st.interval);st.interval=null")
 a=p.evaluate("__state()")
 assert 119.54<a["remaining"]<119.56,a
 p.evaluate("__advance(119550)")
 assert p.evaluate("__state().phase")=="roundEnd"

def muted(p):
 p.evaluate(MOCK)
 p.evaluate("s.sound=false;beep(880);q1a()")
 p.wait_for_timeout(330)
 a=p.evaluate("__audioLog")
 assert a["freqs"]==[] and a["resumes"]==0,a

def double_beep(p):
 p.evaluate(MOCK)
 p.evaluate("s.sound=true;q1a()")
 p.wait_for_timeout(340)
 a=p.evaluate("__audioLog")
 assert a["freqs"]==[880,1100] and len(a["stops"])==2 and a["resumes"]==1,a

def forced_preview(p):
 p.evaluate(MOCK)
 p.evaluate("s.sound=false;q14()")
 p.wait_for_timeout(340)
 a=p.evaluate("__audioLog")
 assert a["freqs"]==[880,1100] and len(a["stops"])==2,a

def missing_audio_device(p):
 p.evaluate("window.AudioContext=undefined;window.webkitAudioContext=undefined;audioCtx=null;s.sound=true;beep(880);q1a()")
 p.wait_for_timeout(320)

tests=[
 ("four_hour_countdown",four_hours),
 ("pause_long_gap",pause_long_gap),
 ("suspended_browser_catchup",suspension_catchup),
 ("wall_clock_changes",wall_clock_changes),
 ("second_alignment",second_alignment),
 ("audio_disabled",muted),
 ("double_beep",double_beep),
 ("preview_while_muted",forced_preview),
 ("audio_unavailable",missing_audio_device)
]
with sync_playwright() as pw:
 if os.name=="nt":
  browser=pw.chromium.launch(channel="msedge",headless=True)
 else:
  executable=shutil.which("chromium") or shutil.which("chromium-browser")
  browser=pw.chromium.launch(executable_path=executable,headless=True,args=["--no-sandbox"])
 for name,test in tests:
  page=browser.new_page(viewport={"width":812,"height":490})
  errors=[]
  page.on("pageerror",lambda e: errors.append(str(e)))
  try:
   page.set_content(html,wait_until="domcontentloaded")
   page.wait_for_function("typeof st!=='undefined'&&typeof q4a==='function'")
   test(page)
   assert not errors,f"{name}: JavaScript errors {errors}"
  except Exception as e:
   raise AssertionError(f"Bridge Timer long-run/audio test {name}: {e}") from e
  finally:
   page.close()
 browser.close()
print("Long-running clock/audio audit passed: 9 / 9 tests")
