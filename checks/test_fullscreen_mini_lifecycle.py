"""Guard the real full-screen mini timer alignment during immediate view changes.

Unlike old screenshot-only tests, these assertions measure the SAME event
turn as Timer -> Settings and deliberately exercise the 250-ms thumbnail
content throttle. That throttle must not delay geometry.
"""
from pathlib import Path
import os, shutil
from playwright.sync_api import sync_playwright

html=Path(__file__).resolve().parents[1].joinpath("timer.html").read_text(encoding="utf-8")
html=html.replace("localStorage","miniAuditStorage").replace(
 "</style></head><body>",
 """</style><script>const miniAuditStorage={d:{},
 getItem(k){return this.d[k]??null},setItem(k,v){this.d[k]=v},
 removeItem(k){delete this.d[k]}};</script></head><body>""",1)
SIZES=[(1600,900),(812,456),(960,540),(960,720),(1280,720),(1920,1080)]

def measure(page):
 return page.evaluate("""()=>{
   const rect=id=>{const r=document.getElementById(id).getBoundingClientRect();
     return {left:r.left,right:r.right,top:r.top,bottom:r.bottom,width:r.width,height:r.height};};
   const card=document.querySelector("#settings .tournamentCard").getBoundingClientRect();
   const mini=document.getElementById("miniTimer");
   return {mini:rect("miniTimer"),cardLeft:card.left,
     viewport:[innerWidth,innerHeight],
     fullscreen:document.body.classList.contains("fs"),
     live:document.body.classList.contains("settingsLive"),
     settingsHidden:document.getElementById("settings").classList.contains("hidden"),
     miniWidthCSS:mini.style.getPropertyValue("--fullscreen-mini-width"),
     pointerEvents:getComputedStyle(mini).pointerEvents,
     aspectRatio:getComputedStyle(mini).aspectRatio,
     timerStarted:st.started,timerPos:st.pos,timerRunning:st.running};
 }""")

def aligned(page,context):
 r=measure(page)
 a=r["mini"]
 assert r["fullscreen"] and r["live"] and not r["settingsHidden"],(context,r)
 assert abs(a["left"])<.12,(context,"left",r)
 assert abs(a["bottom"]-r["viewport"][1])<1.5,(context,"bottom",r)
 assert abs(a["right"]-r["cardLeft"])<1.5,(context,"right",r)
 assert abs(a["width"]/a["height"]-16/9)<.035,(context,"ratio",r)
 assert r["pointerEvents"]=="auto",(context,"pointer-events",r)
 assert a["width"]>5,(context,"collapsed",r) # 812px simulated FS: centered card starts at x=20
 return r

def setup(page,mode):
 # Avoid reading Settings form into the test state on showTimer().
 page.evaluate("""mode=>{
   st.started=true;showTimer();
   Object.assign(s,{mode,positions:6,sound:false,minutes:15,seconds:0,hours:0});
   q4a(1,false);st.started=true;st.running=false;st.endAt=null;
   render();
 }""",mode)

