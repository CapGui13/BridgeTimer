"""Regression: fullscreen Timer controls auto-hide after exactly 4 seconds.
Includes Debug, returning from Settings, keyboard wake, and inert test previews.
The approved 1600x900 timer, digits and footer must not be resized.
"""
from pathlib import Path
import os, shutil
from playwright.sync_api import sync_playwright

html=(Path(__file__).resolve().parents[1]/"timer.html").read_text(encoding="utf-8")
html=html.replace("localStorage","bridgeAuditStorage").replace(
 "</style></head><body>",
 """</style><script>const bridgeAuditStorage={data:{},getItem(k){return this.data[k]??null},
 setItem(k,v){this.data[k]=v},removeItem(k){delete this.data[k]}};
 </script></head><body>""",1)

def controls(page):
 return page.evaluate("""()=>{
  const top=document.querySelector('#timer .topBtns');
  const bottom=document.querySelector('#timer .controls');
  const report=e=>({opacity:Number(getComputedStyle(e).opacity),
    visibility:getComputedStyle(e).visibility,
    pointer:getComputedStyle(e).pointerEvents,inert:e.inert});
  return {shown:document.body.classList.contains('showControls'),
    fullscreen:document.body.classList.contains('fs'),
    top:report(top),bottom:report(bottom),bottomBandInert:document.querySelector('#timer .bottom').inert,preview:document.querySelector('#timer').classList.contains('spm')};
 }""")

def prepare(page,debug=False):
 page.evaluate("""debug=>{
   if(debug)document.body.classList.add('debugMode');
   st.started=true;st.phase='round';st.running=false;
   st.remaining=1200;st.pos=1;st.roundDuration=1800;
   showTimer();q25(true);
 }""",debug)

