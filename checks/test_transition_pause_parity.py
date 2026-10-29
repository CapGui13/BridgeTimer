"""Edge/WebView2 acceptance: jump and between-turn identical ±15s and Pause.

Tests the actual shipped HTML with real buttons and keyboard shortcuts,
both windowed and faux-native fullscreen stage geometry.
"""
from pathlib import Path
import os,shutil
from playwright.sync_api import sync_playwright

html=(Path(__file__).resolve().parents[1]/"timer.html").read_text(encoding="utf-8")
html=html.replace("localStorage","phasePauseStorage").replace("</style></head><body>",
  """</style><script>const phasePauseStorage={data:{},
      getItem(k){return this.data[k]??null},setItem(k,v){this.data[k]=v},
      removeItem(k){delete this.data[k]}};</script></head><body>""",1)

def metrics(page):
 return page.evaluate("""()=>{
  const overlay=document.querySelector('#pauseOverlay');
  const pauseBig=overlay.querySelector('.pauseBig');
  const pauseSmall=overlay.querySelector('.pauseSmall');
  const splash=document.querySelector('#jumpSplash');
  const main=document.querySelector('#timer .main');
  const r=overlay.getBoundingClientRect();
  const big= getComputedStyle(pauseBig), small=getComputedStyle(pauseSmall);
  const ov=getComputedStyle(overlay),sp=getComputedStyle(splash);
  return {
    phase:st.phase,running:st.running,remaining:st.remaining,
    overlayDisplay:ov.display,overlayZ:Number(ov.zIndex),
    splashDisplay:sp.display,splashZ:Number(sp.zIndex),
    pauseTitle:pauseBig.textContent.trim(),
    pauseSubtitle:pauseSmall.textContent.trim(),
    blur:ov.backdropFilter,overlayBg:ov.backgroundColor,
    font:big.fontSize,color:big.color,subFont:small.fontSize,
    rect:[r.x,r.y,r.width,r.height],
    phasePage:main.classList.contains('phasePage'),
    miniPause:document.querySelector('#miniTimer').classList.contains('is-pause'),
    caption:document.querySelector('#pause').textContent,
    less:document.querySelector('#minus').textContent,
    more:document.querySelector('#plus').textContent,
    remainingLabel:document.querySelector('#jumpSplashSeconds').textContent,
    splashTitle:document.querySelector('#jumpSplashTitle').textContent,
    timerTop:document.querySelector('#timer .top').getBoundingClientRect().height,
    timerBottom:document.querySelector('#timer .bottom').getBoundingClientRect().height
  };
}""")

