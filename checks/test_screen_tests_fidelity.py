"""Compare all ten Screen Tests gallery snapshots against the real Timer.

The real Timer is measured in the single-test preview at an EXACT reference
1600x900 stage. Gallery iframes must use the same fullscreen CSS and geometry,
not an 812px-window font carried into a 1600px virtual view.
"""
from pathlib import Path
import os,shutil
from playwright.sync_api import sync_playwright

html=(Path(__file__).resolve().parents[1]/"timer.html").read_text(encoding="utf-8")
html=html.replace("localStorage","bridgeAuditStorage").replace(
"</style></head><body>",
"""</style><script>const bridgeAuditStorage={data:{},getItem(k){return this.data[k]??null},
setItem(k,v){this.data[k]=v},removeItem(k){delete this.data[k]}};
</script></head><body>""",1)

NAMES=["temporary","pause","board","prejump","jump","between","orange","red","roundend","ended"]
SELECTORS=[".top",".bottom","#status","#clock","#msg","#jumpSplash",
           "#jumpSplashTitle","#jumpSplashText","#jumpSplashSeconds",
           "#finishBig","#pauseOverlay","#localTime","#round","#pause",
           "#minus","#next","#bar"]

# A Page or Frame supports eval with (selector list) as the argument.
def metrics(context):
 return context.evaluate("""sels=>{
  const stage=document.querySelector('#timer').getBoundingClientRect();
  const out={};
  for(const selector of sels){
   const el=document.querySelector(selector.startsWith('.')?'#timer '+selector:selector);
   if(!el)continue;
   const cs=getComputedStyle(el),r=el.getBoundingClientRect();
   out[selector]={x:r.left-stage.left,y:r.top-stage.top,
    w:r.width,h:r.height,display:cs.display,visibility:cs.visibility,
    font:parseFloat(cs.fontSize),shown:el.getClientRects().length>0&&cs.visibility!=="hidden",
     text:el.textContent.trim().replace(/\\s+/g,' ').slice(0,200)};
  }return out;
 }""",SELECTORS)

def compare(kind,actual,preview):
 for selector in SELECTORS:
  a,b=actual[selector],preview[selector]
  # Wall-clock time advances while each preview opens; the snapshot is frozen.
  if selector not in (".bottom","#localTime"):
   assert a["text"]==b["text"],f"{kind} {selector} text differs: {a['text']!r} / {b['text']!r}"
  if not a["shown"] or not b["shown"]:
   assert a["shown"]==b["shown"],f"{kind} {selector} visible parent differs: {a} / {b}"
   continue
  for key in ("x","y","w","h","font"):
   # The live wall clock may have different digits than its frozen preview.
   # Compare its anchor, baseline and typography, not intrinsic text width.
   if selector=="#localTime" and key=="w":continue
   # Footer controls are centered in the LIVE free span between the
   # current wall-clock label and the TOUR label. The two snapshots are
   # taken at different instants; clock glyph widths can change. Accept
   # exactly that derived center displacement, not arbitrary motion.
   center_delta=0
   if key=="x" and selector in ("#pause","#minus","#next"):
    clock_real=actual["#localTime"]
    clock_gallery=preview["#localTime"]
    round_real=actual["#round"]
    round_gallery=preview["#round"]
    center_delta=(
      (clock_real["x"]+clock_real["w"])-(clock_gallery["x"]+clock_gallery["w"])
      + round_real["x"]-round_gallery["x"]
    )/2
   # The gallery can either retain the captured footer center or
   # recompute it from the later wall-clock digits. Both are correct
   # provided every other property matches and the control displacement
   # is either zero or exactly the live clock-dependent center shift.
   movement=a[key]-b[key]
   assert min(abs(movement),abs(movement-center_delta))<=1.4,(
     f"{kind} {selector} {key}: real {a[key]:.2f} vs gallery {b[key]:.2f}; "
     f"allowed center shift {center_delta:.2f}")

