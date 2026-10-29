"""High-stakes Bridge Timer round-transition race and state-machine tests.

Exercise actual production JS in Edge. Clock is deterministic, without
wall-clock sleeps and without editing timer.html. Every test uses a fresh
document to avoid leaked timeouts / state.
"""
from pathlib import Path
import os, shutil
from playwright.sync_api import sync_playwright

html=Path("timer.html").read_text(encoding="utf8").replace(
 "localStorage","transitionAuditStorage").replace(
 "</style></head><body>",
 """</style><script>const transitionAuditStorage={d:{},getItem(k){return this.d[k]??null},
 setItem(k,v){this.d[k]=v},removeItem(k){delete this.d[k]}};</script></head><body>""",1)

SETUP="""v=>{
 clearInterval(st.interval);st.interval=null;
 if(st.running)pause();
 window.__clock=500000;window.__wall=1000000;
 Object.defineProperty(performance,"now",{configurable:true,value:()=>window.__clock});
 Date.now=()=>window.__wall;
 Object.assign(s,{mode:v.mode,positions:v.positions,startPosition:1,
  hours:0,minutes:v.duration//60,seconds:v.duration%60,
  between:v.between,jumpRound:v.jumpRound||0,jumpDisplaySecs:v.jumpSecs||9,
  sound:false,boardProgressNotice:false,quickMessage:"",resumeTime:""});
 st.started=true;q4a(1,false);st.running=false;st.endAt=null;
 showTimer();render();
 window.__step=(ms)=>{__clock+=ms;__wall+=ms;tick()};
 window.__freeze=()=>{clearInterval(st.interval);st.interval=null};
 window.__state=()=>({pos:st.pos,phase:st.phase,running:st.running,
  remaining:st.remaining,started:st.started,
  endAt:st.endAt,roundDuration:st.roundDuration,breakDuration:st.breakDuration,
  roundBetween:st.roundBetween,longClockAtStart:st.longClockAtStart,
  undo:!!undoState});
}"""
# SETUP uses a JavaScript expression, not Python: build duration with integers
SETUP=SETUP.replace("v.duration//60","Math.floor(v.duration/60)")
SCENARIOS=[
 ("pairs_auto_break_chain",{"mode":"2","positions":3,"duration":120,"between":10}),
 ("pairs_auto_jump_chain",{"mode":"2","positions":3,"duration":120,"between":10,"jumpRound":1,"jumpSecs":9}),
 ("pairs_auto_without_break",{"mode":"2","positions":3,"duration":120,"between":0}),
 ("mp4_auto_round_end",{"mode":"4","positions":3,"duration":120,"between":0}),
 ("manual_before_deadline",{"mode":"2","positions":4,"duration":120,"between":10}),
 ("manual_after_auto_deadline",{"mode":"2","positions":4,"duration":120,"between":10}),
 ("mp4_manual_after_auto_deadline",{"mode":"4","positions":4,"duration":120,"between":0}),
 ("break_manual_after_auto_deadline",{"mode":"2","positions":4,"duration":120,"between":10}),
 ("paused_manual_transition",{"mode":"2","positions":4,"duration":120,"between":10}),
 ("undo_current_round",{"mode":"2","positions":4,"duration":120,"between":10}),
 ("undo_mp4_round_end",{"mode":"4","positions":4,"duration":120,"between":0}),
 ("settings_during_running",{"mode":"2","positions":4,"duration":120,"between":10}),
 ("overshoot_many_rounds",{"mode":"2","positions":6,"duration":120,"between":10}),
 ("final_pairs_end",{"mode":"2","positions":1,"duration":120,"between":10}),
 ("mp4_final_round_end",{"mode":"4","positions":1,"duration":120,"between":10}),
]
def active(page):
 page.evaluate("start();__freeze()")
def s(page):
 return page.evaluate("__state()")
def advance(page,ms):
 page.evaluate("__step",ms)
def expect(page,pos,phase,running=None):
 state=s(page)
 assert (state["pos"],state["phase"])==(pos,phase),state
 if running is not None:assert state["running"] is running,state
 return state
