"""Exploratory Windows Edge audit of the 10% clock-reduction trial.

Observes cases not covered by the shipping regression tests. Does not modify
the production source. Saves screenshots and JSON diagnostics.
"""
from pathlib import Path
import json,os
from playwright.sync_api import sync_playwright

root=Path(__file__).resolve().parents[1]
html=(root/"timer.html").read_text(encoding="utf-8")
html=html.replace("localStorage","auditStorage").replace("</style></head><body>",
 """</style><script>const auditStorage={data:{},getItem(k){return this.data[k]??null},
 setItem(k,v){this.data[k]=v},removeItem(k){delete this.data[k]}};</script></head><body>""",1)

SETUP="""isLong=>{
  Object.assign(s,{mode:"2",positions:6,eventName:"Compétition",
   hours:isLong?1:0,minutes:isLong?5:45,seconds:9,
   boardProgressNotice:false,jumpAdvanceNotice:false,sound:false});
  Object.assign(st,{started:true,running:false,phase:"round",pos:1,
   remaining:isLong?3909:2709,roundDuration:isLong?3909:2709,
   longClockAtStart:isLong,roundEndSince:null});
  tempMessageUntil=0;s.quickMessage="";
  showTimer();render();
}"""
METRICS="""()=>{
 const el=id=>document.getElementById(id),t=el("timer"),c=el("clock"),m=el("msg");
 const status=el("status"),main=t.querySelector(".main"),pause=el("pauseOverlay"),finish=el("finishOverlay");
 const b=e=>{const v=e.getBoundingClientRect();return {
   x:v.x,y:v.y,left:v.left,top:v.top,right:v.right,bottom:v.bottom,
   width:v.width,height:v.height}};
 const range=document.createRange();range.selectNodeContents(m);
 const mr=range.getBoundingClientRect();
 const cr=document.createRange();cr.selectNodeContents(c);
 const ink=cr.getBoundingClientRect();
 const computed=getComputedStyle(c),g=computed.scale.split(/\s+/).map(Number);
 const act=t.classList.contains("noticeMotionActive");
 return {phase:st.phase,roundReading:t.classList.contains("roundReading"),
   noticeActive:act,notice:m.textContent,noticeFactor:Number(t.style.getPropertyValue("--notice-clock-scale")||1),
   rest:t.style.getPropertyValue("--clock-rest-y"),timerScale:Number(t.style.getPropertyValue("--stage-scale")),
   clockFont:computed.fontSize,clockScaleX:g[0],clockScaleY:g[1]||g[0],
   clockColor:computed.color,clockVisibility:computed.visibility,clock: b(c),clockInk:b(cr),
   title:b(status),main:b(main),message:b(m),messageInk:{top:mr.top,bottom:mr.bottom,height:mr.height},
   pauseVisible:pause.classList.contains("on"),endVisible:finish.classList.contains("on"),
   clockMsgOverlap:Math.max(0,ink.bottom-mr.top),
   statusClockGap:ink.top-b(status).bottom,
   timerClass:t.className
 };
}"""

