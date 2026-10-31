"""Trial: only the visible countdown eases when a bottom announcement appears.

Test message appearance, removal, steady ticking, reduced motion, and the
unmodified 1600x900 title/buttons/footer. Gallery and mini remain static.
"""
from pathlib import Path
import os, shutil
from playwright.sync_api import sync_playwright

html=(Path(__file__).resolve().parents[1]/"timer.html").read_text(encoding="utf-8")
html=html.replace("localStorage","motionStorage").replace("</style></head><body>",
 """</style><script>const motionStorage={data:{},getItem(k){return this.data[k]??null},
 setItem(k,v){this.data[k]=v},removeItem(k){delete this.data[k]}};</script></head><body>""",1)

START="""()=>{
 Object.assign(s,{mode:'2',positions:6,eventName:'AAAA',
   boardProgressNotice:false,jumpAdvanceNotice:false,sound:false,
   hours:0,minutes:45,seconds:0});
 Object.assign(st,{started:true,phase:'round',running:false,
   remaining:2655,roundDuration:2700,pos:1,roundBoards:8,
   longClockAtStart:false});
 showTimer();render();
}"""
SAMPLE="""()=>{
 const t=document.querySelector('#timer'),c=document.querySelector('#clock'),
       m=document.querySelector('#msg'),foot=document.querySelector('.bottom'),
       title=document.querySelector('#status'),bar=document.querySelector('#timer .controls');
 const rect=e=>{const r=e.getBoundingClientRect();return {x:r.x,y:r.y,w:r.width,h:r.height}};
 const cs=getComputedStyle(c),ms=getComputedStyle(m);
 return {text:m.textContent,active:t.classList.contains('noticeMotionActive'),
   primed:t.classList.contains('noticeMotionReady'),scale:parseFloat(cs.scale),scaleY:Number(cs.scale.split(/\s+/)[1]||cs.scale),
   target:parseFloat(t.style.getPropertyValue('--notice-clock-scale')||'1'),
   font:parseFloat(cs.fontSize),msgOpacity:parseFloat(ms.opacity),
   stageScale:parseFloat(t.style.getPropertyValue('--stage-scale')),
   clock:rect(c),bottom:rect(foot),status:rect(title),buttons:rect(bar),
   transition:cs.transitionDuration,preview:t.classList.contains('spm')};
}"""

