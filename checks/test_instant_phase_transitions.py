"""Bridge Timer: instantaneous jump/between transitions and no fullscreen fade.

Only covers the unwanted transition effects. It must not change/touch the
separately validated Timer <-> Settings navigation.
"""
from pathlib import Path
from playwright.sync_api import sync_playwright
import os, shutil

root=Path(__file__).resolve().parents[1]
html=(root/"timer.html").read_text(encoding="utf8")
html=html.replace("localStorage","bridgeAuditStorage").replace(
 "</style></head><body>",
 """</style><script>const bridgeAuditStorage={
 data:{},getItem(k){return this.data[k]??null},
 setItem(k,v){this.data[k]=v},removeItem(k){delete this.data[k]}
 };</script></head><body>""",1)

assert "fsFading" not in html and "fsFadeIn" not in html, "Fullscreen artificial opacity fade returned"
assert "transition:width .08s linear" not in html, "Jump bar CSS animation returned"
assert "async function fs()" in html, "Fullscreen control went missing"
assert 'function showTimer(){' in html and 'function showSettings(reset=false)' in html

with sync_playwright() as p:
 if os.name=="nt": browser=p.chromium.launch(channel="msedge",headless=True)
 else: browser=p.chromium.launch(
     executable_path=shutil.which("chromium") or shutil.which("chromium-browser"),
     headless=True,args=["--no-sandbox"])
 for width,height in [(812,480),(960,560),(1280,720)]:
  page=browser.new_page(viewport={"width":width,"height":height})
  errors=[]
  page.on("pageerror",lambda e:errors.append(str(e)))
  page.set_content(html,wait_until="domcontentloaded")
  page.evaluate("""()=>{
    s.mode="2";s.positions=6;s.jumpDisplaySecs=15;s.between=20;
    st.started=true;st.running=true;st.pos=1;st.remaining=60;
    st.phase="round";showTimer();render();
  }""")
  for name,phase,seconds in [
    ("round_to_jump","jump",15),
    ("jump_to_break","break",20),
    ("break_to_round","round",90),
    ("round_to_jump_again","jump",15),
    ("jump_to_round","round",100),
  ]:
   out=page.evaluate("""([phase,remaining])=>{
      st.phase=phase;st.remaining=remaining;
      st.breakDuration=20;
      render();
      const splash=document.querySelector('#jumpSplash');
      const bar=document.querySelector('#jumpSplashBar');
      const computed=getComputedStyle(bar);
      const anims=splash.getAnimations({subtree:true});
      return {
        shown:splash.classList.contains('on'),
        title:document.querySelector('#jumpSplashTitle').textContent,
        seconds:document.querySelector('#jumpSplashSeconds').textContent,
        transitionDuration:computed.transitionDuration,
        animations:anims.map(a=>a.effect?.getTiming?.().duration??"unknown"),
        top:document.querySelector('#timer .top').getBoundingClientRect().height,
        footer:document.querySelector('#timer .bottom').getBoundingClientRect().height
      };
    }""",[phase,seconds])
   assert out["shown"]==(phase!="round"),(width,name,out)
   if phase=="jump": assert str(out["seconds"])=="15",(width,name,out)
   if phase=="break": assert "CHANGEMENT" in out["title"],(width,name,out)
   assert out["transitionDuration"] in ("0s","0ms"),(width,name,out)
   assert not out["animations"],f"Animated phase transition {width} {name}: {out}"
   assert abs(out["top"]-55)<=1.3 and abs(out["footer"]-59)<=1.3, (width,name,out)
  # Mock the native API, preserving the exact fs() handler used by Windows.
  page.evaluate("""()=>{window.nativeFullscreen=()=>Promise.resolve(!document.body.classList.contains('fs'))}""")
  page.evaluate("fs()")
  page.wait_for_function("!fif")
  fullscreen=page.evaluate("""()=>({
    fs:document.body.classList.contains('fs'),
    timerOpacity:getComputedStyle(document.querySelector('#timer')).opacity,
    oldFade:document.body.classList.contains('fsFading')||document.body.classList.contains('fsFadeIn'),
    title:document.querySelector('#fsBtn').textContent
  })""")
  assert fullscreen["fs"] and fullscreen["timerOpacity"]=="1" and not fullscreen["oldFade"],fullscreen
  page.evaluate("fs()")
  page.wait_for_function("!fif")
  after=page.evaluate("""()=>({
    fs:document.body.classList.contains('fs'),
    timerOpacity:getComputedStyle(document.querySelector('#timer')).opacity,
    title:document.querySelector('#fsBtn').textContent
  })""")
  assert not after["fs"] and after["timerOpacity"]=="1",after
  # Settings roundtrip is intentionally untouched.
  page.evaluate("showSettings(false)")
  assert page.evaluate("!document.querySelector('#settings').classList.contains('hidden')")
  page.evaluate("showTimer()")
  assert page.evaluate("!document.querySelector('#timer').classList.contains('hidden')")
  assert not errors,(width,errors)
  page.close()
 browser.close()
print("Immediate phase and fullscreen transitions OK at 812/960/1280; Settings navigation preserved")
