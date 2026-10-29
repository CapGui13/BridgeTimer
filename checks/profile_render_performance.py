"""Measure a simulated four-hour tournament and rendering costs in Edge.

This is a measurement, not a hardware-load or sound test. Runs an accelerated
four-hour clock and then profiles repaint throughput and mini-frame DOM growth.
Reports numbers and rejects only logical failures/leaked iframe elements.
"""
import os,shutil,json
from pathlib import Path
from playwright.sync_api import sync_playwright

src=Path("timer.html").read_text(encoding="utf8")
src=src.replace("localStorage","auditStorage").replace("</style></head><body>",
 """</style><script>const auditStorage={d:{},getItem(k){return this.d[k]??null},
 setItem(k,v){this.d[k]=v},removeItem(k){delete this.d[k]}};</script></head><body>""",1)

with sync_playwright() as pw:
 browser=pw.chromium.launch(channel="msedge",headless=True) if os.name=="nt" else pw.chromium.launch(
  executable_path=shutil.which("chromium") or shutil.which("chromium-browser"),headless=True,args=["--no-sandbox"])
 page=browser.new_page(viewport={"width":1650,"height":928})
 errors=[]
 page.on("pageerror",lambda e:errors.append(str(e)))
 page.set_content(src,wait_until="domcontentloaded")
 page.wait_for_function("typeof recoveryArmed!=='undefined'&&recoveryArmed")
 result=page.evaluate("""() => {
  Object.assign(s,{mode:"4",hours:4,minutes:0,seconds:0,
    positions:6,between:0,boardProgressNotice:false,sound:false});
  fill();st.started=true;q4a(1,false);showTimer();
  // Simulated performance clock: time advances in ten-second steps without
  // sleeping for four hours. The actual production tick()/render() is called.
  window.__mon=50000;
  Object.defineProperty(performance,"now",{configurable:true,value:()=>__mon});
  start();clearInterval(st.interval);st.interval=null;
  for(let i=0;i<1440;i++){__mon+=10000;tick()}
  const phase=st.phase,remaining=st.remaining,pos=st.pos;
  delete performance.now;
  let begin=performance.now();
  for(let i=0;i<200;i++)render();
  const timerRenderMs=performance.now()-begin;
  showSettings(false);
  const mini=document.querySelector("#miniTimer");
  const frameCountBefore=mini.querySelectorAll("iframe").length;
  begin=performance.now();
  for(let i=0;i<300;i++)render();
  const settingsRenderMs=performance.now()-begin;
  const frameCountAfter=mini.querySelectorAll("iframe").length;
  return {phase,remaining,pos,timerRenderMs,settingsRenderMs,
   frameCountBefore,frameCountAfter,
   jsHeapUsed:performance.memory?.usedJSHeapSize??null};
 }""")
 assert result["phase"]=="roundEnd" and result["remaining"]==0 and result["pos"]==1,result
 assert result["timerRenderMs"]>=0 and result["settingsRenderMs"]>=0,result
 assert result["frameCountAfter"]==result["frameCountBefore"] and result["frameCountAfter"]<=1,result
 assert not errors,errors
 Path("render-performance.json").write_text(json.dumps(result,indent=2),encoding="utf8")
 print("Simulated 4-hour session and render profile: "+json.dumps(result,ensure_ascii=False))
 page.close();browser.close()
