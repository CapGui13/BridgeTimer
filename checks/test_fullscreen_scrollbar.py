"""Regression: no document scrollbar is painted at the OLD window edge
while the window resizes to native fullscreen.

The fullscreen Settings page genuinely overflows vertically. We test the
root and body scrollbar suppression before and during the native resize,
and verify that windowed Settings scrolling returns after the reverse trip.
"""
from pathlib import Path
from playwright.sync_api import sync_playwright
import os, shutil

html=(Path(__file__).resolve().parents[1]/"timer.html").read_text(encoding="utf-8")
html=html.replace("localStorage","bridgeAuditStorage").replace(
"</style></head><body>",
"""</style><script>const bridgeAuditStorage={data:{},
getItem(k){return this.data[k]??null},setItem(k,v){this.data[k]=v},
removeItem(k){delete this.data[k]}};</script></head><body>""",1)

def snapshot(page):
 return page.evaluate("""()=>{
  const root=document.documentElement, body=document.body;
  return {
   locked:root.classList.contains('fullscreenScrollbarLock'),
   switching:body.classList.contains('fullscreenSwitching'),
   fs:body.classList.contains('fs'),
   rootOverflow:getComputedStyle(root).overflowY,
   bodyOverflow:getComputedStyle(body).overflowY,
   rootScrollbar:getComputedStyle(root).scrollbarWidth,
   bodyScrollbar:getComputedStyle(body).scrollbarWidth,
   htmlHeight:root.scrollHeight,viewportHeight:root.clientHeight,
   nativeCalls:window.__nativeCalls||0
  };
 }""")

with sync_playwright() as pw:
 if os.name=="nt": browser=pw.chromium.launch(channel="msedge",headless=True)
 else: browser=pw.chromium.launch(
  executable_path=shutil.which("chromium") or shutil.which("chromium-browser"),
  headless=True,args=["--no-sandbox"])

 for startScreen in ("settings","timer","jump"):
  page=browser.new_page(viewport={"width":812,"height":480})
  errors=[]
  page.on("pageerror",lambda e: errors.append(str(e)))
  page.set_content(html,wait_until="domcontentloaded")
  page.evaluate("""screen=>{
    s.mode='2';s.positions=6;st.pos=1;st.started=true;st.phase=screen==='jump'?'jump':'round';
    st.remaining=900;st.running=false;
    if(screen==='settings')showSettings(false);else{showTimer();render()}
    window.__nativeCalls=0;
    window.nativeFullscreen=()=>{
      window.__nativeCalls++;
      window.__nativeAtCall={
       htmlOverflow:getComputedStyle(document.documentElement).overflowY,
       bodyOverflow:getComputedStyle(document.body).overflowY,
       htmlScrollbar:getComputedStyle(document.documentElement).scrollbarWidth,
       bodyScrollbar:getComputedStyle(document.body).scrollbarWidth
      };
      return new Promise(resolve=>{window.__resolveNative=resolve});
    };
  }""",startScreen)

  before=snapshot(page)
  assert not before["locked"],(startScreen,before)
  if startScreen=="settings":
   assert before["htmlHeight"]>before["viewportHeight"],(
     "Settings must be a genuinely scrollable page",before)

  for index,(width,height,expectedFullscreen) in enumerate(((1600,900,True),(812,480,False))):
   page.evaluate("()=>{fs()}")
   page.wait_for_function("window.__nativeCalls>0 && typeof window.__resolveNative==='function'") if index==0 else page.wait_for_function("window.__nativeCalls>1 && typeof window.__resolveNative==='function'")
   beforeNative=page.evaluate("window.__nativeAtCall")
   assert beforeNative["htmlOverflow"]=="hidden" and beforeNative["bodyOverflow"]=="hidden",(startScreen,index,beforeNative)
   assert beforeNative["htmlScrollbar"]=="none" and beforeNative["bodyScrollbar"]=="none",(startScreen,index,beforeNative)
   pending=snapshot(page)
   assert pending["locked"] and pending["switching"],(startScreen,index,pending)
   page.set_viewport_size({"width":width,"height":height})
   afterResize=snapshot(page)
   assert afterResize["rootOverflow"]=="hidden" and afterResize["rootScrollbar"]=="none",(startScreen,index,afterResize)
   assert afterResize["bodyOverflow"]=="hidden" and afterResize["bodyScrollbar"]=="none",(startScreen,index,afterResize)
   page.evaluate("value=>{const f=window.__resolveNative;delete window.__resolveNative;f(value)}",expectedFullscreen)
   page.wait_for_function("!fif && !document.body.classList.contains('fullscreenSwitching')")
   after=snapshot(page)
   assert not after["locked"] and not after["switching"],(startScreen,index,after)
   assert after["fs"]==expectedFullscreen,(startScreen,index,after)
   if expectedFullscreen:
    assert after["rootScrollbar"]=="none" and after["bodyScrollbar"]=="none",(startScreen,index,after)
   else:
    assert after["rootOverflow"]!="hidden" and after["bodyOverflow"]!="hidden",(startScreen,index,after)
    assert after["rootScrollbar"]!="none" and after["bodyScrollbar"]!="none",(startScreen,index,after)

  if startScreen=="settings":
   page.evaluate("window.scrollTo(0,350)")
   pos=page.evaluate("window.scrollY")
   assert pos>0,("Settings must remain scrollable on windowed return",pos)
  elif startScreen=="jump":
   assert page.evaluate("document.querySelector('#timer .main').classList.contains('phasePage')")
  assert not errors,(startScreen,errors)
  page.close()
 browser.close()
print("Fullscreen scrollbar lock: Settings, Timer, Jump; enter/exit; windowed scroll restored")
