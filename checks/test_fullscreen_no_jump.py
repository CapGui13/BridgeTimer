"""Validate that native fullscreen leaves no INTERMEDIATE WebView2 frame.

Real HWND geometry is covered in Win32 tests. Here we simulate the asynchronous
native call and change viewport while the fullscreen veil is already painted.
This must not impact the approved instantaneous jump or Settings navigation.
"""
from pathlib import Path
import os,shutil
from playwright.sync_api import sync_playwright

html=(Path(__file__).resolve().parents[1]/"timer.html").read_text(encoding="utf-8")
html=html.replace("localStorage","bridgeAuditStorage").replace(
 "</style></head><body>",
 """</style><script>const bridgeAuditStorage={
 data:{},getItem(k){return this.data[k]??null},
 setItem(k,v){this.data[k]=v},removeItem(k){delete this.data[k]}
 };</script></head><body>""",1)

assert "fsFading" not in html and "fsFadeIn" not in html, "Old opacity fade returned"
assert "body.fullscreenSwitching::after" in html,"Fullscreen paint veil missing"
assert "phaseMain.classList.toggle" in html,"Already validated jump teleportation missing"

def status(page):
 return page.evaluate("""()=>({
  switching:document.body.classList.contains('fullscreenSwitching'),
  fs:document.body.classList.contains('fs'),
  veil:getComputedStyle(document.body,'::after').content,
  veilBg:getComputedStyle(document.body,'::after').backgroundColor,
  timerOpacity:getComputedStyle(document.querySelector('#timer')).opacity,
  settingsActive:!document.getElementById('settings').classList.contains('hidden'),
  timerActive:!document.getElementById('timer').classList.contains('hidden'),
  nativeCalls:window.__nativeCalls||0,
  inTransition:fif
 })""")

with sync_playwright() as pw:
 if os.name=="nt": browser=pw.chromium.launch(channel="msedge",headless=True)
 else: browser=pw.chromium.launch(executable_path=shutil.which("chromium") or shutil.which("chromium-browser"),
                              headless=True,args=["--no-sandbox"])
 for show in ("settings","timer","jump"):
  page=browser.new_page(viewport={"width":812,"height":480})
  errors=[]
  page.on("pageerror",lambda e:errors.append(str(e)))
  page.set_content(html,wait_until="domcontentloaded")
  page.evaluate("""show=>{
    s.mode='2';s.positions=5;st.started=true;st.pos=1;st.running=false;
    st.phase=show==='jump'?'jump':'round';st.remaining=15;
    if(show==='settings'){showSettings(false)}else{showTimer();render()}
    window.__nativeCalls=0;window.__nativeBefore=[];
    window.nativeFullscreen=()=>{
      window.__nativeCalls++;
      window.__nativeBefore.push({
        veil:document.body.classList.contains('fullscreenSwitching'),
        content:getComputedStyle(document.body,'::after').content,
        painted:performance.now()
      });
      return new Promise(resolve=>{window.__resolveNative=resolve});
    };
  }""",show)
  base=status(page)
  assert base["settingsActive"]==(show=="settings"),(show,base)
  for i,(w,h,willFullscreen) in enumerate([(1600,900,True),(812,480,False)]):
   # Fire without awaiting: the mocked native call remains unresolved.
   page.evaluate("()=>{fs()}")
   page.wait_for_function("window.__nativeCalls>0 && typeof window.__resolveNative==='function'")
   mid=status(page)
   assert mid["switching"] and mid["inTransition"],(show,i,mid)
   assert mid["veil"] not in ("none","normal"),(show,i,mid)
   assert mid["timerOpacity"]=="1",(show,i,mid)
   page.set_viewport_size({"width":w,"height":h})
   # Native geometry has changed, but the mask must still cover the UI.
   resized=status(page)
   assert resized["switching"] and resized["veil"] not in ("none","normal"),(show,i,resized)
   page.evaluate("value=>{const cb=window.__resolveNative;delete window.__resolveNative;cb(value)}",willFullscreen)
   page.wait_for_function("!fif && !document.body.classList.contains('fullscreenSwitching')")
   complete=status(page)
   assert complete["fs"]==willFullscreen,(show,i,complete)
   assert not complete["switching"] and complete["timerOpacity"]=="1",(show,i,complete)
   assert complete["nativeCalls"]==i+1,(show,i,complete)
   # A genuine stage re-layout has occurred under the cover.
   scaled=page.evaluate("""()=>{
     const visibleTimer=!document.querySelector('#timer').classList.contains('hidden');
     const element=document.querySelector(visibleTimer?'#timer':'#settings .wrap>.head');
     const r=element.getBoundingClientRect();
     const footer=document.querySelector('#settings .actions').getBoundingClientRect();
     return {visibleTimer,x:r.x,y:r.y,width:r.width,height:r.height,
       footerRight:footer.right,footerBottom:footer.bottom};
   }""")
   assert abs(scaled["width"]-w)<2,(show,i,scaled)
   if scaled["visibleTimer"]:
    assert abs(scaled["height"]-h)<2,(show,i,scaled)
   else:
    assert abs(scaled["footerRight"]-w)<2 and abs(scaled["footerBottom"]-h)<2,(show,i,scaled)
  seen=page.evaluate("window.__nativeBefore")
  assert len(seen)==2 and all(x["veil"] and x["content"] not in ("none","normal") for x in seen),(show,seen)
  # Settings navigation and the jump-screen swap must remain unchanged.
  if show=="settings":
   assert status(page)["settingsActive"],(show,status(page))
   page.evaluate("showTimer()")
   assert status(page)["timerActive"]
  elif show=="jump":
   assert page.evaluate("document.querySelector('#timer .main').classList.contains('phasePage')")
  assert not errors,(show,errors)
  page.close()
 browser.close()
print("Fullscreen no-jump: atomic painted cover on enter/exit for Settings, Timer, Jump")
