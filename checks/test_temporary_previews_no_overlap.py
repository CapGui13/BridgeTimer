"""Temporary-message mini timer and test previews only: regression test.

The normal fullscreen timer typography, all other announcements, and the
1600x900 scale must stay as in the approved version.
"""
from pathlib import Path
import os,shutil
from playwright.sync_api import sync_playwright

source=Path(__file__).resolve().parents[1]/"timer.html"
html=source.read_text(encoding="utf-8")
assert "#timer.miniTempPreview.roundReading #msg.roundMessageTemporary" in html
assert "#timer.galleryTempPreview.roundReading #msg.roundMessageTemporary" in html
html=html.replace("localStorage","tempAuditStorage").replace("</style></head><body>",
 """</style><script>const tempAuditStorage={data:{},getItem(k){return this.data[k]??null},
 setItem(k,v){this.data[k]=v},removeItem(k){delete this.data[k]}};</script></head><body>""",1)
TEXT="Au prochain tour, les EO sautent une table"

SETUP="""text=>{
 Object.assign(s,{mode:'4',positions:6,pairCount:26,hours:1,minutes:0,seconds:0,
    eventName:'AAAA',quickMessage:text,quickMessageSecs:15,boardProgressNotice:false,sound:false});
 Object.assign(st,{started:true,phase:'round',running:true,remaining:3595,
    roundDuration:3600,pos:1,longClockAtStart:true,roundBoards:8});
 tempMessageUntil=Date.now()+60000;
 fill();showTimer();render();
}"""
MAIN="""()=>{
 const e=document.querySelector('#msg'),style=getComputedStyle(e);
 return {text:e.textContent,kind:e.className,font:parseFloat(style.fontSize),
 lineHeight:parseFloat(style.lineHeight)};
}"""
MINI="""()=>{
 const d=document.querySelector('#faithfulMiniFrame')?.contentDocument;
 const msg=d?.querySelector('#msg'),clock=d?.querySelector('#clock'),main=d?.querySelector('.main');
 if(!msg||!clock||!main)return null;
 const range=d.createRange();range.selectNodeContents(msg);
 const ink=range.getBoundingClientRect(),clockBox=clock.getBoundingClientRect(),
       mainBox=main.getBoundingClientRect(),style=getComputedStyle(msg);
 return {text:msg.textContent,kind:msg.className,
  font:parseFloat(style.fontSize),lineHeight:parseFloat(style.lineHeight),
  glyphTop:ink.top,glyphBottom:ink.bottom,glyphLeft:ink.left,glyphRight:ink.right,
  clockBottom:clockBox.bottom,mainBottom:mainBox.bottom,mainLeft:mainBox.left,
  mainRight:mainBox.right,scrollWidth:msg.scrollWidth,clientWidth:msg.clientWidth,
  scrollHeight:msg.scrollHeight,clientHeight:msg.clientHeight};
}"""
GALLERY="""()=>{
 const card=[...document.querySelectorAll('.screenPreviewCard')].find(
   c=>c.querySelector('.spHeader h3')?.textContent==='Message temporaire');
 const d=card?.querySelector('iframe')?.contentDocument,msg=d?.querySelector('#msg');
 if(!msg)return null;
 const range=d.createRange();range.selectNodeContents(msg);
 const ink=range.getBoundingClientRect(),box=msg.getBoundingClientRect(),
       style=getComputedStyle(msg);
 return {text:msg.textContent,kind:msg.className,
  font:parseFloat(style.fontSize),lineHeight:parseFloat(style.lineHeight),
  glyphTop:ink.top,glyphBottom:ink.bottom,msgTop:box.top,msgBottom:box.bottom,
  scrollWidth:msg.scrollWidth,clientWidth:msg.clientWidth,
  scrollHeight:msg.scrollHeight,clientHeight:msg.clientHeight};
}"""

def verify_mini(a,where):
 assert a and a["text"]==TEXT,(where,a)
 assert "roundMessageTemporary" in a["kind"],(where,a)
 assert abs(a["lineHeight"]/a["font"]-1.12)<.025,(where,a)
 assert a["glyphTop"]>=a["clockBottom"]+5,(where,a)
 assert a["glyphBottom"]<=a["mainBottom"]-4,(where,a)
 assert a["glyphLeft"]>=a["mainLeft"]-1 and a["glyphRight"]<=a["mainRight"]+1,(where,a)
 assert a["scrollWidth"]<=a["clientWidth"]+2,(where,a)
 assert a["scrollHeight"]<=a["clientHeight"]+2,(where,a)

with sync_playwright() as pw:
 if os.name=="nt":
  browser=pw.chromium.launch(channel="msedge",headless=True)
 else:
  browser=pw.chromium.launch(executable_path=shutil.which("chromium") or shutil.which("chromium-browser"),
                             headless=True,args=["--no-sandbox"])
 for width,height in ((812,490),(1280,720),(1650,930),(1920,1080)):
  page=browser.new_page(viewport={"width":width,"height":height})
  errors=[]
  page.on("pageerror",lambda err:errors.append(str(err)))
  page.set_content(html,wait_until="domcontentloaded")
  page.evaluate(SETUP,TEXT)
  live=page.evaluate(MAIN)
  assert live["text"]==TEXT
  assert abs(live["lineHeight"]/live["font"]-.72)<.03,(width,height,live)

  page.evaluate("showSettings(false);syncFaithfulMini(true)")
  page.wait_for_function("""()=>
    !!document.querySelector('#faithfulMiniFrame')?.contentDocument?.querySelector('#msg')""",timeout=20000)
  page.evaluate("syncFaithfulMini(true)")
  verify_mini(page.evaluate(MINI),("mini",width,height))

  # The existing ten-card test gallery uses immutable 1600x900 snapshots.
  page.evaluate("document.body.classList.add('debugMode');_osp()")
  page.wait_for_function("""()=>{
   const frames=[...document.querySelectorAll('.screenPreviewCard iframe')];
   return frames.length===10 && frames.every(f=>!!f.contentDocument?.querySelector('#msg'));
  }""",timeout=20000)
  gallery=page.evaluate(GALLERY)
  assert gallery and gallery["text"]==TEXT,(width,height,gallery)
  assert abs(gallery["lineHeight"]/gallery["font"]-1.12)<.025,(width,height,gallery)
  assert gallery["scrollHeight"]<=gallery["clientHeight"]+3,(width,height,gallery)
  assert gallery["glyphBottom"]<=gallery["msgBottom"]+3,(width,height,gallery)
  assert gallery["glyphTop"]>=gallery["msgTop"]-4,(width,height,gallery)

  # Single-preview mode is not a gallery iframe: it needs the same fix.
  page.evaluate("_ssp('temporary')")
  single=page.evaluate(MAIN)
  assert single["text"]==TEXT,(width,height,single)
  assert abs(single["lineHeight"]/single["font"]-1.12)<.025,(width,height,single)

  # Close test screens and return to the real timer: unchanged old line-height.
  page.evaluate("_csp();showTimer()")
  normal=page.evaluate(MAIN)
  assert normal["text"]==TEXT,(width,height,normal)
  assert abs(normal["lineHeight"]/normal["font"]-.72)<.03,(width,height,normal)
  assert not errors,(width,height,errors)
  page.close()

 browser.close()
print("Temporary mini + gallery + single-preview fitting, no overlap; full timer unchanged: PASS")
