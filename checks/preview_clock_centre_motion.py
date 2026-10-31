from pathlib import Path
from playwright.sync_api import sync_playwright
html=Path("timer.html").read_text(encoding="utf-8")
html=html.replace("localStorage","previewStorage").replace("</style></head><body>",
 """</style><script>const previewStorage={data:{},getItem(k){return this.data[k]??null},
 setItem(k,v){this.data[k]=v},removeItem(k){delete this.data[k]}};</script></head><body>""",1)
out=Path("screenshots");out.mkdir(exist_ok=True)
with sync_playwright() as pw:
 browser=pw.chromium.launch(channel="msedge",headless=True)
 for width,height in ((1600,900),(1280,720),(682,415)):
  for longRound in (False,True):
   page=browser.new_page(viewport={"width":width,"height":height},device_scale_factor=1)
   page.set_content(html,wait_until="domcontentloaded")
   page.evaluate("""longRound=>{
    Object.assign(s,{mode:"4",positions:6,pairCount:26,eventName:"Festival du Roy René",
     hours:longRound?1:0,minutes:longRound?5:45,seconds:9,
     boardProgressNotice:false,jumpAdvanceNotice:false,sound:false});
    Object.assign(st,{started:true,running:false,phase:"round",pos:1,
     remaining:longRound?3909:2709,roundDuration:longRound?3909:2709,
     longClockAtStart:longRound});
    showTimer();render();
   }""",longRound)
   page.wait_for_timeout(600)
   key=f"{width}x{height}_"+("long" if longRound else "short")
   page.screenshot(path=str(out/f"{key}_rest.png"))
   page.evaluate("""()=>{
    s.quickMessage='Au prochain tour, les EO sautent une table';
    tempMessageUntil=Date.now()+60000;render()
   }""")
   page.wait_for_timeout(600)
   page.screenshot(path=str(out/f"{key}_notice.png"))
   page.close()
 browser.close()