with sync_playwright() as pw:
 if os.name=="nt":
  browser=pw.chromium.launch(channel="msedge",headless=True)
 else:
  browser=pw.chromium.launch(executable_path=shutil.which("chromium") or shutil.which("chromium-browser"),
    headless=True,args=["--no-sandbox"])
 for debug in (False,True):
  page=browser.new_page(viewport={"width":1600,"height":900})
  errors=[]
  page.on("pageerror",lambda exc:errors.append(str(exc)))
  page.clock.install()
  page.set_content(html,wait_until="domcontentloaded")
  prepare(page,debug)
  assert controls(page)["shown"],("fullscreen must reveal controls on entry",debug)
  # Leave a 500-ms margin against host-side evaluation latency:
  # Playwright's installed clock still advances while Python inspects the page.
  page.clock.fast_forward(3500)
  before=controls(page)
  assert before["shown"] and before["top"]["pointer"]=="auto" and before["bottom"]["pointer"]=="auto" and before["top"]["visibility"]=="visible" and before["bottom"]["visibility"]=="visible",(
    "controls hidden before 4 seconds",debug,before)
  page.clock.fast_forward(700)
  hidden=controls(page)
  assert not hidden["shown"] and hidden["top"]["pointer"]=="none" and hidden["bottom"]["pointer"]=="none",(
    "controls did not hide at 4 seconds",debug,hidden)
  page.keyboard.press("Shift")
  awake=controls(page)
  assert awake["shown"] and awake["top"]["pointer"]=="auto" and awake["top"]["visibility"]=="visible",("keyboard action must reveal controls",debug,awake)
  page.clock.fast_forward(4050)
  assert not controls(page)["shown"],("keyboard reset must expire 4s later",debug)
  page.mouse.move(500,320)
  assert controls(page)["shown"],("mouse movement must reveal controls",debug)
  page.clock.fast_forward(4050)
  assert not controls(page)["shown"],("mouse movement reset must expire 4s later",debug)
  # Returning to the real timer from Settings starts a fresh four-second window.
  page.evaluate("showSettings(false);showTimer()")
  assert controls(page)["shown"],("returning from Settings did not restore controls",debug)
  page.clock.fast_forward(4100)
  assert not controls(page)["shown"],("returned timer controls did not hide",debug)
  # Normal windowed mode keeps the familiar always-visible controls.
  page.evaluate("q25(false)")
  in_window=controls(page)
  assert not in_window["fullscreen"] and in_window["top"]["pointer"]=="auto",(
   "windowed controls must remain available",debug,in_window)
  if debug:
   # Test screens keep the header/bottom visible but inactive.
   page.evaluate("showSettings(false);q25(true);_osp();_ssp('board')")
   preview=controls(page)
   assert preview["preview"] and preview["top"]["inert"] and preview["bottomBandInert"] and preview["top"]["visibility"]=="visible" and preview["bottom"]["visibility"]=="visible",preview
   assert preview["top"]["pointer"]=="none" and preview["bottom"]["pointer"]=="none",preview
  assert not errors,(debug,errors)
  page.close()
 # Real Chromium/Edge paint check: the buttons must fade smoothly without layout reflow.
 page=browser.new_page(viewport={"width":1600,"height":900})
 page.set_content(html,wait_until="domcontentloaded")
 prepare(page,True)
 page.wait_for_timeout(4500)
 after=controls(page)
 assert not after["shown"] and after["top"]["visibility"]=="hidden" and after["bottom"]["visibility"]=="hidden",(
  "4-second idle must visually remove buttons, even with Debug enabled",after)
 page.mouse.move(220,340)
 page.wait_for_timeout(270)
 after=controls(page)
 assert after["shown"] and after["top"]["visibility"]=="visible" and after["bottom"]["visibility"]=="visible",(
  "mouse motion must visually restore both rows of buttons",after)
 page.close()
 # Regression against a visible shift when commands are hidden and shown.
 # The real screen geometry must remain fixed across both changes,
 # including the digits, title, notices, header and footer.
 def geometry(page):
  return page.evaluate("""()=>{
   const sels=['#timer .topBtns','#timer .controls','#timer .top',
     '#timer .bottom','#clock','#status','#msg','#localTime','#round'];
   const result={};
   for(const sel of sels){
    const e=document.querySelector(sel),r=e.getBoundingClientRect(),cs=getComputedStyle(e);
    result[sel]={box:[r.x,r.y,r.width,r.height],transform:cs.transform,
      visibility:cs.visibility,opacity:parseFloat(cs.opacity),transition:cs.transitionProperty};
   }
   return result;
  }""")
 for viewport in ((960,720),(1600,900),(1650,928)):
  for long_clock in (False,True):
   page=browser.new_page(viewport={"width":viewport[0],"height":viewport[1]})
   errors=[]
   page.on("pageerror",lambda e:errors.append(str(e)))
   page.set_content(html,wait_until="domcontentloaded")
   page.evaluate("""longClock=>{
    Object.assign(s,{eventName:'Cucksleague - Final',mode:'2',positions:13,
      hours:longClock?1:0,minutes:longClock?0:14,seconds:28});
    Object.assign(st,{started:true,running:false,phase:'round',
      remaining:longClock?3888:868,pos:1,roundDuration:longClock?5400:1800,
      roundBoards:8,roundBoardDuration:225,longClockAtStart:longClock});
    showTimer();q25(true);render();
   }""",long_clock)
   page.wait_for_timeout(350)
   baseline=geometry(page)
   control=baseline["#timer .controls"]
   assert "opacity" in control["transition"] and "transform" not in control["transition"],(
     viewport,long_clock,"Bottom controls must fade without sliding",control)
   assert "opacity" in baseline["#timer .topBtns"]["transition"] and "transform" not in baseline["#timer .topBtns"]["transition"],(
     viewport,long_clock,"Header controls must fade without sliding",baseline["#timer .topBtns"])
   for shown in (False,True):
    page.evaluate("value=>document.body.classList.toggle('showControls',value)",shown)
    for interval in (70,190):
     page.wait_for_timeout(interval)
     measured=geometry(page)
     if interval==70:
      for selector in ("#timer .controls","#timer .topBtns"):
       assert .01<measured[selector]["opacity"]<.99,(
        viewport,long_clock,shown,selector,"Opacity must be partway through its fade",measured[selector])
     for selector,expected in baseline.items():
      current=measured[selector]
      assert current["transform"]==expected["transform"],(
       viewport,long_clock,shown,interval,selector,"Transform jumped",expected,current)
      for coordinate,(a,b) in enumerate(zip(current["box"],expected["box"])):
       # The wall clock's text changes every second, so its intrinsic
       # width can fluctuate independently of fading buttons. Its anchor,
       # font height and the positions of all the OTHER elements cannot.
       if selector=="#localTime" and coordinate==2:continue
       assert abs(a-b)<.25,(
        viewport,long_clock,shown,interval,selector,"Position or size jumped",expected,current)
    assert measured["#timer .topBtns"]["visibility"]==("visible" if shown else "hidden")
    assert measured["#timer .controls"]["visibility"]==("visible" if shown else "hidden")
   # TOUR 9 -> TOUR 10 widens the right-hand label. Controls must not shift.
   page.evaluate("st.pos=10;render()")
   shifted=geometry(page)
   for selector in ("#timer .controls","#timer .topBtns"):
    assert shifted[selector]["box"]==baseline[selector]["box"],(
     viewport,long_clock,selector,"Round number changed button position",
     baseline[selector],shifted[selector])
   assert not errors,(viewport,long_clock,errors)
   page.close()
 browser.close()
print("4-second auto-hide, smooth opacity-only fade, stationary controls and Debug OK")
