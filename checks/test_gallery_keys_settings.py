"""Regression: full gallery previews remain scrollable and F/F11 work in Settings."""
from pathlib import Path
import os
import shutil
from playwright.sync_api import sync_playwright

html=(Path(__file__).resolve().parents[1]/"timer.html").read_text(encoding="utf-8")
html=html.replace("localStorage","testStorage").replace("</style></head><body>",
 """</style><script>const testStorage={data:{},getItem(k){return this.data[k]??null},
 setItem(k,v){this.data[k]=v},removeItem(k){delete this.data[k]}}</script></head><body>""",1)

with sync_playwright() as pw:
 if os.name=="nt":
  browser=pw.chromium.launch(channel="msedge",headless=True)
 else:
  browser=pw.chromium.launch(executable_path=shutil.which("chromium") or shutil.which("chromium-browser"),headless=True,args=["--no-sandbox"])

 for width,height in ((812,490),(960,540),(1650,928),(1920,1080)):
  page=browser.new_page(viewport={"width":width,"height":height})
  errors=[]
  page.on("pageerror",lambda e:errors.append(str(e)))
  page.set_content(html,wait_until="domcontentloaded")
  page.evaluate("""()=>{
   document.body.classList.add('debugMode');
   Object.assign(s,{mode:'2',positions:6,eventName:'Gallery Regression'});
   Object.assign(st,{started:true,running:false,phase:'round',
     remaining:3598,pos:1,roundDuration:3600,roundBoards:8});
   showSettings(false);_osp();
  }""")
  page.wait_for_timeout(250)
  assert page.locator(".screenPreviewCard").count()==10,(width,height,"Expected all ten previews")
  page.evaluate("document.querySelector('#spg').scrollTop=document.querySelector('#spg').scrollHeight")
  page.wait_for_timeout(120)
  measurements=page.evaluate("""()=>{
   const gallery=document.querySelector('#spg'),card=gallery.lastElementChild;
   const frame=card.querySelector('iframe'),pane=card.querySelector('.pv');
   const doc=frame.contentDocument;
   const r=e=>e.getBoundingClientRect();
   return {
     cardBottom:r(card).bottom,
     galleryBottom:r(gallery).bottom,
     frameWidth:r(frame).width,
     paneWidth:r(pane).width,
     frameBottom:doc.querySelector('#timer .bottom').getBoundingClientRect().bottom,
     timerBottom:doc.querySelector('#timer').getBoundingClientRect().bottom
   };
  }""")
  assert measurements["galleryBottom"]<=height+1,(width,height,measurements)
  assert measurements["cardBottom"]<=measurements["galleryBottom"]-7,(width,height,measurements)
  assert abs(measurements["frameWidth"]-measurements["paneWidth"])<1,(width,height,measurements)
  assert abs(measurements["frameBottom"]-measurements["timerBottom"])<1,(width,height,measurements)
  assert not errors,(width,height,errors)
  page.close()

 for live in (False,True):
  page=browser.new_page(viewport={"width":812,"height":490})
  errors=[]
  page.on("pageerror",lambda e:errors.append(str(e)))
  page.set_content(html,wait_until="domcontentloaded")
  page.evaluate("""live=>{
   window.__full=false;window.__toggleCount=0;
   window.nativeFullscreen=()=>{
     window.__toggleCount++;
     window.__full=!window.__full;
     return Promise.resolve(window.__full);
   };
   if(live){
     Object.assign(st,{started:true,phase:'round',running:false,remaining:2400,roundDuration:3600});
     showTimer();showSettings(false);
   }
  }""",live)
  assert page.locator("#settings").is_visible()
  for key,count,fullscreen in (("f",1,True),("F",2,False)):
   page.keyboard.press(key)
   page.wait_for_function("n=>window.__toggleCount===n && !fif",arg=count)
   assert page.evaluate("document.body.classList.contains('fs')")==fullscreen
   assert page.locator("#settings").is_visible()
  page.locator("#clubName").focus()
  page.keyboard.press("f")
  assert page.evaluate("window.__toggleCount")==2,"F must remain an ordinary letter in text fields"
  for count,fullscreen in ((3,True),(4,False)):
   page.keyboard.press("F11")
   page.wait_for_function("n=>window.__toggleCount===n && !fif",arg=count)
   assert page.evaluate("document.body.classList.contains('fs')")==fullscreen
   assert page.locator("#settings").is_visible()
  assert not errors,(live,errors)
  page.close()
 browser.close()
print("Gallery: all 10 full 16:9 previews, bottom visible at 4 sizes; Settings F/F11: OK")
