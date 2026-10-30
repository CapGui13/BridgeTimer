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
  page.clock.fast_forward(3900)
  before=controls(page)
  assert before["shown"] and before["top"]["pointer"]=="auto" and before["bottom"]["pointer"]=="auto",(
    "controls hidden before 4 seconds",debug,before)
  page.clock.fast_forward(150)
  hidden=controls(page)
  assert not hidden["shown"] and hidden["top"]["pointer"]=="none" and hidden["bottom"]["pointer"]=="none",(
    "controls did not hide at 4 seconds",debug,hidden)
  page.keyboard.press("Shift")
  awake=controls(page)
  assert awake["shown"] and awake["top"]["pointer"]=="auto",("keyboard action must reveal controls",debug,awake)
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
   assert preview["preview"] and preview["top"]["inert"] and preview["bottomBandInert"],preview
   assert preview["top"]["pointer"]=="none" and preview["bottom"]["pointer"]=="none",preview
  assert not errors,(debug,errors)
  page.close()
 # Real Chromium/Edge paint check: opacity transition must ACTUALLY finish.
 page=browser.new_page(viewport={"width":1600,"height":900})
 page.set_content(html,wait_until="domcontentloaded")
 prepare(page,True)
 page.wait_for_timeout(4500)
 after=controls(page)
 assert not after["shown"] and after["top"]["opacity"]<.05 and after["bottom"]["opacity"]<.05,(
  "4-second idle must visually remove buttons, even with Debug enabled",after)
 page.mouse.move(220,340)
 page.wait_for_timeout(270)
 after=controls(page)
 assert after["shown"] and after["top"]["opacity"]>.95 and after["bottom"]["opacity"]>.95,(
  "mouse motion must visually restore both rows of buttons",after)
 page.close()
 browser.close()
print("4-second fullscreen control autohide + Debug + keyboard/mouse + preview + windowed OK")