def run(name,page):
 if name=="pairs_auto_break_chain":
  active(page);advance(page,120000);expect(page,1,"break",True)
  advance(page,10000);expect(page,2,"round",True)
  advance(page,120000);expect(page,2,"break",True)
  advance(page,10000);expect(page,3,"round",True)
  advance(page,120000);expect(page,3,"ended",False)
 elif name=="pairs_auto_jump_chain":
  active(page);advance(page,120000);expect(page,1,"jump",True)
  advance(page,9000);expect(page,1,"break",True)
  advance(page,10000);expect(page,2,"round",True)
 elif name=="pairs_auto_without_break":
  active(page);advance(page,120000);expect(page,2,"round",True)
  advance(page,120000);expect(page,3,"round",True)
  advance(page,120000);expect(page,3,"ended",False)
 elif name=="mp4_auto_round_end":
  active(page);advance(page,120000);expect(page,1,"roundEnd",False)
  advance(page,60000);expect(page,1,"roundEnd",False)
  page.evaluate("next();__freeze()");expect(page,2,"round",True)
 elif name=="manual_before_deadline":
  active(page);advance(page,119999);expect(page,1,"round",True)
  page.evaluate("next();__freeze()");expect(page,2,"round",True)
  advance(page,20);expect(page,2,"round",True)
 elif name=="manual_after_auto_deadline":
  active(page);advance(page,120000);expect(page,1,"break",True)
  page.evaluate("next();__freeze()")
  # An event-loop race at zero must not count AUTO and MANUAL advance twice.
  expect(page,1,"break",True)
  advance(page,250)
  page.evaluate("next();__freeze()")
  expect(page,2,"round",True) # explicit deliberate skip later is still allowed
 elif name=="mp4_manual_after_auto_deadline":
  active(page);advance(page,120000);expect(page,1,"roundEnd",False)
  page.evaluate("next();__freeze()")
  expect(page,1,"roundEnd",False)
  advance(page,250)
  page.evaluate("next();__freeze()")
  expect(page,2,"round",True)
 elif name=="break_manual_after_auto_deadline":
  active(page);advance(page,120000);expect(page,1,"break",True)
  advance(page,10000);expect(page,2,"round",True)
  page.evaluate("next();__freeze()")
  expect(page,2,"round",True)
  advance(page,250)
  page.evaluate("next();__freeze()")
  expect(page,3,"round",True)
 elif name=="paused_manual_transition":
  page.evaluate("next()");expect(page,2,"round",False)
  page.evaluate("previousPosition()");expect(page,1,"round",False)
  page.evaluate("next()");expect(page,2,"round",False)
  assert s(page)["endAt"] is None,s(page)
 elif name=="undo_current_round":
  active(page);advance(page,25000);before=s(page)
  page.evaluate("next();__freeze()");expect(page,2,"round",True)
  page.evaluate("q4d();__freeze()");state=expect(page,1,"round",True)
  assert abs(state["remaining"]-before["remaining"])<1.1,(before,state)
 elif name=="undo_mp4_round_end":
  active(page);advance(page,120000);expect(page,1,"roundEnd",False)
  # Explicit user next when no race (unlike the zero-time case).
  advance(page,250)
  page.evaluate("next();__freeze()");expect(page,2,"round",True)
  page.evaluate("q4d()");expect(page,1,"roundEnd",False)
 elif name=="settings_during_running":
  active(page);advance(page,40000);before=s(page)
  page.evaluate("""()=>{
   showSettings(false);
   s.minutes=9;s.seconds=0;s.between=50;fill();apply();
   __freeze();
  }""")
  after=s(page)
  assert (after["pos"],after["phase"],after["running"])==(1,"round",True),after
  assert abs(after["remaining"]-before["remaining"])<1,(before,after)
  assert after["roundDuration"]==120,(before,after)
  page.evaluate("next();__freeze()")
  expect(page,2,"round",True)
  assert s(page)["roundDuration"]==540,s(page)
 elif name=="overshoot_many_rounds":
  active(page)
  advance(page,120000+10000+120000+10000+13000)
  state=expect(page,3,"round",True)
  assert abs(state["remaining"]-107)<.01,state
  advance(page,120000*30)
  expect(page,6,"ended",False)
 elif name=="final_pairs_end":
  active(page);advance(page,120000);expect(page,1,"ended",False)
  page.evaluate("next()");expect(page,1,"ended",False)
 elif name=="mp4_final_round_end":
  active(page);advance(page,120000);expect(page,1,"roundEnd",False)
  advance(page,250);page.evaluate("next()")
  expect(page,1,"roundEnd",False)

with sync_playwright() as p:
 if os.name=="nt":browser=p.chromium.launch(channel="msedge",headless=True)
 else:browser=p.chromium.launch(executable_path=shutil.which("chromium") or shutil.which("chromium-browser"),
                               headless=True,args=["--no-sandbox"])
 for name,params in SCENARIOS:
  page=browser.new_page(viewport={"width":960,"height":620})
  errors=[]
  page.on("pageerror",lambda err:errors.append(str(err)))
  try:
   page.set_content(html,wait_until="domcontentloaded")
   page.wait_for_function("typeof recoveryArmed!=='undefined'&&recoveryArmed")
   page.evaluate(SETUP,params)
   run(name,page)
   assert not errors,(name,errors)
   print("PASS transition:",name,flush=True)
  except Exception as e:
   raise AssertionError(f"Transition {name} failed: {e}") from e
  finally:
   page.close()
 browser.close()
print(f"Transitions E2E: {len(SCENARIOS)} scenarios passed")