with sync_playwright() as pw:
 if os.name=="nt":
  browser=pw.chromium.launch(channel="msedge",headless=True)
 else:
  browser=pw.chromium.launch(executable_path=shutil.which("chromium") or shutil.which("chromium-browser"),
    headless=True,args=["--no-sandbox"])
 for w,h in ((812,490),(1280,720),(1600,900),(1920,1080)):
  page=browser.new_page(viewport={"width":w,"height":h})
  errors=[];page.on("pageerror",lambda e:errors.append(str(e)))
  page.set_content(html,wait_until="domcontentloaded")
  page.evaluate(START)
  page.wait_for_timeout(140)
  initial=page.evaluate(SAMPLE)
  assert initial["primed"] and not initial["active"],(w,h,initial)
  assert initial["scale"]>=0.90 and initial["scale"]<=1.151,(w,h,initial)
  assert abs(initial["scaleY"]-1.15)<.007,(w,h,initial)
  # A new announcement activates smooth, independent scale interpolation.
  page.evaluate("""()=>{
    s.quickMessage='Vous êtes censés jouer la donne 1';
    tempMessageUntil=Date.now()+60000;
    render();
  }""")
  page.wait_for_timeout(100)
  halfway=page.evaluate(SAMPLE)
  assert halfway["active"] and "donne 1" in halfway["text"],(w,h,halfway)
  assert .73<halfway["target"]<.95,(w,h,halfway)
  assert initial["scale"]*halfway["target"]<halfway["scale"]<initial["scale"],(w,h,halfway)
  assert 0<halfway["msgOpacity"]<=1,(w,h,halfway)
  page.wait_for_timeout(500)
  final=page.evaluate(SAMPLE)
  assert abs(final["scale"]-initial["scale"]*final["target"])<.025,(w,h,final)
  assert abs(final["scaleY"]-1.15*final["target"])<.025,(w,h,final)
  assert abs(final["font"]-initial["font"])<1.5,(w,h,initial,final)
  assert abs(final["bottom"]["y"]-initial["bottom"]["y"])<.3,(w,h,initial,final)
  assert abs(final["status"]["y"]-initial["status"]["y"])<.3,(w,h,initial,final)
  assert abs(final["buttons"]["x"]-initial["buttons"]["x"])<.3,(w,h,initial,final)

  # A normal ticking render must NOT restart the animation.
  page.evaluate("st.remaining-=1;render()")
  page.wait_for_timeout(80)
  tick=page.evaluate(SAMPLE)
  assert abs(tick["scale"]-final["scale"])<.012,(w,h,final,tick)

  # When notice disappears the digits expand back smoothly.
  page.evaluate("tempMessageUntil=0;render()")
  page.wait_for_timeout(100)
  retract=page.evaluate(SAMPLE)
  assert not retract["active"] and retract["text"]=="",(w,h,retract)
  assert final["scale"]<retract["scale"]<initial["scale"],(w,h,retract)
  page.wait_for_timeout(500)
  restored=page.evaluate(SAMPLE)
  assert abs(restored["scale"]-initial["scale"])<.012,(w,h,restored)
  assert abs(restored["scaleY"]-1.15)<.012,(w,h,restored)
  assert abs(restored["clock"]["h"]-initial["clock"]["h"])<1.5,(w,h,initial,restored)

  # A longer temporary message uses the same system; its text must be legible.
  page.evaluate("""()=>{
    s.quickMessage='Au prochain tour, les EO sautent une table';
    tempMessageUntil=Date.now()+60000;
    render();
  }""")
  page.wait_for_timeout(520)
  temp=page.evaluate(SAMPLE)
  assert temp["active"] and temp["text"]=="Au prochain tour, les EO sautent une table",(w,h,temp)
  assert temp["target"]<1 and abs(temp["scale"]-initial["scale"]*temp["target"])<.025,(w,h,temp)

  # No animation in Screen Tests, including single-preview and gallery.
  page.evaluate("document.body.classList.add('debugMode');showSettings(false);_osp()")
  page.wait_for_function("document.querySelectorAll('.screenPreviewCard').length===10")
  gallery=page.evaluate("""()=>{
    const card=[...document.querySelectorAll('.screenPreviewCard')].find(c=>
      c.querySelector('h3')?.textContent==='Message temporaire');
    const d=card?.querySelector('iframe')?.contentDocument;
    const e=d?.querySelector('#clock');return e&&getComputedStyle(e).scale;
  }""")
  assert gallery is not None and abs(float(gallery)-1)<.001,(w,h,gallery)
  page.evaluate("_ssp('temporary')")
  assert abs(page.evaluate("parseFloat(getComputedStyle(document.querySelector('#clock')).scale)")-1)<.001,(w,h)
  page.evaluate("_csp()")
  assert not errors,(w,h,errors)
  page.close()

 # Accessibility: reduced-motion disables all easing but still fits message.
 page=browser.new_page(viewport={"width":1600,"height":900},reduced_motion="reduce")
 page.set_content(html,wait_until="domcontentloaded")
 page.evaluate(START);page.wait_for_timeout(100)
 page.evaluate("""()=>{
    s.quickMessage='Vous êtes censés jouer la donne 1';
    tempMessageUntil=Date.now()+60000;
    render();
  }""")
 reduced=page.evaluate(SAMPLE)
 assert reduced["active"] and abs(reduced["scaleY"]-1.15*reduced["target"])<.003,reduced
 page.close()
 browser.close()
print("Notice scale/fade 420ms, ticking stable, restores clock, static previews, reduced motion: PASS")
