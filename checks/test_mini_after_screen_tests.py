"""Screen-test gallery must not leak its temporary styles into Settings mini.

Run a match, visit Screen Tests, switch between overview and individual
preview, then return. Previously mini clock retained the gallery's enlarged
font and translation (overlapping board announcement).
"""
from pathlib import Path
import os, shutil
from playwright.sync_api import sync_playwright

html=(Path(__file__).resolve().parents[1]/"timer.html").read_text(encoding="utf-8")
html=html.replace("localStorage","testGalleryStorage").replace("</style></head><body>",
 """</style><script>const testGalleryStorage={data:{},getItem(k){return this.data[k]??null},
 setItem(k,v){this.data[k]=v},removeItem(k){delete this.data[k]}};</script></head><body>""",1)
SETUP="""fullscreen=>{
 Object.assign(s,{mode:'4',positions:6,pairCount:26,boardProgressNotice:true,boards:8,
  boardMinutes:7,boardSeconds:30,eventName:'AAAA',hours:1,minutes:0,seconds:0,sound:false});
 Object.assign(st,{started:true,running:true,phase:'round',remaining:3502,
  roundDuration:3600,pos:1,roundBoards:8,roundBoardDuration:450,longClockAtStart:true});
 if(fullscreen)q25(true);
 showTimer();render();showSettings(false);
 document.querySelector('#boardProgressNotice').checked=true;
 s.boardProgressNotice=true;render();syncFaithfulMini(true);
}"""
CHECK="""()=>{
 const ids=['clock','msg','status','submsg','bar'];
 const inline=Object.fromEntries(ids.map(id=>[id,document.getElementById(id).getAttribute('style')]));
 const d=document.getElementById('faithfulMiniFrame')?.contentDocument,
  c=d?.getElementById('clock'),m=d?.getElementById('msg');
 if(!c||!m)return {err:'mini-preview unavailable'};
 const rect=e=>{const r=e.getBoundingClientRect();return {top:r.top,bottom:r.bottom,
    left:r.left,right:r.right,width:r.width,height:r.height}};
 const range=d.createRange();range.selectNodeContents(m);
 return {inline,clockInline:c.getAttribute('style'),msgInline:m.getAttribute('style'),
  clock:rect(c),msg:rect(m),ink:rect(range),msgText:m.textContent,
  settingsLive:document.body.classList.contains('settingsLive')};
}"""
with sync_playwright() as pw:
 if os.name=='nt':
  browser=pw.chromium.launch(channel='msedge',headless=True)
 else:
  browser=pw.chromium.launch(executable_path=shutil.which('chromium') or shutil.which('chromium-browser'),
                             headless=True,args=['--no-sandbox'])
 for width,height,fullscreen in [(1650,930,True),(1280,720,False),(812,490,False),(1920,1080,True)]:
  page=browser.new_page(viewport={'width':width,'height':height})
  errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
  page.set_content(html,wait_until='domcontentloaded')
  page.wait_for_function("typeof recoveryArmed!=='undefined'&&recoveryArmed")
  page.evaluate(SETUP,fullscreen)
  page.wait_for_function("!!document.querySelector('#faithfulMiniFrame')?.contentDocument?.querySelector('#clock')")
  page.evaluate("syncFaithfulMini(true)")
  before=page.evaluate(CHECK)
  assert before["msgText"]=="Vous êtes censés jouer la donne 1",(width,height,before)
  for iteration in range(2):
   page.evaluate("document.body.classList.add('debugMode');_osp()")
   assert page.locator(".screenPreviewCard").count()==10,(width,height,iteration)
   page.evaluate("_ssp('board')")
   page.evaluate("_ssp('all')")
   page.evaluate("_csp()")
   page.wait_for_function("document.body.classList.contains('settingsLive')")
   page.evaluate("syncFaithfulMini(true)")
   after=page.evaluate(CHECK)
   assert after["settingsLive"] and not errors,(width,height,after,errors)
   assert after["msgText"]==before["msgText"],(width,height,iteration,after["msgText"])
   for id in ["clock","msg","status","submsg","bar"]:
    assert after["inline"][id]==before["inline"][id],(width,height,iteration,id,before["inline"][id],after["inline"][id])
   assert after["clockInline"]==before["clockInline"],(width,height,iteration,"mini clock style")
   assert after["msgInline"]==before["msgInline"],(width,height,iteration,"mini text style")
   for comp in ("clock","msg","ink"):
    for v in ("top","bottom","left","right","height","width"):
     assert abs(after[comp][v]-before[comp][v])<1.8,(width,height,iteration,comp,v,before[comp][v],after[comp][v])
  page.close()
 browser.close()
print("Mini after Screen Tests: 2 cycles, 4 viewports, clock and message geometry unchanged: PASS")