with sync_playwright() as pw:
 if os.name=="nt":browser=pw.chromium.launch(channel="msedge",headless=True)
 else:browser=pw.chromium.launch(executable_path=shutil.which("chromium") or shutil.which("chromium-browser"),
                  args=["--no-sandbox"],headless=True)
 checks=0
 for mode in ("2","4"):
  page=browser.new_page(viewport={"width":1600,"height":900})
  errors=[]
  page.on("pageerror",lambda e:errors.append(str(e)))
  page.set_content(html,wait_until="domcontentloaded")
  page.wait_for_function("typeof recoveryArmed !== 'undefined'&&recoveryArmed")
  setup(page,mode)
  for width,height in SIZES:
   page.set_viewport_size({"width":width,"height":height})
   page.evaluate("updateStage();q25(false);showTimer()")
   # Deliberately freeze content updates. Previously showSettings()
   # delegated its essential placement solely to syncFaithfulMini(),
   # which can return before calling syncFullscreenMiniWidth().
   page.evaluate("""()=>{
     q25(true);
     faithfulMiniLast=performance.now();
     document.getElementById("miniTimer").style.setProperty("--fullscreen-mini-width","12px");
     showSettings(false);
   }""")
   aligned(page,f"{mode} {width}x{height} first fullscreen")
   checks+=1
   # Multiple rapid transitions within 250ms. Width must already be
   # correct before the first paint. No arbitrary sleeps or retries.
   for n in range(3):
    page.evaluate("""()=>{
      showTimer();q25(false);q25(true);
      faithfulMiniLast=performance.now();
      showSettings(false);
    }""")
    aligned(page,f"{mode} {width}x{height} rapid round-trip {n}")
    checks+=1
   # Vertical scrolling must not move a fixed miniature or its anchor.
   page.evaluate("window.scrollTo(0,220)")
   aligned(page,f"{mode} {width}x{height} scrolled")
   checks+=1
   page.evaluate("window.scrollTo(0,0)")
   # Real double-click on the miniature, not calling onclick directly.
   page.locator("#miniTimer").dblclick(timeout=4000)
   res=measure(page)
   assert res["settingsHidden"],(mode,width,height,"double click",res)
   assert res["timerStarted"] and res["timerPos"]==1,(mode,"timer state",res)
   checks+=1
   # Restore window mode, then re-enter settings; approved mini still
   # uses its own windowed positioning, without fullscreen width override.
   page.evaluate("q25(false);showSettings(false)")
   state=measure(page)
   assert not state["fullscreen"] and state["miniWidthCSS"]=="",(mode,width,height,"stale CSS",state)
   assert state["mini"]["left"]>=0,(mode,width,height,"windowed left",state)
   assert state["mini"]["bottom"]<=height+1,(mode,width,height,"windowed bottom",state)
   checks+=1
   page.evaluate("showTimer()")
  assert not errors,errors
  page.close()

 # The live timer is hidden in Settings. Never font-fit the hidden source:
 # previously q40() measured a 0x0 message and replaced 112px with 30px.
 # The iframe miniature then faithfully displayed that WRONG size.
 for phase in ("jump","break"):
  for fullscreen in (False,True):
   page=browser.new_page(viewport={"width":1600,"height":900})
   errors=[]
   page.on("pageerror",lambda e:errors.append(str(e)))
   page.set_content(html,wait_until="domcontentloaded")
   page.wait_for_function("typeof recoveryArmed !== 'undefined'&&recoveryArmed")
   page.evaluate("""phase=>{
     Object.assign(s,{mode:"2",positions:7,between:30,jumpDisplaySecs:60,sound:false,
       jumpSplashBodySetting:"À cette position, les EO sautent une table",
       betweenSplashBodySetting:"Changez de table"});
     st.started=true;showTimer();q25(phase==="jump" ? false : true);
     st.phase=phase;st.pos=3;st.remaining=15;st.breakDuration=30;
     st.running=true;st.endAt=null;render();
   }""",phase)
   page.evaluate("(fs)=>q25(fs)",fullscreen)
   page.evaluate("render()")
   before=page.evaluate("""()=>{
     const title=document.querySelector('#jumpSplashTitle');
     const body=document.querySelector('#jumpSplashText');
     return {title:parseFloat(getComputedStyle(title).fontSize),
       body:parseFloat(getComputedStyle(body).fontSize),style:body.style.fontSize};
   }""")
   assert before["body"]>=40,(phase,fullscreen,"main transition text is too small",before)
   page.evaluate("showSettings(false);syncFaithfulMini(true)")
   page.wait_for_function("!!document.querySelector('#faithfulMiniFrame')?.contentDocument?.querySelector('#jumpSplashText')")
   page.evaluate("syncFaithfulMini(true)")
   after=page.evaluate("""()=>{
     const frame=document.querySelector('#faithfulMiniFrame');
     const mini=frame.contentDocument;
     const body=document.querySelector('#jumpSplashText');
     const title=document.querySelector('#jumpSplashTitle');
     const miniBody=mini.querySelector('#jumpSplashText');
     const miniTitle=mini.querySelector('#jumpSplashTitle');
     return {sourceBody:parseFloat(getComputedStyle(body).fontSize),
       miniBody:parseFloat(getComputedStyle(miniBody).fontSize),
       sourceTitle:parseFloat(getComputedStyle(title).fontSize),
       miniTitle:parseFloat(getComputedStyle(miniTitle).fontSize),
       miniStyle:miniBody.style.fontSize};
   }""")
   assert abs(after["sourceBody"]-before["body"])<.01,(phase,fullscreen,"hidden source was resized",before,after)
   assert abs(after["miniBody"]-before["body"])<.01,(phase,fullscreen,"mini message differs",before,after)
   assert abs(after["miniTitle"]-before["title"])<.01,(phase,fullscreen,"mini title differs",before,after)
   assert after["miniStyle"]==before["style"],(phase,fullscreen,"mini lost actual fitted inline font",before,after)
   # Re-render while Settings is shown, the original failure path.
   page.evaluate("render();syncFaithfulMini(true)")
   after_again=page.evaluate("""()=>{
     const s=document.querySelector('#jumpSplashText');
     const m=document.querySelector('#faithfulMiniFrame').contentDocument.querySelector('#jumpSplashText');
     return [parseFloat(getComputedStyle(s).fontSize),parseFloat(getComputedStyle(m).fontSize)];
   }""")
   assert all(abs(x-before["body"])<.01 for x in after_again),(phase,fullscreen,"render destroyed font",after_again,before)
   assert not errors,(phase,fullscreen,errors)
   checks+=1
   page.close()
 browser.close()
print(f"Fullscreen miniature immediate-geometry and double-click: {checks} checks passed (2 modes, {len(SIZES)} sizes, rapid transitions)")
