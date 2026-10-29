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

# Snapshot normalized within the actual timer's stage.
SCRIPT="""() => {
 const stage=document.querySelector('#timer').getBoundingClientRect();
 const selectors=JSON.parse(arguments[0]);
 const out={};
 for(const selector of selectors){
  const el=document.querySelector(selector.startsWith('.')?'#timer '+selector:selector);
  if(!el)continue;
  const cs=getComputedStyle(el),r=el.getBoundingClientRect();
  out[selector]={x:r.left-stage.left,y:r.top-stage.top,
   w:r.width,h:r.height,display:cs.display,visibility:cs.visibility,
   font:parseFloat(cs.fontSize),text:el.textContent.trim().replace(/\\s+/g,' ').slice(0,200)};
 }
 return out;
}"""

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
    font:parseFloat(cs.fontSize),text:el.textContent.trim().replace(/\\s+/g,' ').slice(0,200)};
  }return out;
 }""",SELECTORS)

def compare(kind,actual,preview):
 for selector in SELECTORS:
  a,b=actual[selector],preview[selector]
  assert a["text"]==b["text"],f"{kind} {selector} text differs: {a['text']!r} / {b['text']!r}"
  if a["display"]=="none" or b["display"]=="none":
   assert a["display"]==b["display"],f"{kind} {selector} visibility differs: {a['display']} / {b['display']}"
   continue
  for key in ("x","y","w","h","font"):
   assert abs(a[key]-b[key])<=1.4,f"{kind} {selector} {key}: real {a[key]:.2f} vs gallery {b[key]:.2f}"

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
   showSettings(false);_osp();
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
   assert abs(preview[".top"]["h"]-82)<2,(kind,preview[".top"])
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
 browser.close()
print("9 fullscreen Screen Tests snapshots match real 1600x900 Timer geometry from two windowed sizes")
