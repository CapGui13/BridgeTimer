"""Web Audio reliability tests: exact two-tone cadence, faults and 500 alerts.

All tests run the shipping JS in Edge with a programmable AudioContext:
they verify the requests and scheduling, NOT physical speaker audibility.
"""
from pathlib import Path
import os,shutil
from playwright.sync_api import sync_playwright

html=Path("timer.html").read_text(encoding="utf8")
html=html.replace("localStorage","audioAuditStorage").replace(
 "</style></head><body>",
 """</style><script>const audioAuditStorage={d:{},getItem(k){return this.d[k]??null},
 setItem(k,v){this.d[k]=v},removeItem(k){delete this.d[k]}};</script></head><body>""",1)
html=html.replace("<script>", """<script>
 window.__deviceHandlers={};
 try{Object.defineProperty(navigator,"mediaDevices",{configurable:true,value:{
 addEventListener:(type,cb)=>{window.__deviceHandlers[type]=cb;}
 }})}catch(e){}
 </script><script>""",1)

INSTALL="""() => {
 window.__record={starts:[],stops:[],freqs:[],gains:[],resumes:0,contexts:0,closes:0};
 window.__failResumes=0;
 window.AudioContext=class {
  constructor(){__record.contexts++;this.state='suspended';this.currentTime=14;this.destination={}}
  resume(){
   __record.resumes++;
   if(__failResumes>0){__failResumes--;return Promise.reject(new Error("audio interrupted"))}
   this.state='running';return Promise.resolve();
  }
  close(){__record.closes++;this.state='closed';return Promise.resolve()}
  addEventListener(){}
  createOscillator(){
   const node={frequency:{value:0},connect(){},disconnect(){},onended:null,
    start(t){__record.starts.push(t);__record.freqs.push(this.frequency.value)},
    stop(t){__record.stops.push(t)}};
   return node;
  }
  createGain(){return {gain:{
    setValueAtTime(v,t){__record.gains.push([v,t])},
    exponentialRampToValueAtTime(){}
   },connect(){},disconnect(){}}}
 };
 window.webkitAudioContext=undefined;
 audioCtx=null;audioContextEpoch=0;
 s.sound=true;
}"""

with sync_playwright() as pw:
 if os.name=="nt":browser=pw.chromium.launch(channel="msedge",headless=True)
 else:browser=pw.chromium.launch(executable_path=shutil.which("chromium") or shutil.which("chromium-browser"),
                                  headless=True,args=["--no-sandbox"])
 page=browser.new_page(viewport={"width":960,"height":680})
 errors=[]
 page.on("pageerror",lambda e:errors.append(str(e)))
 page.set_content(html,wait_until="domcontentloaded")
 page.wait_for_function("typeof recoveryArmed!=='undefined' && recoveryArmed")
 page.evaluate(INSTALL)

 # One round-end sound is EXACTLY the old two pitches, durations and
 # 280-ms overlap, scheduled on the same AudioContext time base.
 assert page.evaluate("q1a()") is True
 metrics=page.evaluate("__record")
 assert metrics["freqs"]==[880,1100],metrics
 assert len(metrics["starts"])==2
 assert abs(metrics["starts"][1]-metrics["starts"][0]-.28)<1e-6,metrics
 assert abs(metrics["stops"][0]-metrics["starts"][0]-.35)<1e-6,metrics
 assert abs(metrics["stops"][1]-metrics["starts"][1]-.35)<1e-6,metrics
 assert all(abs(g[0]-.07)<1e-7 for g in metrics["gains"]),metrics
 assert metrics["resumes"]==1,metrics

 # Muting the tournament suppresses real alerts. Keep the internal
 # audio initialization/recovery callable; the manual Test son UI is removed.
 page.evaluate("s.sound=false")
 assert page.evaluate("q1a()") is False
 assert page.evaluate("q14()") is True
 metrics=page.evaluate("__record")
 assert metrics["freqs"]==[880,1100,880,1100],metrics
 # Removing the manual test button must not remove the sound option.
 assert page.locator("#testSoundBtn").count()==0
 assert page.locator("#sound").count()==1
 page.evaluate("s.sound=true")

 # Prove a stream of 500 independent alerts doesn't multiply oscillators
 # or create 500 AudioContexts.
 page.evaluate("""async () => {
  for(let i=0;i<500;i++){
   const played=await q1a();if(!played)throw Error("Dropped alert "+i)
  }
 }""")
 metrics=page.evaluate("__record")
 assert len(metrics["freqs"])==1004,metrics
 assert metrics["contexts"]==1,metrics
 assert metrics["resumes"]==1,metrics

 # Device reroute: forget the cached context WITHOUT playing another
 # alert, and create a fresh one when the next actual alert/test occurs.
 count=len(metrics["freqs"])
 assert page.evaluate("typeof window.__deviceHandlers.devicechange")== "function"
 page.evaluate("__deviceHandlers.devicechange()")
 assert len(page.evaluate("__record.freqs"))==count
 assert page.evaluate("q1a()") is True
 metrics=page.evaluate("__record")
 assert metrics["contexts"]==2 and len(metrics["freqs"])==count+2,metrics

 # Force a closed or interrupted context. A failing resume must cause a
 # single fresh context and precisely one two-tone pattern, never a replay.
 page.evaluate("audioDropContext();window.__failResumes=1")
 assert page.evaluate("q1a()") is True
 metrics=page.evaluate("__record")
 assert len(metrics["freqs"])==count+4,metrics
 assert metrics["contexts"]>=4,metrics

 # A slow / blocked resume must NOT produce an alarm long after the
 # relevant timer transition has already ended.
 page.evaluate("""() => {
  audioDropContext();
  window.AudioContext=class {
   constructor(){this.state='suspended';this.currentTime=3;this.destination={}}
   resume(){return new Promise(()=>{})}
   close(){this.state='closed';return Promise.resolve()}
  };
 }""")
 assert page.evaluate("q1a()") is False
 assert len(page.evaluate("__record.freqs"))==count+4
 # Hardware missing: no uncaught error, initialization reports failure.
 page.evaluate("audioDropContext();window.AudioContext=undefined;window.webkitAudioContext=undefined")
 assert page.evaluate("q1a()") is False
 assert page.evaluate("q14()") is False
 assert not errors,errors
 page.close()
 browser.close()
print("Audio robustness OK: exact 880/1100 Hz, 280-ms cadence, 500 alerts, device reroute, retry and delayed-resume suppression")
