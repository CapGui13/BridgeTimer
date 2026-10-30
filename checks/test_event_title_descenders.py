"""The event name must show complete g/p/q descenders without resizing the timer.

Compare real Edge pixels just below the legacy title box. Hidden overflow
cuts the descenders; CSS clip margin must reveal them. Preserve ellipsis.
"""
from pathlib import Path
import io, math, os, shutil
from PIL import Image
from playwright.sync_api import sync_playwright

html=(Path(__file__).resolve().parents[1]/"timer.html").read_text(encoding="utf-8")
html=html.replace("localStorage","bridgeAuditStorage").replace(
 "</style></head><body>",
 """</style><script>const bridgeAuditStorage={data:{},
 getItem(k){return this.data[k]??null},
 setItem(k,v){this.data[k]=v},removeItem(k){delete this.data[k]}};
 </script></head><body>""",1)

def measure(page):
 return page.evaluate("""()=>{
  const t=$('status').getBoundingClientRect(),c=$('clock').getBoundingClientRect();
  const css=getComputedStyle($('status'));
  return {status:[t.x,t.y,t.width,t.height,t.bottom],
   clock:[c.x,c.y,c.width,c.height],
   font:getComputedStyle($('clock')).fontSize,
   transform:getComputedStyle($('clock')).transform,
   slot:$('status').offsetHeight,
   overflow:css.overflow,margin:css.overflowClipMargin};
 }""")

def pixels_below(page, status):
 im=Image.open(io.BytesIO(page.screenshot())).convert("RGB")
 x,y,w,h,bottom=status["status"]
 y_start=max(0,math.ceil(bottom))
 y_stop=min(im.height,math.floor(bottom+12))
 x_start=max(0,math.floor(x))
 x_stop=min(im.width,math.ceil(x+w))
 return sum(1 for j in range(y_start,y_stop) for i in range(x_start,x_stop)
   if min(im.getpixel((i,j)))>215)

with sync_playwright() as pw:
 if os.name=="nt":
  browser=pw.chromium.launch(channel="msedge",headless=True)
 else:
  browser=pw.chromium.launch(
   executable_path=shutil.which("chromium") or shutil.which("chromium-browser"),
   headless=True,args=["--no-sandbox"])

 for width,height in ((960,720),(1600,900),(1920,1080)):
  for fullscreen in (False,True):
   page=browser.new_page(viewport={"width":width,"height":height})
   errors=[]
   page.on("pageerror",lambda e:errors.append(str(e)))
   page.set_content(html,wait_until="domcontentloaded")
   page.evaluate("""(fullscreen)=>{
    Object.assign(s,{eventName:"Cucksleague - Final",mode:"2",positions:13,
      hours:0,minutes:14,seconds:28,boards:8,boardProgressNotice:true});
    Object.assign(st,{started:true,running:true,phase:"round",remaining:868,
      pos:1,roundDuration:1800,roundBoards:8,roundBoardDuration:225,longClockAtStart:false});
    $("settings").classList.add("hidden");
    $("timer").classList.remove("hidden");
    q25(fullscreen);render();
   }""",fullscreen)
   original=measure(page)
   assert original["overflow"]=="clip" and "10px" in original["margin"],original

   # What the former "overflow:hidden" rule did, measured on the same frame.
   page.evaluate("""()=>{$('status').style.overflow='hidden'}""")
   clipped=measure(page)
   before=pixels_below(page,clipped)

   page.evaluate("""()=>{$('status').style.removeProperty('overflow')}""")
   restored=measure(page)
   after=pixels_below(page,restored)
   assert after>=before+12,(
     width,height,fullscreen,"Title descenders are still cut",before,after,restored)
   assert original["slot"]==clipped["slot"]==restored["slot"],(
     width,height,fullscreen,"Title reserved height changed",original,clipped,restored)
   assert original["clock"]==clipped["clock"]==restored["clock"],(
     width,height,fullscreen,"Timer digits moved when title unclipped",original,clipped,restored)
   assert original["font"]==clipped["font"]==restored["font"]
   assert original["transform"]==clipped["transform"]==restored["transform"]

   # Text overflow ellipsis is retained for exceptionally long event names.
   page.evaluate("""()=>{
    s.eventName="Cucksleague - Finale extraordinaire de la fédération de bridge, "+
     "une compétition internationale avec cent participants à travers la Provence";
    render();
   }""")
   ellipse=page.evaluate("""()=>{
    const e=$('status'),css=getComputedStyle(e);
    return {over:e.scrollWidth>e.clientWidth,ellipsis:css.textOverflow,
      slot:e.offsetHeight};
   }""")
   assert ellipse["over"] and ellipse["ellipsis"]=="ellipsis",(
    width,height,fullscreen,"Long event title lost ellipsis",ellipse)
   assert ellipse["slot"]==original["slot"],(
    width,height,fullscreen,"Long event name resized title slot",ellipse,original)
   assert not errors,(width,height,fullscreen,errors)
   page.close()
 browser.close()
print("Full event-title descenders, ellipsis and invariant timer geometry verified")