out=root/"audit_outputs";out.mkdir(exist_ok=True)
results={}
with sync_playwright() as pw:
 browser=pw.chromium.launch(channel="msedge",headless=True)
 for isLong in (False,True):
  for width,height in ((812,490),(1600,900),(1000,750)):
   tag=("long" if isLong else "short")+f"_{width}x{height}"
   page=browser.new_page(viewport={"width":width,"height":height})
   errors=[];page.on("pageerror",lambda e:errors.append(str(e)))
   page.set_content(html,wait_until="domcontentloaded")
   page.evaluate(SETUP,isLong);page.wait_for_timeout(520)
   noMessage=page.evaluate(METRICS)
   page.evaluate("""()=>{
     s.quickMessage="Attention, au prochain tour les EO sautent une table";
     tempMessageUntil=Date.now()+60000;render();
   }""");page.wait_for_timeout(520)
   message=page.evaluate(METRICS)
   if (width,height)==(1600,900) and not isLong:
    page.screenshot(path=str(out/"normal_with_message.png"))
   page.evaluate("pause()");page.wait_for_timeout(520)
   pausedMessage=page.evaluate(METRICS)
   if (width,height)==(1600,900) and not isLong:
    page.screenshot(path=str(out/"paused_with_message.png"))
   page.evaluate("tempMessageUntil=0;render()");page.wait_for_timeout(520)
   pausedNoMessage=page.evaluate(METRICS)
   if (width,height)==(1600,900) and not isLong:
    page.screenshot(path=str(out/"paused_without_message.png"))
   page.evaluate("""()=>{
     st.phase="ended";st.running=false;st.roundEndSince=performance.now()-5000;
     render();
   }""");page.wait_for_timeout(520)
   ended=page.evaluate(METRICS)
   if (width,height)==(1600,900) and not isLong:
    page.screenshot(path=str(out/"ended.png"))
   # Same notice/format but a different aspect ratio, recalculating layout.
   page.evaluate("""()=>{
     st.phase="round";st.running=false;s.eventName="Compétition";
     s.quickMessage="Attention, au prochain tour les EO sautent une table";
     tempMessageUntil=Date.now()+60000;render();
   }""");page.wait_for_timeout(520)
   beforeResize=page.evaluate(METRICS)
   page.set_viewport_size({"width":width+170,"height":height+265})
   page.evaluate("render()");page.wait_for_timeout(520)
   resizeCached=page.evaluate(METRICS)
   page.evaluate("noticeMotionKey=null;render()");page.wait_for_timeout(520)
   resizeRecomputed=page.evaluate(METRICS)
   # Same notice but title text and font metrics change.
   page.evaluate("""()=>{
     s.eventName="Championnat international de bridge en équipes, grande finale";
     render();
   }""");page.wait_for_timeout(520)
   titleCached=page.evaluate(METRICS)
   page.evaluate("noticeMotionKey=null;render()");page.wait_for_timeout(520)
   titleRecomputed=page.evaluate(METRICS)
   results[tag]={
    "normal":noMessage,"notice":message,"pausedWithNotice":pausedMessage,
    "pausedWithoutNotice":pausedNoMessage,"finished":ended,
    "beforeResize":beforeResize,"resizeCached":resizeCached,
    "resizeRecomputed":resizeRecomputed,"titleCached":titleCached,
    "titleRecomputed":titleRecomputed,"errors":errors}
   summary={
    "view":tag,"max10":message["noticeFactor"]>=.9-1e-5,
    "pauseWithMessage_restFactor":pausedMessage["noticeFactor"],
    "pauseWithMessage_y":pausedMessage["rest"],
    "pauseNoMessage_restFactor":pausedNoMessage["noticeFactor"],
    "finish_restFactor":ended["noticeFactor"],
    "finish_y":ended["rest"],
    "resize_factor_cached":resizeCached["noticeFactor"],
    "resize_factor_recomputed":resizeRecomputed["noticeFactor"],
    "title_factor_cached":titleCached["noticeFactor"],
    "title_factor_recomputed":titleRecomputed["noticeFactor"],
    "notice_ink_overlap":round(message["clockMsgOverlap"],2),
    "pause_ink_overlap":round(pausedMessage["clockMsgOverlap"],2),
    "errors":errors}
   print("AUDIT_CASE "+json.dumps(summary,ensure_ascii=False),flush=True)
   assert message["noticeFactor"]>=.9-1e-5,summary
   assert not errors,summary
   page.close()
 browser.close()
(out/"audit_metrics.json").write_text(json.dumps(results,indent=2,ensure_ascii=False),encoding="utf-8")
print("AUDIT_COMPLETE "+str(out/"audit_metrics.json"),flush=True)
