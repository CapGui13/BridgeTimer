"""BridgeTimer trial: four visual regressions (10% resize, Pause, previews, ending title).

Tests true live countdown state and frozen gallery/mini states under Windows Edge.
Never changes application code or commits: assertions only.
"""
from pathlib import Path
import os,shutil
from playwright.sync_api import sync_playwright

html=(Path(__file__).resolve().parents[1]/"timer.html").read_text(encoding="utf-8")
html=html.replace("localStorage","fourAuditStorage").replace("</style></head><body>",
 """</style><script>const fourAuditStorage={data:{},getItem(k){return this.data[k]??null},
 setItem(k,v){this.data[k]=v},removeItem(k){delete this.data[k]}};</script></head><body>""",1)

SETUP="""isLong=>{
 Object.assign(s,{mode:"2",positions:6,eventName:"Compétition",
  hours:isLong?1:0,minutes:isLong?5:45,seconds:9,
  boardProgressNotice:false,jumpAdvanceNotice:false,sound:false});
 const duration=isLong?3909:2709;
 Object.assign(st,{started:true,running:true,phase:"round",pos:1,
  remaining:duration,endAt:performance.now()+duration*1000,
  roundDuration:duration,longClockAtStart:isLong,roundEndSince:null});
 s.quickMessage="";tempMessageUntil=0;
 showTimer();render();
}"""
SAMPLE="""()=>{
 const id=x=>document.getElementById(x),t=id("timer"),c=id("clock"),title=id("status");
 const b=e=>{const r=e.getBoundingClientRect();return {x:r.x,y:r.y,width:r.width,
   height:r.height,top:r.top,bottom:r.bottom,left:r.left,right:r.right}};
 const cs=getComputedStyle(c),scale=cs.scale.split(/\\s+/).map(Number);
 return {factor:Number(t.style.getPropertyValue("--notice-clock-scale")||"1"),
  rest:t.style.getPropertyValue("--clock-rest-y"),scaleX:scale[0],scaleY:scale.at(-1),
  active:t.classList.contains("noticeMotionActive"),
  paused:id("pauseOverlay").classList.contains("on"),
  ended:id("finishOverlay").classList.contains("on"),
  phase:st.phase,title:b(title),clock:b(c),msg:b(id("msg")),
  titleTransform:getComputedStyle(title).transform};
}"""

def near(a,b,tol=1):
 return abs(a-b)<tol
def stable_title(a,b,where):
 for key in ("x","y","width","height"):
  assert near(a["title"][key],b["title"][key],.8),(where,key,a["title"],b["title"])

