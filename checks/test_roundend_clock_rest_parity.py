"""Visual regression: FIN DU TOUR and FIN DE LA SEANCE retain the
same clock size/position as a normal, message-free round or Pause.

Exercises both formats, two finish phases and native Windows Edge viewport
sizes. Compares CSS properties AND actual element rectangles after easing.
"""
from pathlib import Path
import os,shutil
from playwright.sync_api import sync_playwright

html=(Path(__file__).resolve().parents[1]/"timer.html").read_text(encoding="utf-8")
html=html.replace("localStorage","endParityStorage").replace("</style></head><body>",
 """</style><script>const endParityStorage={data:{},getItem(k){return this.data[k]??null},
 setItem(k,v){this.data[k]=v},removeItem(k){delete this.data[k]}};</script></head><body>""",1)

SETUP="""mode=>{
 Object.assign(s,{mode,positions:6,pairCount:26,
  eventName:"Senior Mixte /2 - Finale de Comité",
  hours:0,minutes:45,seconds:0,boardProgressNotice:false,
  jumpAdvanceNotice:false,sound:false});
 Object.assign(st,{started:true,running:true,phase:"round",pos:1,
  remaining:2,roundDuration:2700,longClockAtStart:false});
 tempMessageUntil=0;s.quickMessage="";
 showTimer();render();
}"""
SAMPLE="""()=>{
 const t=document.querySelector("#timer"),c=document.querySelector("#clock"),
   title=document.querySelector("#status"),main=t.querySelector(".main"),
   resume=document.querySelector("#finishResume");
 const rect=e=>{const r=e.getBoundingClientRect();return {
   x:r.x,y:r.y,width:r.width,height:r.height,
   top:r.top,bottom:r.bottom,left:r.left,right:r.right}};
 const scale=getComputedStyle(c).scale.split(/\s+/).map(Number);
 const translate=getComputedStyle(c).translate;
 return {phase:st.phase,clockText:c.textContent,
  title:rect(title),clock:rect(c),main:rect(main),
  scaleX:scale[0],scaleY:scale.at(-1),translate,
  factor:Number(t.style.getPropertyValue("--notice-clock-scale")||1),
  rest:t.style.getPropertyValue("--clock-rest-y"),
  ended:document.querySelector("#finishOverlay").classList.contains("on"),
  resume:rect(resume),resumeScrollable:resume.scrollWidth>resume.clientWidth+2,
  snapshot:t.classList.contains("noticeMotionSnapshot")};
}"""

def compare(baseline,finished,label):
 assert finished["ended"],(label,finished)
 assert finished["factor"]==1 and finished["rest"]=="22px",(label,finished)
 for key in ("scaleX","scaleY"):
  assert abs(baseline[key]-finished[key])<.015,(label,key,baseline,finished)
 assert baseline["translate"]==finished["translate"],(label,"translation",baseline,finished)
 for element in ("clock","title"):
  for key in ("x","y","width","height"):
   diff=abs(baseline[element][key]-finished[element][key])
   assert diff<1.0,(label,element,key,diff,baseline,finished)
 assert finished["resume"]["bottom"]<=finished["main"]["bottom"]+2,(label,finished)
 assert not finished["resumeScrollable"],(label,"resume text too wide",finished)

with sync_playwright() as pw:
 if os.name=="nt":
  browser=pw.chromium.launch(channel="msedge",headless=True)
 else:
  browser=pw.chromium.launch(executable_path=shutil.which("chromium") or shutil.which("chromium-browser"),
   headless=True,args=["--no-sandbox"])
 for width,height in ((812,490),(1280,720),(1600,900),(1920,1080)):
  for mode in ("4","2"):
   page=browser.new_page(viewport={"width":width,"height":height})
   errors=[];page.on("pageerror",lambda e:errors.append(str(e)))
   page.set_content(html,wait_until="domcontentloaded")
   page.evaluate(SETUP,mode)
   page.wait_for_timeout(550)
   live=page.evaluate(SAMPLE)
   assert not live["ended"] and abs(live["scaleY"]-1.15)<.015,(width,height,mode,live)
   # Pause should keep same clock at rest (no notice).
   page.evaluate("pause()");page.wait_for_timeout(520)
   paused=page.evaluate(SAMPLE)
   for key in ("x","y","width","height"):
    assert abs(paused["clock"][key]-live["clock"][key])<1,(width,height,mode,key,paused,live)
   # End of MP4 tour vs end of Paires session: same geometry as live timer.
   endPhase="roundEnd" if mode=="4" else "ended"
   page.evaluate("""phase=>{
     st.phase=phase;st.running=false;
     st.roundEndSince=performance.now()-1500;render();
   }""",endPhase)
   page.wait_for_timeout(550)
   end=page.evaluate(SAMPLE)
   compare(live,end,(width,height,mode))
   # The 1600x900 sample stage must also preserve the enlarged end clock
   # when rendered statically for a Screen Tests preview.
   page.evaluate("document.body.classList.add('debugMode');showSettings(false);_osp()")
   page.wait_for_function("""()=>{
    const cards=[...document.querySelectorAll(".screenPreviewCard iframe")];
    return cards.length===10&&cards.every(f=>f.contentDocument?.getElementById("clock"))
   }""",timeout=20000)
   sample=page.evaluate("""mode=>{
     const title=mode==="4"?"Fin du tour (Match par 4)":"Fin de la séance (Paires)";
     const card=[...document.querySelectorAll(".screenPreviewCard")].find(x=>
      x.querySelector(".spHeader h3")?.textContent===title);
     const c=card?.querySelector("iframe")?.contentDocument?.getElementById("clock");
     return c?{scaleY:Number(getComputedStyle(c).scale.split(/\s+/).at(-1)),
      transition:getComputedStyle(c).transitionDuration}:null;
   }""",mode)
   assert sample and abs(sample["scaleY"]-1.15)<.015,(width,height,mode,sample)
   assert "0s" in sample["transition"],(width,height,mode,sample)
   assert not errors,(width,height,mode,errors)
   page.close()
 browser.close()
print("END-SCREEN PARITY PASS: 8 window/mode combinations, clock/title identical and resume line visible")
