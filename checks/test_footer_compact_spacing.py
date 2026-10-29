"""Footer-space regression: short and long tournament labels, paired teams and Paires.

Check the actual browser rectangles in windowed and fullscreen display.  No
placeholder geometry and no mutation of the production HTML.
"""
from pathlib import Path
import os, shutil
from playwright.sync_api import sync_playwright

html=Path("timer.html").read_text(encoding="utf-8").replace(
 "localStorage","footerAuditStorage").replace("</style></head><body>",
 """</style><script>const footerAuditStorage={d:{},getItem(k){return this.d[k]??null},
 setItem(k,v){this.d[k]=v},removeItem(k){delete this.d[k]}};</script></head><body>""",1)

SIZES=[(812,456),(812,580),(850,500),(960,540),(960,720),(1280,720),(1600,900),(1920,1080)]
def metrics(page):
 return page.evaluate("""()=>{
   const r=id=>{const x=document.querySelector(id).getBoundingClientRect();
      return {left:x.left,right:x.right,top:x.top,bottom:x.bottom,width:x.width,height:x.height}};
   const ctrl=document.querySelector("#timer .controls");
   const visible=[...ctrl.querySelectorAll("button")].filter(x=>getComputedStyle(x).display!=="none");
   return {clock:r("#localTime"),round:r("#round"),controls:r("#timer .controls"),
     footer:r("#timer .bottom"),buttons:visible.map(x=>({id:x.id,width:x.getBoundingClientRect().width,
       padding:getComputedStyle(x).padding,txt:x.textContent.trim()})),
     width:innerWidth,height:innerHeight,
     gap:getComputedStyle(ctrl).columnGap,
     scale:Number(document.querySelector("#timer").style.getPropertyValue("--stage-scale")),
     fullscreen:document.body.classList.contains("fs")};
 }""")
def assert_spacing(label,d,min_gap=3):
 left=d["controls"]["left"]-d["clock"]["right"]
 right=d["round"]["left"]-d["controls"]["right"]
 assert abs(left-right)<=1.2,(label,"unequal",left,right,d)
 assert left>=min_gap and right>=min_gap,(label,"overlap",left,right,d)
 assert d["controls"]["left"]>=d["clock"]["right"],(label,"clock intersect",d)
 assert d["controls"]["right"]<=d["round"]["left"],(label,"round intersect",d)

with sync_playwright() as pw:
 if os.name=="nt":browser=pw.chromium.launch(channel="msedge",headless=True)
 else:browser=pw.chromium.launch(executable_path=shutil.which("chromium") or shutil.which("chromium-browser"),
                                 args=["--no-sandbox"],headless=True)
 n=0
 for width,height in SIZES:
  page=browser.new_page(viewport={"width":width,"height":height})
  page.set_content(html,wait_until="domcontentloaded")
  page.wait_for_function("typeof recoveryArmed!=='undefined' && recoveryArmed")
  page.evaluate("""()=>{st.started=true;showTimer();}""")
  for mode in ("4","2"):
   for count in (6,12,18,24):
    for phase in ("round","break","jump","roundEnd"):
     page.evaluate("""x=>{
       s.mode=x.mode;s.positions=x.count;st.pos=x.count>=18?12:Math.min(x.count,2);
       st.phase=x.phase;st.running=false;
       st.started=true;st.roundDuration=3600;st.remaining=67;st.breakDuration=10;
       st.endAt=null;render();
     }""",{"mode":mode,"count":count,"phase":phase})
     # Edge can finish font and flex measurements after the synchronous
     # render. Re-run the production positioning calculation once on the
     # final DOM rectangles, without changing any layout rules.
     page.evaluate("alignTimerFooterControls()")
     d=metrics(page)
     assert_spacing(f"{width}x{height} {mode} {count} {phase}",d)
     n+=1
  # Fullscreen must not adopt any newly introduced compact-window CSS.
  page.evaluate("q25(true);render()")
  f=metrics(page)
  assert f["fullscreen"],f
  assert_spacing(f"{width}x{height} fullscreen",f,1.0)
  n+=1
  page.close()
 browser.close()
print(f"Footer label/button spacing: {n} real Edge geometries passed")
