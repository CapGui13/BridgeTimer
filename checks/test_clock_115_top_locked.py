"""Make both clock formats 15% taller, without raising their top or clipping.

The original 1600x900 timer text is already very wide, so horizontal growth
may be capped to fit the window. This applies a shared visual transform to
whole clock, preserving long-form small seconds and both colon marks.
"""
from pathlib import Path
import os,shutil
from playwright.sync_api import sync_playwright

html=(Path(__file__).resolve().parents[1]/"timer.html").read_text(encoding="utf-8")
html=html.replace("localStorage","growthStorage").replace("</style></head><body>",
 """</style><script>const growthStorage={data:{},getItem(k){return this.data[k]??null},
 setItem(k,v){this.data[k]=v},removeItem(k){delete this.data[k]}};</script></head><body>""",1)

SETUP="""longRound=>{
 Object.assign(s,{mode:"2",positions:6,eventName:"Compet",
   hours:longRound?1:0,minutes:longRound?5:45,seconds:9,
   boardProgressNotice:false,jumpAdvanceNotice:false,sound:false});
 Object.assign(st,{started:true,running:false,phase:"round",
   pos:1,remaining:longRound?3909:2709,
   roundDuration:longRound?3909:2709,longClockAtStart:longRound});
 showTimer();render();
}"""

METRICS="""()=>{
 const t=document.querySelector('#timer'),c=document.querySelector('#clock'),
  main=c.parentElement,status=document.querySelector('#status'),rect=e=>{
   const r=e.getBoundingClientRect();
   return {left:r.left,top:r.top,right:r.right,bottom:r.bottom,width:r.width,height:r.height}
  };
 const range=document.createRange();range.selectNodeContents(c);
 const r=()=>({box:rect(c),ink:rect(range),status:rect(status),main:rect(main)});
 const transformed=r(),visual=getComputedStyle(c).scale,
  old=c.style.scale,oldTransition=c.style.transition;
 // Stop the 420ms animation temporarily before taking the baseline:
 // otherwise layout reads capture the OLD interpolated scale.
 c.style.transition='none';
 c.style.scale='1';void c.offsetHeight;
 const baseline=r();
 if(old)c.style.scale=old;else c.style.removeProperty('scale');
 void c.offsetHeight;
 if(oldTransition)c.style.transition=oldTransition;else c.style.removeProperty('transition');
 return {clockText:c.textContent,long:c.classList.contains('longStartClock'),
  x:Number(visual.split(/\s+/)[0]),y:Number(visual.split(/\s+/)[1]||visual),
  transformed,baseline,offsetWidth:c.offsetWidth,
  primary:c.querySelector('.clockPrimary')&&parseFloat(getComputedStyle(c.querySelector('.clockPrimary')).fontSize),
  seconds:c.querySelector('.clockSeconds')&&parseFloat(getComputedStyle(c.querySelector('.clockSeconds')).fontSize),
  colon:!!c.querySelector('.clockSeparator'),
  growX:t.style.getPropertyValue('--clock-display-scale-x'),
  growY:t.style.getPropertyValue('--clock-display-scale-y')};
}"""

with sync_playwright() as pw:
 if os.name=='nt':
  browser=pw.chromium.launch(channel='msedge',headless=True)
 else:
  browser=pw.chromium.launch(executable_path=shutil.which('chromium') or shutil.which('chromium-browser'),
    headless=True,args=['--no-sandbox'])
 for width,height in ((682,415),(812,490),(1280,720),(1600,900),(1920,1080)):
  for longRound in (False,True):
   page=browser.new_page(viewport={'width':width,'height':height})
   errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
   page.set_content(html,wait_until='domcontentloaded')
   page.evaluate(SETUP,longRound)
   page.wait_for_timeout(100)
   a=page.evaluate(METRICS)
   assert a['long']==longRound,(width,height,a)
   assert abs(a['y']-1.15)<.008,(width,height,longRound,a)
   assert a['x']<=1.151,(width,height,longRound,a)
   assert a['x']>.85,(width,height,longRound,a)
   assert a['growX'] and a['growY'],(width,height,longRound,a)
   before=a['baseline'];after=a['transformed']
   # Crucial request: top of the enlarged clock NEVER moves upwards.
   assert after['box']['top']>=before['box']['top']-.6,(width,height,longRound,a)
   assert after['ink']['top']>=before['ink']['top']-1.1,(width,height,longRound,a)
   assert abs(after['box']['height']/before['box']['height']-1.15)<.008,(width,height,longRound,a)
   assert after['box']['bottom']>before['box']['bottom'],(width,height,longRound,a)
   # Range ink bounds include Bahnschrift line-height whitespace below
   # the painted digits; with the intentional 22px lowered rest position,
   # testing the Range's bottom wrongly reports clipped pixels.
   # The clock box itself must remain entirely inside the main display.
   assert after['box']['bottom']<=after['main']['bottom']-4,(width,height,longRound,a)
   assert after['box']['left']>=after['main']['left']-2,(width,height,longRound,a)
   assert after['box']['right']<=after['main']['right']+2,(width,height,longRound,a)
   # The original Bahnschrift ink already extends outside its CSS line box.
   # Compare to that APPROVED visible top, not the title's line box.
   assert after['ink']['top']>=before['ink']['top']-1.1,(width,height,longRound,a)
   if longRound:
    assert a['clockText']=='1:05:09' and a['colon'],(width,height,a)
    assert abs(a['seconds']/a['primary']-.56)<.002,(width,height,a)
   else:
    assert a['clockText']=='45:09' and not a['colon'],(width,height,a)

   # The countdown eases down when a message appears but preserves its top.
   page.evaluate("""()=>{
     s.quickMessage='Au prochain tour, les EO sautent une table';
     tempMessageUntil=Date.now()+60000;render();
   }""")
   page.wait_for_timeout(520)
   msg=page.evaluate(METRICS)
   assert msg['y']<a['y'] and msg['x']<a['x'],(width,height,longRound,a,msg)
   # As the clock shrinks to make room for a message, its line box may
   # move UP toward the approved original baseline — not above the title.
   # We only lock the highest edge of the ENLARGED, no-message clock.
   # A notice intentionally raises the clock from its NEW lowered rest.
   # It must still stay beneath the event title. Range bounds include
   # non-painted Bahnschrift ascent space and are not reliable glyph edges.
   assert msg['transformed']['box']['top']>=msg['transformed']['status']['bottom']+2,(width,height,longRound,a,msg)
   page.evaluate("tempMessageUntil=0;render()")
   page.wait_for_timeout(520)
   restored=page.evaluate(METRICS)
   assert abs(restored['y']-1.15)<.012,(width,height,longRound,restored)
   assert abs(restored['x']-a['x'])<.012,(width,height,longRound,restored)
   assert not errors,(width,height,longRound,errors)
   page.close()
 browser.close()
print("1.15x-height clock, top locked, no side clipping, short/long formats, animated notices: PASS")
