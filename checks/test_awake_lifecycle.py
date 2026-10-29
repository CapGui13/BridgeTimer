"""Bridge Timer anti-sleep regression: pauses, round transitions, recovery, errors."""
import os,shutil
from pathlib import Path
from playwright.sync_api import sync_playwright

html=Path(__file__).resolve().parents[1].joinpath("timer.html").read_text(encoding="utf8")
html=html.replace("localStorage","bridgeAuditStorage").replace(
 "</style></head><body>",
 """</style><script>const bridgeAuditStorage={data:{},
 getItem(k){return this.data[k]??null},setItem(k,v){this.data[k]=v},
 removeItem(k){delete this.data[k]}};</script></head><body>""",1)

with sync_playwright() as pw:
 if os.name=="nt": browser=pw.chromium.launch(channel="msedge",headless=True)
 else: browser=pw.chromium.launch(executable_path=shutil.which("chromium") or shutil.which("chromium-browser"),headless=True,args=["--no-sandbox"])
 for mode in ("4","2"):
  page=browser.new_page(viewport={"width":1280,"height":720})
  errors=[]
  page.on("pageerror",lambda e:errors.append(str(e)))
  page.set_content(html,wait_until="domcontentloaded")
  page.wait_for_function("typeof recoveryArmed!=='undefined' && recoveryArmed")
  page.evaluate("""mode=>{
    window.__awakeHistory=[];
    window.nativeSetAwake=async (on,serial)=>{
      __awakeHistory.push({on,serial});return true;
    };
    Object.assign(s,{mode,positions:3,between:15,minutes:1,seconds:0,hours:0,sound:false});
    st.started=true;st.running=false;q4a(1,false);showTimer();
  }""",mode)
  page.evaluate("start()")
  page.wait_for_function("__awakeHistory.length >= 1")
  page.evaluate("pause()")
  page.wait_for_function("__awakeHistory.length >= 2")
  assert all(x["on"] for x in page.evaluate("__awakeHistory")), ("Pause must keep anti-sleep",mode)
  page.evaluate("showSettings(false);q25(true);q25(false);showTimer()")
  assert all(x["on"] for x in page.evaluate("__awakeHistory")), ("Settings must keep anti-sleep",mode)
  page.evaluate("start();pause()")
  assert all(x["on"] for x in page.evaluate("__awakeHistory")), ("Resume must keep anti-sleep",mode)
  # End of an MP4 round is an active tournament; end of a Pairs event isn't.
  page.evaluate("""mode=>{
    st.running=false;st.phase="round";st.pos=mode==="2"?s.positions:1;
    qe();
  }""",mode)
  latest=page.evaluate("__awakeHistory.at(-1)")
  assert latest["on"] is (mode=="4"), ("round end / tournament end",mode,latest)
  page.evaluate("q22()")
  assert page.evaluate("__awakeHistory.at(-1).on") is False, ("Stop must release",mode)
  assert not errors,errors
  page.close()

 # If Windows refuses the request, the page remains functional and
 # the Web Wake Lock API (when provided) can still be acquired/released.
 page=browser.new_page()
 page.set_content(html,wait_until="domcontentloaded")
 page.wait_for_function("typeof recoveryArmed!=='undefined' && recoveryArmed")
 page.evaluate("""()=>{
  window.nativeSetAwake=async ()=>{throw new Error("simulated native failure")};
  window.__webLocks=[];
  Object.defineProperty(navigator,"wakeLock",{configurable:true,value:{
   request:async()=>{const lock={released:false,release:async()=>{lock.released=true},
     addEventListener(){}};__webLocks.push(lock);return lock}
  }});
  st.started=true;st.phase="round";st.running=false;
 }""")
 page.evaluate("q31()")
 page.wait_for_function("__webLocks.length >= 1")
 page.evaluate("st.started=false;q32()")
 page.wait_for_function("__webLocks[0].released")
 assert page.evaluate("!tournamentNeedsAwake()")
 page.close()
 browser.close()
print("Anti-sleep lifecycle: Pairs and MP4, pause, settings, stop, end, native failure and wakeLock fallback OK")
