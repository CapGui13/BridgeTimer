"""Regression: notice layout must remain fixed while countdown scale animates.

The old placement read getBoundingClientRect() on an animated clock; every
countdown tick could move the notice box and rewrap a one-line message.
"""
from pathlib import Path
import os,shutil
from playwright.sync_api import sync_playwright

html=(Path(__file__).resolve().parents[1]/"timer.html").read_text(encoding="utf-8")
html=html.replace("localStorage","reflowStorage").replace("</style></head><body>",
 """</style><script>const reflowStorage={data:{},getItem(k){return this.data[k]??null},
 setItem(k,v){this.data[k]=v},removeItem(k){delete this.data[k]}};</script></head><body>""",1)
TEXT="Au prochain tour, les EO sautent une table"

INIT="""longRound=>{
 Object.assign(s,{mode:'4',positions:6,pairCount:26,eventName:'AAAA',
  hours:longRound?1:0,minutes:longRound?0:45,seconds:0,
  boardProgressNotice:false,jumpAdvanceNotice:false,sound:false});
 Object.assign(st,{started:true,phase:'round',running:false,
  remaining:longRound?3599:2699,
  roundDuration:longRound?3600:2700,roundBoards:8,pos:1,
  longClockAtStart:longRound});
 showTimer();render();
}"""
MEASURE="""()=>{
 const t=document.querySelector('#timer'),msg=document.querySelector('#msg'),
  clock=document.querySelector('#clock'),cs=getComputedStyle(msg);
 const range=document.createRange();range.selectNodeContents(msg);
 const lines=[...range.getClientRects()].filter(r=>r.width>0.5&&r.height>0.5);
 const box=msg.getBoundingClientRect(),clockBox=clock.getBoundingClientRect();
 const round=v=>Math.round(v*100)/100;
 return {text:msg.textContent,kind:msg.className,scale:getComputedStyle(clock).scale,
  top:msg.style.top,height:msg.style.height,
  font:msg.style.fontSize,whiteSpace:msg.style.whiteSpace,lineHeight:cs.lineHeight,
  lines:lines.length,boxTop:round(box.top),boxHeight:round(box.height),
  clockBottom:round(clockBox.bottom),opacity:cs.opacity,
  active:t.classList.contains('noticeMotionActive')};
}"""

with sync_playwright() as pw:
 if os.name=="nt":browser=pw.chromium.launch(channel="msedge",headless=True)
 else:browser=pw.chromium.launch(executable_path=shutil.which("chromium") or shutil.which("chromium-browser"),
                                  headless=True,args=["--no-sandbox"])
 for w,h in ((812,490),(1280,720),(1600,900),(1920,1080)):
  for longRound in (False,True):
   page=browser.new_page(viewport={"width":w,"height":h})
   errors=[];page.on("pageerror",lambda e:errors.append(str(e)))
   page.set_content(html,wait_until="domcontentloaded")
   page.evaluate(INIT,longRound)
   page.wait_for_timeout(100)
   page.evaluate("""text=>{
     s.quickMessage=text;tempMessageUntil=Date.now()+60000;render();
   }""",TEXT)
   first=page.evaluate(MEASURE)
   assert first["text"]==TEXT and first["active"],(w,h,longRound,first)
   assert first["lines"]>=1,(w,h,longRound,first)
   # The short message should fit on one line, as on the approved display.
   assert first["whiteSpace"]=="nowrap" and first["lines"]==1,(w,h,longRound,first)
   previousScale=float(first["scale"])
   changed=False
   for n in range(13):
    page.wait_for_timeout(60)
    page.evaluate("st.remaining-=1;render()")
    current=page.evaluate(MEASURE)
    if abs(float(current["scale"])-previousScale)>0.005:changed=True
    previousScale=float(current["scale"])
    for prop in ("top","height","font","whiteSpace","lineHeight","lines","boxTop","boxHeight"):
     if prop in ("boxTop","boxHeight"):
      assert abs(current[prop]-first[prop])<1.15,(w,h,longRound,n,prop,first,current)
     else:
      assert current[prop]==first[prop],(w,h,longRound,n,prop,first,current)
    assert current["text"]==TEXT,(w,h,longRound,n,current)
   assert changed,(w,h,longRound,"the visual clock scale did not animate")
   # On disappearance, no message remains, and the digits regain 100% size.
   page.evaluate("tempMessageUntil=0;render()")
   page.wait_for_timeout(550)
   gone=page.evaluate(MEASURE)
   assert not gone["active"] and gone["text"]=="",(w,h,longRound,gone)
   assert abs(float(gone["scale"])-1)<.01,(w,h,longRound,gone)
   assert not errors,(w,h,longRound,errors)
   page.close()
 browser.close()
print("Notice single line + immutable box and font through 13 ticks / 420ms clock scale: PASS")
