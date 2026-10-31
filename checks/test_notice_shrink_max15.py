"""Limit notice-related countdown shrink to 15%, preserving vertical slide.

Run on Edge (Windows) or Chromium (Linux). Check small/large windows,
both start-of-round formats, both short and longer temporary notices.
"""
from pathlib import Path
import os,shutil
from playwright.sync_api import sync_playwright

html=(Path(__file__).resolve().parents[1]/"timer.html").read_text(encoding="utf-8")
html=html.replace("localStorage","cap15Storage").replace("</style></head><body>",
 """</style><script>const cap15Storage={data:{},getItem(k){return this.data[k]??null},
 setItem(k,v){this.data[k]=v},removeItem(k){delete this.data[k]}};</script></head><body>""",1)

SETUP="""longRound=>{
 Object.assign(s,{mode:"4",positions:6,pairCount:26,eventName:"AAAA",
   hours:longRound?1:0,minutes:longRound?5:45,seconds:9,
   boardProgressNotice:false,jumpAdvanceNotice:false,sound:false});
 Object.assign(st,{started:true,running:false,phase:"round",pos:1,
   remaining:longRound?3909:2709,roundDuration:longRound?3909:2709,
   longClockAtStart:longRound});
 showTimer();render();
}"""
METRICS="""()=>{
 const t=document.querySelector("#timer"),c=document.querySelector("#clock"),
       m=document.querySelector("#msg"),computed=getComputedStyle(c);
 const scales=computed.scale.split(/\s+/).map(Number);
 const translation=computed.translate, vertical=translation.match(/(-?\d+(?:\.\d+)?)px\s*$/);
 return {
  active:t.classList.contains("noticeMotionActive"),msg:m.textContent,
  factor:Number(t.style.getPropertyValue("--notice-clock-scale")||1),
  sx:scales[0],sy:scales[1]||scales[0],
  rest:t.style.getPropertyValue("--clock-rest-y"),
  moved:vertical?Number(vertical[1]):0,
  easing:computed.transitionDuration
 };
}"""

with sync_playwright() as pw:
 if os.name=="nt":browser=pw.chromium.launch(channel="msedge",headless=True)
 else:browser=pw.chromium.launch(executable_path=shutil.which("chromium") or shutil.which("chromium-browser"),
   headless=True,args=["--no-sandbox"])
 for width,height in ((812,490),(1280,720),(1600,900),(1920,1080)):
  for longRound in (False,True):
   page=browser.new_page(viewport={"width":width,"height":height})
   errors=[]
   page.on("pageerror",lambda e:errors.append(str(e)))
   page.set_content(html,wait_until="domcontentloaded")
   page.evaluate(SETUP,longRound)
   page.wait_for_timeout(510)
   normal=page.evaluate(METRICS)
   assert normal["factor"]==1 and normal["rest"]=="22px",(width,height,longRound,normal)
   assert abs(normal["sy"]-1.15)<.005,(width,height,longRound,normal)
   for message in (
      "Au prochain tour, les EO sautent une table",
      "Attention à tous les joueurs : prenez le temps de vérifier les étuis avant de passer au tour suivant ; merci de votre coopération"
   ):
    page.evaluate("""text=>{
       s.quickMessage=text;tempMessageUntil=Date.now()+60000;render();
    }""",message)
    after=page.evaluate(METRICS)
    assert after["active"] and after["rest"]=="0px",(width,height,longRound,after)
    assert .85-1e-5<=after["factor"]<=.89+1e-5,(width,height,longRound,after)
    assert "0.42s" in after["easing"],(width,height,longRound,after)
    page.wait_for_timeout(510)
    settled=page.evaluate(METRICS)
    assert abs(settled["sy"]/normal["sy"]-settled["factor"])<.012,(width,height,longRound,normal,settled)
    assert settled["sy"]/normal["sy"]>=.84,(width,height,longRound,settled)
    assert abs(settled["moved"])<.15,(width,height,longRound,settled)
    # A normal ticking refresh must not change scale once stable.
    page.evaluate("st.remaining-=1;render()")
    tick=page.evaluate(METRICS)
    assert abs(tick["sy"]-settled["sy"])<.015,(width,height,longRound,tick,settled)
    page.evaluate("tempMessageUntil=0;render()")
    page.wait_for_timeout(510)
    restored=page.evaluate(METRICS)
    assert restored["factor"]==1 and restored["rest"]=="22px",(width,height,longRound,restored)
    assert abs(restored["sy"]-normal["sy"])<.015,(width,height,longRound,restored,normal)
    assert abs(restored["moved"]-22)<.2,(width,height,longRound,restored)
   assert not errors,(width,height,longRound,errors)
   page.close()
 browser.close()
print("Message shrink <=15%, 420ms vertical motion, both clock formats, long text: PASS")
