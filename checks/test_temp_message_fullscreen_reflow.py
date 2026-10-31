"""Temporary notice keeps the SAME typography after native fullscreen exit/reentry.

Strictly isolated: no changes to board / jump message layout, timer, or mini.
"""
from pathlib import Path
import os, shutil
from playwright.sync_api import sync_playwright

html=(Path(__file__).resolve().parents[1]/"timer.html").read_text(encoding="utf-8")
html=html.replace("localStorage","fullscreenAuditStorage").replace("</style></head><body>",
 """</style><script>const fullscreenAuditStorage={data:{},getItem(k){return this.data[k]??null},
 setItem(k,v){this.data[k]=v},removeItem(k){delete this.data[k]}};</script></head><body>""",1)

TEXT="Au prochain tour, les EO sautent une table"
INIT="""msg=>{
 Object.assign(s,{mode:"4",positions:6,pairCount:26,eventName:"AAAA",
   boardProgressNotice:false,jumpAdvanceNotice:false,quickMessage:msg,quickMessageSecs:99,sound:false});
 Object.assign(st,{started:true,running:true,phase:"round",remaining:3599,
   roundDuration:3600,pos:1,longClockAtStart:true,roundBoards:8});
 showTimer();
 s.quickMessage=msg;
 tempMessageUntil=Date.now()+60000;
 render();
}"""
MEASURE="""()=>{
 const e=document.querySelector('#msg'),t=document.querySelector('#timer');
 const style=getComputedStyle(e),rg=document.createRange();rg.selectNodeContents(e);
 const ink=rg.getBoundingClientRect(),rect=e.getBoundingClientRect(),
       clock=document.querySelector('#clock').getBoundingClientRect();
 return {
  text:e.textContent,kind:e.className,
  fs:document.body.classList.contains('fs'),whiteSpace:style.whiteSpace,
  font:parseFloat(style.fontSize),lineHeight:parseFloat(style.lineHeight),
  ink:ink.toJSON(),box:rect.toJSON(),clock:clock.toJSON(),
  scrollWidth:e.scrollWidth,clientWidth:e.clientWidth,
  scrollHeight:e.scrollHeight,clientHeight:e.clientHeight,
  cache:lrf,stageScale:parseFloat(t.style.getPropertyValue('--stage-scale'))
 };
}"""

def stable(a,at):
 assert a["text"]==TEXT,(at,a)
 assert "roundMessageTemporary" in a["kind"],(at,a)
 assert a["whiteSpace"]=="nowrap",(at,a)
 assert abs(a["lineHeight"]/a["font"]-.72)<.03,(at,a)
 assert a["ink"]["left"]>=a["box"]["left"]-2,(at,a)
 assert a["ink"]["right"]<=a["box"]["right"]+2,(at,a)
 # The clock element's box extends below its visible glyphs; allow its
 # known line-box descender area, but never let text escape its message band.
 assert a["ink"]["top"]>=a["clock"]["bottom"]-20*a["stageScale"],(at,a)
 assert a["ink"]["top"]>=a["box"]["top"]-3,(at,a)
 assert a["ink"]["bottom"]<=a["box"]["bottom"]+3,(at,a)
 assert a["scrollWidth"]<=a["clientWidth"]+2,(at,a)
 assert a["scrollHeight"]<=a["clientHeight"]+3,(at,a)

with sync_playwright() as pw:
 if os.name=="nt":
  browser=pw.chromium.launch(channel="msedge",headless=True)
 else:
  browser=pw.chromium.launch(executable_path=shutil.which("chromium") or shutil.which("chromium-browser"),
                             headless=True,args=["--no-sandbox"])
 for width,height in ((1280,720),(1600,900),(1920,1080)):
  page=browser.new_page(viewport={"width":width,"height":height})
  errors=[]
  page.on("pageerror",lambda e:errors.append(str(e)))
  page.set_content(html,wait_until="domcontentloaded")
  page.evaluate(INIT,TEXT)
  page.evaluate("q25(true);render()")
  page.wait_for_timeout(100)
  first=page.evaluate(MEASURE)
  stable(first,("initial",width,height))

  for round in range(3):
   page.set_viewport_size({"width":812,"height":490})
   page.evaluate("q25(false)")
   page.wait_for_timeout(100)
   during=page.evaluate(MEASURE)
   stable(during,("windowed",width,height,round))

   page.set_viewport_size({"width":width,"height":height})
   page.evaluate("q25(true)")
   page.wait_for_timeout(100)
   after=page.evaluate(MEASURE)
   stable(after,("back-fullscreen",width,height,round))
   assert abs(after["font"]-first["font"])<=1.3,(width,height,first,after)
   assert abs(after["ink"]["height"]-first["ink"]["height"])<=1.3,(width,height,first,after)

  # Ultra-long text may wrap, but only with safe vertical spacing.
  page.evaluate("""()=>{
   s.quickMessage='Attention : changement exceptionnel de direction et de position pour toutes les tables concernées par le tournoi de cet après-midi';
   render();
  }""")
  extended=page.evaluate(MEASURE)
  assert extended["text"].startswith("Attention : changement"),extended
  if extended["whiteSpace"]=="normal":
   assert abs(extended["lineHeight"]/extended["font"]-1.12)<.03,extended
  assert extended["scrollHeight"]<=extended["clientHeight"]+3,extended
  assert not errors,(width,height,errors)
  page.close()
 browser.close()
print("Temporary notice stable over 3 fullscreen cycles at 3 sizes; long text safe: PASS")