with sync_playwright() as pw:
 if os.name=="nt": browser=pw.chromium.launch(channel="msedge",headless=True)
 else: browser=pw.chromium.launch(
  executable_path=shutil.which("chromium") or shutil.which("chromium-browser"),
  headless=True,args=["--no-sandbox"])

 for startwidth,startheight in ((812,480),(960,720)):
  page=browser.new_page(viewport={"width":startwidth,"height":startheight})
  errors=[]
  page.on("pageerror",lambda e:errors.append(str(e)))
  page.set_content(html,wait_until="domcontentloaded")
  page.evaluate("""()=>{
   s.eventName="Test visuel";s.mode="2";s.positions=6;
   s.minutes=75;s.hours=1;s.seconds=0;
   s.jumpDisplaySecs=15;s.between=20;
   showSettings(false);document.body.classList.add("debugMode");_osp();
  }""")
  page.wait_for_function("document.querySelectorAll('#spg .screenPreviewCard iframe').length===10")
  page.wait_for_function("""()=>[...document.querySelectorAll('#spg iframe')]
    .every(x=>x.contentDocument&&x.contentDocument.querySelector('#timer .bottom'))""")
  assert page.locator("#spg .spHeader h3").all_inner_texts()==[
    "Message temporaire","Pause","Numéro de donne en cours","Pré-alerte saut",
    "Saut de table","Temps entre tours","Alerte orange","Alerte rouge",
    "Fin du tour (Match par 4)","Fin de la séance (Paires)"
   ],"The 5 requested gallery rows are not in order"
  assert page.locator("#sps option").evaluate_all("els=>els.map(el=>el.value)")==["all"]+NAMES
  assert page.locator("#spg button").count()==0,"Removed Voir en grand buttons reappeared"
  assert "Rendu plein écran" not in page.locator("#spg").inner_text()
  gallery=[]
  for ix,kind in enumerate(NAMES):
   card=page.locator("#spg .screenPreviewCard").nth(ix)
   frame=card.locator("iframe").element_handle()
   content=frame.content_frame()
   assert content is not None,(kind,"iframe missing")
   fs=content.evaluate("document.body.classList.contains('fs')")
   assert fs,(kind,"gallery must use real fullscreen CSS")
   preview=metrics(content)
   assert abs(preview[".top"]["h"]-80)<2,(kind,preview[".top"])
   assert abs(preview[".bottom"]["h"]-88)<2,(kind,preview[".bottom"])
   if kind=="board":
    assert "donne 3" in preview["#msg"]["text"],("board screenshot must show current board 3",preview["#msg"])
   if kind in ("temporary","board","prejump"):
    minimum={"temporary":95,"board":92,"prejump":81}[kind]
    assert preview["#msg"]["font"]>=minimum,(
      kind,"Green message still shrinks to former tiny font in long-clock gallery",
      preview["#msg"]["font"],"expected >=",minimum)
   gallery.append(preview)
  # The source now uses a different viewport, to catch accidental inheritance
  # of old windowed font sizes into gallery snapshots.
  page.set_viewport_size({"width":1600,"height":956})
  page.evaluate("q25(true)")
  for ix,kind in enumerate(NAMES):
   page.evaluate("kind=>_ssp(kind)",kind)
   actual=metrics(page)
   if kind=="board":
    assert "donne 3" in actual["#msg"]["text"],("live board preview missing",actual["#msg"])
    assert page.evaluate("!!_spset.boardProgressNotice && zboard() && !_spset.jumpAdvanceNotice"),"board sample should enable actual board progress computation"
   compare(kind,actual,gallery[ix])
  page.evaluate("q25(false);_csp()")
  assert page.evaluate("!document.querySelector('#settings').classList.contains('hidden')")
  assert not errors,(startwidth,errors)
  page.close()

 # Switching Tous -> single must be a genuine teleportation, not a
 # change in the scene's origin, zoom, toolbar, or native fullscreen state.
 # Test both real windowed dimensions and fullscreen, including scrolling
 # the gallery, the actual user double-click and selector parity.
 for viewport,fullscreen in [((812,480),False),((960,720),False),((1600,900),True),((1650,928),True)]:
  page=browser.new_page(viewport={"width":viewport[0],"height":viewport[1]})
  errors=[]
  page.on("pageerror",lambda e:errors.append(str(e)))
  page.set_content(html,wait_until="domcontentloaded")
  page.evaluate("document.body.classList.add('debugMode');_osp()")
  page.evaluate("(on)=>q25(on)",fullscreen)
  def layout():
   return page.evaluate("""()=>{
    const t=document.querySelector('#timer');
    const tb=document.querySelector('#sptb').getBoundingClientRect();
    const st=t.getBoundingClientRect();
    const r=el=>[el.x,el.y,el.width,el.height];
    return {toolbar:r(tb),stage:r(st),scale:parseFloat(t.style.getPropertyValue('--stage-scale')),
      origin:[parseFloat(t.style.getPropertyValue('--stage-left')),parseFloat(t.style.getPropertyValue('--stage-top'))],
      fullscreen:document.body.classList.contains('fs')};
   }""")
  before=layout()
  scroll=page.evaluate("""()=>{
    const e=document.querySelector('#spg');
    e.scrollTop=180;
    return {position:e.scrollTop,toolbar:document.querySelector('#sptb').getBoundingClientRect().top,
      client:e.clientHeight,scroll:e.scrollHeight,display:getComputedStyle(e).display,
      overflow:getComputedStyle(e).overflowY,cards:e.children.length,
      root:document.querySelector('#timer').className,
      rect:e.getBoundingClientRect().toJSON()};
  }""")
  assert scroll["position"]>0,(viewport,"gallery should scroll independently",scroll)
  assert abs(scroll["toolbar"]-before["toolbar"][1])<.25,(viewport,"gallery scroll moved toolbar",scroll,before)
  page.evaluate("document.querySelector('#spg').scrollTop=0")
  first=page.locator("#spg .screenPreviewCard").first
  first.click()
  assert page.evaluate("spk==='all'"),(viewport,"single-click must not open a test")
  first.dblclick()
  assert page.evaluate("spk==='temporary' && !document.querySelector('#timer').classList.contains('spa')"),(
    viewport,"double-click did not open the matching single preview")
  after=layout()
  assert before["fullscreen"]==after["fullscreen"]==fullscreen,(viewport,"native fullscreen unexpectedly toggled",before,after)
  for key in ("toolbar","stage","origin"):
   assert all(abs(a-b)<=.5 for a,b in zip(before[key],after[key])),(viewport,key,"layout jumped",before,after)
  assert abs(before["scale"]-after["scale"])<1e-9,(viewport,"scale jumped",before,after)
  clicked=metrics(page)
  page.locator("#sps").select_option("all")
  page.locator("#sps").select_option("temporary")
  selected=metrics(page)
  compare("temporary (double-click vs selector)",clicked,selected)
  page.locator("#sps").select_option("all")
  final=layout()
  for key in ("toolbar","stage","origin"):
   assert all(abs(a-b)<=.5 for a,b in zip(before[key],final[key])),(viewport,key,"reverse layout jumped",before,final)
  assert not errors,(viewport,errors)
  page.close()

 # Debug-only entry; interactive preview toolbar stays usable, but the
 # timer's own top and bottom controls are read-only, in every viewport.
 for viewport,fullscreen in [((960,720),False),((1600,900),True)]:
  page=browser.new_page(viewport={"width":viewport[0],"height":viewport[1]})
  errors=[]
  page.on("pageerror",lambda e:errors.append(str(e)))
  page.set_content(html,wait_until="domcontentloaded")
  assert not page.locator("#spb").is_visible(),("non-Debug must hide test entry",viewport)
  page.evaluate("_osp()")
  assert page.locator("#settings").is_visible(),("non-Debug must not open preview",viewport)
  assert not page.evaluate("!!_sps"),("preview state set without Debug",viewport)
  page.locator("#debugBtn").click()
  assert page.locator("#spb").is_visible(),("Debug must reveal test entry",viewport)
  page.evaluate("on=>q25(on)",fullscreen)
  page.locator("#spb").click()
  assert page.evaluate("!!_sps && document.querySelector('#timer').classList.contains('spm')"),viewport
  assert len(page.locator("#spg .screenPreviewCard").all())==len(NAMES),viewport
  page.locator("#sps").select_option("board")
  assert "donne 3" in page.locator("#msg").inner_text(),(viewport,"test selector should display third board")
  assert "Simulation — chrono réel inchangé" not in page.locator("#sptb").inner_text()
  assert "Simulation — chrono réel inchangé" not in page.locator("#spg").inner_text()
  page.locator("#sps").select_option("jump")
  assert page.evaluate("spk==='jump'"),viewport
  assert page.locator("#spc").is_visible(),("preview exit disappeared",viewport)
  lock=page.evaluate("""()=>{
    const top=document.querySelector('#timer .topBtns');
    const bot=document.querySelector('#timer .bottom');
    return {topInert:top.inert,bottomInert:bot.inert,
      pointer:getComputedStyle(top).pointerEvents,
      mode:document.querySelector('#timer').className};
  }""")
  assert lock["topInert"] and lock["bottomInert"] and lock["pointer"]=="none",(viewport,lock)
  page.evaluate("document.body.classList.add('showControls')")
  for id in ("resumeBtn","messageBtn","settingsBtn","fsBtn"):
   button=page.locator("#"+id)
   assert button.is_visible(),(viewport,id,"should still be drawn")
   r=button.bounding_box()
   assert r,(viewport,id,"missing button rect")
   page.mouse.click(r["x"]+r["width"]/2,r["y"]+r["height"]/2)
   still=page.evaluate("""()=>{
     return {preview:spk,settingsVisible:!document.querySelector('#settings').classList.contains('hidden'),
       resumeVisible:!document.querySelector('#resumeOverlay').classList.contains('hidden'),
       messageVisible:!document.querySelector('#tempMessageOverlay').classList.contains('hidden'),
       fullscreen:document.body.classList.contains('fs')};
   }""")
   assert still["preview"]=="jump" and not still["settingsVisible"],(viewport,id,still)
   assert not still["resumeVisible"] and not still["messageVisible"],(viewport,id,still)
   assert still["fullscreen"]==fullscreen,(viewport,id,"fullscreen changed",still)
  page.locator("#spc").click()
  assert page.locator("#settings").is_visible(),(viewport,"return to settings")
  assert not page.evaluate("document.querySelector('#timer .topBtns').inert"),viewport
  page.locator("#debugBtn").click()
  assert not page.locator("#spb").is_visible(),("Debug off should hide button immediately",viewport)
  assert not errors,errors
  page.close()
 # Regression: the THREE families of round notices must never reach the
 # approved clock, for either initial duration and in both UI scale modes.
 # The timer digits themselves must retain their size and position.
 for viewport in ((1600,900),(960,720),(812,480),(1920,1080)):
  page=browser.new_page(viewport={"width":viewport[0],"height":viewport[1]})
  errors=[]
  page.on("pageerror",lambda e:errors.append(str(e)))
  page.set_content(html,wait_until="domcontentloaded")
  for fullscreen in (False,True):
   page.evaluate("(fs)=>q25(fs)",fullscreen)
   for long_clock in (False,True):
    prev_clock=None
    for kind in ("board","prejump","temporary"):
     measured=page.evaluate("""([longClock,kind])=>{
       st.started=true;showTimer();
       const duration=longClock?3600:1800;
       const remaining=kind==="prejump"?40:duration-180;
       Object.assign(s,{mode:"2",eventName:"Tournoi de bridge",positions:8,
         hours:longClock?1:0,minutes:longClock?0:30,seconds:0,
         boardProgressNotice:kind==="board",jumpAdvanceNotice:kind==="prejump",
         jumpRound:3,jumpMessage:"Au prochain tour, les EO sautent une table",
         quickMessage:"Merci de bien vouloir terminer les donnes avant la fin du tour",
         sound:false});
       Object.assign(st,{phase:"round",started:true,running:true,endAt:null,
         pos:kind==="prejump"?3:2,remaining,roundDuration:duration,
         longClockAtStart:longClock,roundBoardDuration:duration/8,roundBoards:8});
       tempMessageUntil=kind==="temporary"?Date.now()+30000:0;
       render();
       const clock=$("clock").getBoundingClientRect(),
          msg=$("msg").getBoundingClientRect(),
          main=$("msg").parentElement.getBoundingClientRect();
       const range=document.createRange();range.selectNodeContents($("msg"));
       const ink=range.getBoundingClientRect();
       return {clock:[clock.x,clock.y,clock.width,clock.height],
         clockBottom:clock.bottom,boxTop:msg.top,boxBottom:msg.bottom,
         inkTop:ink.top,inkBottom:ink.bottom,font:parseFloat(getComputedStyle($("msg")).fontSize),mainBottom:main.bottom,text:$("msg").textContent,
         scale:Number($("timer").style.getPropertyValue("--stage-scale"))||1};
     }""",[long_clock,kind])
     assert measured["text"],(viewport,fullscreen,long_clock,kind,"missing announcement")
     assert measured["inkTop"]>measured["clockBottom"]+2,(
       viewport,fullscreen,long_clock,kind,"announcement overlaps timer",measured)
     assert measured["boxBottom"]<=measured["mainBottom"]+1.5,(
       viewport,fullscreen,long_clock,kind,"announcement exceeds main",measured)
     assert measured["inkBottom"]<=measured["mainBottom"]+3,(
       viewport,fullscreen,long_clock,kind,"announcement ink cropped at footer",measured)
     # Compare against the EXACT former typography at the same displayed
     # clock/state rather than an absolute font threshold: clock geometry
     # depends on which digits happen to be shown.
     if kind=="temporary" and viewport==(1600,900):
      comparison=page.evaluate("""()=>{
        const e=$("msg"),newFont=parseFloat(getComputedStyle(e).fontSize);
        const newHeight=parseFloat(e.style.height);
        e.style.width="min(1400px,calc(100% - 48px))";
        e.style.lineHeight="1.08";
        e.style.height=Math.max(0,newHeight-3).toFixed(2)+"px";
        lrf="";q38();
        const oldFont=parseFloat(getComputedStyle(e).fontSize);
        e.style.removeProperty("width");
        e.style.removeProperty("line-height");
        placeRoundNoticeBelowClock();lrf="";q38();
        return {oldFont,newFont,restored:parseFloat(getComputedStyle(e).fontSize)};
      }""")
      assert comparison["newFont"]>=comparison["oldFont"]+1,(
        viewport,fullscreen,long_clock,kind,"notice was not enlarged",comparison)
      assert comparison["newFont"]==comparison["restored"],(
        viewport,fullscreen,long_clock,kind,"new notice size not stable",comparison)
     if prev_clock is not None:
      assert all(abs(x-y)<.15 for x,y in zip(prev_clock,measured["clock"])),(
        viewport,fullscreen,long_clock,kind,"clock moved during notice",prev_clock,measured)
     prev_clock=measured["clock"]
  assert not errors,(viewport,errors)
  page.close()
 browser.close()
print("10 Screen Tests fidelity, Debug-only controls and round notice clearance: browser checks passed")