with sync_playwright() as pw:
 if os.name=="nt":browser=pw.chromium.launch(channel="msedge",headless=True)
 else:browser=pw.chromium.launch(executable_path=shutil.which("chromium") or shutil.which("chromium-browser"),
   headless=True,args=["--no-sandbox"])
 for w,h in ((812,490),(1600,900),(1920,1080)):
  for longClock in (False,True):
   tag=(w,h,"long" if longClock else "short")
   page=browser.new_page(viewport={"width":w,"height":h})
   errors=[];page.on("pageerror",lambda e:errors.append(str(e)))
   page.set_content(html,wait_until="domcontentloaded")
   page.evaluate(SETUP,longClock)
   page.wait_for_timeout(490)
   initial=page.evaluate(SAMPLE)
   assert near(initial["scaleY"],1.15,.012) and initial["rest"]=="22px", (tag,initial)
   # 1. Any message -> at most 10% shrink; actual Pause restores full scale
   # even with the temporary announcement still stored/displayed.
   page.evaluate("""()=>{
    s.quickMessage="Au prochain tour, les EO sautent une table";
    tempMessageUntil=Date.now()+60000;render();
   }""")
   page.wait_for_timeout(500)
   message=page.evaluate(SAMPLE)
   assert message["active"] and .90-1e-5<=message["factor"]<=1,(tag,message)
   page.evaluate("pause()")
   page.wait_for_timeout(520)
   paused=page.evaluate(SAMPLE)
   assert paused["paused"] and not paused["active"],(tag,paused)
   assert paused["factor"]==1 and paused["rest"]=="22px",(tag,paused)
   assert near(paused["scaleY"],initial["scaleY"],.017),(tag,initial,paused)
   # 2. Both ending phases must retain EXACTLY the event-name geometry.
   page.evaluate("""()=>{st.phase="roundEnd";st.roundEndSince=performance.now();render();}""")
   page.wait_for_timeout(520)
   mp4end=page.evaluate(SAMPLE)
   assert mp4end["ended"],(tag,mp4end)
   stable_title(initial,mp4end,("MP4",tag))
   page.evaluate("""()=>{st.phase="ended";render();}""")
   page.wait_for_timeout(520)
   ended=page.evaluate(SAMPLE)
   assert ended["ended"] and near(ended["scaleY"],1.15,.017),(tag,ended)
   stable_title(initial,ended,("Paires",tag))
   # 3. Restore working round, then resize while SAME notice stays visible.
   page.evaluate("""()=>{
     st.phase="round";st.running=true;st.endAt=performance.now()+st.remaining*1000;
     render();
   }""")
   page.wait_for_timeout(520)
   page.set_viewport_size({"width":w+170,"height":h+265})
   page.wait_for_timeout(530)
   resized=page.evaluate(SAMPLE)
   assert resized["active"] and .90-1e-5<=resized["factor"]<=1,(tag,resized)
   fresh=page.evaluate("""()=>{
     const old=document.querySelector('#timer').style.getPropertyValue('--notice-clock-scale');
     noticeMotionKey=null;render();
     return {old,now:document.querySelector('#timer').style.getPropertyValue('--notice-clock-scale')};
   }""")
   assert near(float(fresh["old"]),float(fresh["now"]),.002),(tag,fresh)
   # 4. Ensure mini and gallery show final 1.15 magnification, with no animated frame.
   page.evaluate("tempMessageUntil=0;render()")
   page.wait_for_timeout(520)
   beforeMini=page.evaluate(SAMPLE)
   page.evaluate("showSettings(false);syncFaithfulMini(true)")
   page.wait_for_function("""()=>
    !!document.querySelector('#faithfulMiniFrame')?.contentDocument?.querySelector('#clock')""",timeout=20000)
   page.evaluate("syncFaithfulMini(true)")
   mini=page.evaluate("""()=>{
      const c=document.querySelector('#faithfulMiniFrame').contentDocument.querySelector('#clock'),
        st=getComputedStyle(c);
      return {y:Number(st.scale.split(/\\s+/).at(-1)),transition:st.transitionDuration,
       rest:st.translate};
   }""")
   assert near(mini["y"],beforeMini["scaleY"],.015),(tag,mini,beforeMini)
   assert "0s" in mini["transition"],(tag,mini)
   page.evaluate("document.body.classList.add('debugMode');_osp()")
   page.wait_for_function("""()=>{
     const a=[...document.querySelectorAll('.screenPreviewCard iframe')];
     return a.length===10&&a.every(f=>f.contentDocument?.querySelector('#clock'));
   }""",timeout=20000)
   gallery=page.evaluate("""()=>{
    const a={};
    for(const card of document.querySelectorAll('.screenPreviewCard')){
      const d=card.querySelector('iframe')?.contentDocument;
      const c=d?.querySelector('#clock');
      if(c){const st=getComputedStyle(c);a[card.querySelector('h3')?.textContent]={
        y:Number(st.scale.split(/\\s+/).at(-1)),transition:st.transitionDuration,
        rest:st.translate,phase:d.querySelector('#timer')?.className}}
    }return a;
   }""")
   for label in ("Numéro de donne en cours","Pause","Fin de la séance (Paires)"):
    a=gallery[label]
    assert near(a["y"],1.15,.015),(tag,label,a,gallery)
    assert "0s" in a["transition"],(tag,label,a)
   page.evaluate("_ssp('ended')")
   single=page.evaluate(SAMPLE)
   assert near(single["scaleY"],1.15,.015),(tag,single)
   page.evaluate("_csp()")
   assert not errors,(tag,errors)
   page.close()
 browser.close()
print("FOUR VISUAL FIXES verified: resize, paused notice, static enlarged previews, unmoving event title (both endings / formats / sizes)")