with sync_playwright() as pw:
 if os.name=="nt":
  browser=pw.chromium.launch(channel="msedge",headless=True)
 else:
  browser=pw.chromium.launch(executable_path=shutil.which("chromium") or shutil.which("chromium-browser"),
                             args=["--no-sandbox"],headless=True)
 checks=0
 for size in ((812,480),(1280,720),(1600,900)):
  page=browser.new_page(viewport={"width":size[0],"height":size[1]})
  errors=[]
  page.on("pageerror",lambda e:errors.append(str(e)))
  page.set_content(html,wait_until="domcontentloaded")
  page.wait_for_function("typeof recoveryArmed!=='undefined' && recoveryArmed")
  page.evaluate("""()=>{
    s.mode="2";s.positions=6;s.jumpDisplaySecs=45;s.between=45;
    s.sound=false;s.hours=0;s.minutes=5;s.seconds=0;
    fill();st.started=true;st.pos=1;st.roundDuration=300;
    showTimer();
    document.body.tabIndex=-1;document.body.focus();
    st.longClockAtStart=false;st.endAt=null;st.running=false;
  }""")
  for fullscreen in (False,True):
   page.evaluate("(fs)=>{q25(fs);document.body.focus()}",fullscreen)
   # Baseline: the SAME pause overlay's size, colour, opacity,
   # blur and text as in the normal round, not a new rendering.
   page.evaluate("""()=>{
     st.phase="round";st.remaining=150;st.running=false;st.endAt=null;render();
   }""")
   base=metrics(page)
   assert base["overlayDisplay"]=="flex" and base["pauseTitle"]=="PAUSE",(size,fullscreen,base)
   assert base["less"]=="− 1 min" and base["more"]=="+ 1 min",base
   assert page.evaluate("adjustmentStep()")==60
   checks+=1
   for phase in ("jump","break"):
    page.evaluate("""phase=>{
      st.phase=phase;st.running=false;st.endAt=null;st.remaining=45;
      st.breakDuration=45;render();
    }""",phase)
    o=metrics(page)
    assert o["phasePage"] and o["splashDisplay"]=="flex",(size,fullscreen,phase,o)
    assert o["overlayDisplay"]=="flex" and o["overlayZ"]>o["splashZ"],(size,fullscreen,phase,o)
    assert o["pauseTitle"]==base["pauseTitle"] and o["pauseSubtitle"]==base["pauseSubtitle"],o
    assert (o["blur"],o["overlayBg"],o["font"],o["color"],o["subFont"]) == (
      base["blur"],base["overlayBg"],base["font"],base["color"],base["subFont"]),(
      size,fullscreen,phase,"pause appearance not identical",o,base)
    assert all(abs(a-b)<1 for a,b in zip(o["rect"],base["rect"])),(
      size,fullscreen,phase,"pause overlay moved",o["rect"],base["rect"])
    assert o["miniPause"],(phase,"mini preview must mark pause",o)
    assert o["caption"]=="Reprendre",(size,fullscreen,phase,o)
    assert o["less"]=="− 15 s" and o["more"]=="+ 15 s",(size,fullscreen,phase,o)
    assert page.evaluate("adjustmentStep()")==15
    assert o["remainingLabel"]=="45",o
    checks+=1
    # The footer + and − physically adjust by 15s, even if PAUSED.
    page.locator("#plus").click()
    assert round(page.evaluate("st.remaining"))==60,(phase,"plus click")
    page.locator("#minus").click()
    assert round(page.evaluate("st.remaining"))==45,(phase,"minus click")
    # The same F7/F8 keys, including OS autorepeat, use the same step.
    page.evaluate("document.body.focus()")
    page.keyboard.press("F8")
    assert round(page.evaluate("st.remaining"))==60,(phase,"F8")
    page.keyboard.press("F7")
    assert round(page.evaluate("st.remaining"))==45,(phase,"F7")
    page.evaluate("""()=>{
      for(let i=0;i<2;i++){
       document.dispatchEvent(new KeyboardEvent('keydown',
           {key:'F8',code:'F8',repeat:true,bubbles:true,cancelable:true}));
      }
    }""")
    assert round(page.evaluate("st.remaining"))==75,(phase,"held F8")
    checks+=1
    # Resume using Space, hiding the exact SAME overlay without moving
    # the transition content, while countdown continues. Pause it again
    # using the bottom button and assert the countdown freezes.
    page.keyboard.press("Space")
    running=metrics(page)
    assert running["running"] and running["overlayDisplay"]=="none",(phase,"resume Space",running)
    assert running["caption"]=="Pause" and running["splashDisplay"]=="flex",running
    page.locator("#plus").click()
    after_plus=page.evaluate("st.remaining")
    assert 88<after_plus<=90,(phase,"running +15",after_plus)
    page.locator("#minus").click()
    assert 73<page.evaluate("st.remaining")<=75,(phase,"running -15")
    page.locator("#pause").click()
    again=metrics(page)
    assert not again["running"] and again["overlayDisplay"]=="flex" and again["overlayZ"]>again["splashZ"],again
    assert again["caption"]=="Reprendre" and again["miniPause"],again
    frozen=page.evaluate("st.remaining")
    page.wait_for_timeout(160)
    assert page.evaluate("st.remaining")==frozen,(phase,"paused time still ticking")
    assert again["timerTop"]==base["timerTop"] and again["timerBottom"]==base["timerBottom"],(phase,"bands moved")
    checks+=1
   # Make sure the ordinary round remains unaffected in either UI mode.
   page.evaluate("st.phase='round';st.remaining=180;st.running=false;st.endAt=null;render()")
   assert page.evaluate("adjustmentStep()")==60
   page.locator("#plus").click()
   assert page.evaluate("st.remaining")==240
   assert metrics(page)["overlayDisplay"]=="flex"
   checks+=1
  assert not errors,(size,errors)
  page.close()
 browser.close()
print(f"Transition pause parity: {checks} real-browser checks passed at 3 sizes, windowed and fullscreen")
