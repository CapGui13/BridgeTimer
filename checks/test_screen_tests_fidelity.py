"""Compare all nine Screen Tests gallery snapshots against the real Timer.

The real Timer is measured inside 'Voir en grand' at an EXACT reference
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

NAMES=["prejump","jump","between","orange","red","pause","roundend","ended","temporary"]
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
  page.wait_for_function("document.querySelectorAll('#spg .screenPreviewCard iframe').length===9")
  page.wait_for_function("""()=>[...document.querySelectorAll('#spg iframe')]
    .every(x=>x.contentDocument&&x.contentDocument.querySelector('#timer .bottom'))""")
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
   gallery.append(preview)
  # The source now uses a different viewport, to catch accidental inheritance
  # of old windowed font sizes into gallery snapshots.
  page.set_viewport_size({"width":1600,"height":956})
  page.evaluate("q25(true)")
  for ix,kind in enumerate(NAMES):
   page.evaluate("kind=>_ssp(kind)",kind)
   actual=metrics(page)
   compare(kind,actual,gallery[ix])
  page.evaluate("q25(false);_csp()")
  assert page.evaluate("!document.querySelector('#settings').classList.contains('hidden')")
  assert not errors,(startwidth,errors)
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
 browser.close()
print("9 fullscreen Screen Tests snapshots plus Debug visibility and inert header controls validated")

