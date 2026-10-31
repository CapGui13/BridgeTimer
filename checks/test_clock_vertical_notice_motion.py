"""Bridge Timer: no-message countdown sits lower; eases upward with a notice.

Checks both MM:SS and H:MM:SS, multiple viewports, no title overlap,
independent 1.15 vertical magnification, original 420ms animation, no
per-second restarts and static gallery snapshots.
"""
from pathlib import Path
import os,shutil
from playwright.sync_api import sync_playwright

html=(Path(__file__).resolve().parents[1]/"timer.html").read_text(encoding="utf-8")
html=html.replace("localStorage","verticalMotionStorage").replace("</style></head><body>",
 """</style><script>const verticalMotionStorage={data:{},
 getItem(k){return this.data[k]??null},setItem(k,v){this.data[k]=v},
 removeItem(k){delete this.data[k]}};</script></head><body>""",1)

SETUP="""longRound=>{
 Object.assign(s,{mode:"4",positions:6,pairCount:26,eventName:"Compétition",
  hours:longRound?1:0,minutes:longRound?5:45,seconds:9,
  boardProgressNotice:false,jumpAdvanceNotice:false,sound:false});
 Object.assign(st,{started:true,running:false,phase:"round",
  pos:1,remaining:longRound?3909:2709,roundDuration:longRound?3909:2709,
  longClockAtStart:longRound});
 showTimer();render();
}"""
SAMPLE="""()=>{
 const c=document.querySelector('#clock'),t=document.querySelector('#timer');
 const m=document.querySelector('#msg'),title=document.querySelector('#status');
 const main=document.querySelector('#timer .main');
 const box=e=>{const r=e.getBoundingClientRect();return {
  top:r.top,bottom:r.bottom,left:r.left,right:r.right,height:r.height}};
 const r=document.createRange();r.selectNodeContents(c);
 const translate=getComputedStyle(c).translate;
 const y=/(-?\d+(?:\.\d+)?)px\s*$/.exec(translate);
 return {y:y?Number(y[1]):0,cssTranslate:translate,
  rest:t.style.getPropertyValue('--clock-rest-y'),
  duration:getComputedStyle(c).transitionDuration,
  clock:box(c),ink:box(r),main:box(main),title:box(title),
  scale:getComputedStyle(c).scale,
  text:m.textContent,active:t.classList.contains('noticeMotionActive'),
  ready:t.classList.contains('noticeMotionReady')};
}"""

with sync_playwright() as pw:
 if os.name=="nt":browser=pw.chromium.launch(channel="msedge",headless=True)
 else:browser=pw.chromium.launch(executable_path=shutil.which("chromium") or shutil.which("chromium-browser"),
   headless=True,args=["--no-sandbox"])
 for width,height in ((812,490),(1280,720),(1600,900),(1920,1080)):
  for longRound in (False,True):
   page=browser.new_page(viewport={"width":width,"height":height})
   errors=[];page.on("pageerror",lambda e:errors.append(str(e)))
   page.set_content(html,wait_until="domcontentloaded")
   page.evaluate(SETUP,longRound)
   page.wait_for_timeout(510)
   initial=page.evaluate(SAMPLE)
   assert initial['ready'] and not initial['active'],(width,height,longRound,initial)
   assert initial['rest']=="22px" and abs(initial['y']-22)<.15,(width,height,longRound,initial)
   assert "0.42s" in initial['duration'],(width,height,longRound,initial)
   # Any future re-render of ticking seconds must not restart animations.
   page.evaluate("st.remaining-=1;render()")
   assert abs(page.evaluate(SAMPLE)['y']-22)<.15,(width,height,longRound)
   page.evaluate("""()=>{
    s.quickMessage='Au prochain tour, les EO sautent une table';
    tempMessageUntil=Date.now()+60000;render();
   }""")
   page.wait_for_timeout(110)
   middle=page.evaluate(SAMPLE)
   assert middle['active'] and middle['rest']=="0px",(width,height,longRound,middle)
   assert 0<middle['y']<22,(width,height,longRound,middle)
   page.wait_for_timeout(460)
   up=page.evaluate(SAMPLE)
   assert abs(up['y'])<.15,(width,height,longRound,up)
   assert up['ink']['top']>=up['title']['bottom']-9,(width,height,longRound,up)
   # After the message vanishes, countdown moves DOWN as it grows.
   page.evaluate("tempMessageUntil=0;render()")
   page.wait_for_timeout(100)
   goingDown=page.evaluate(SAMPLE)
   assert goingDown['rest']=="22px" and 0<goingDown['y']<22,(width,height,longRound,goingDown)
   page.wait_for_timeout(480)
   back=page.evaluate(SAMPLE)
   assert abs(back['y']-22)<.15,(width,height,longRound,back)
   assert not errors,(width,height,longRound,errors)
   page.close()
 browser.close()
print("Clock lower at rest, 420ms smooth rise/fall on notice, short and long modes: PASS")
