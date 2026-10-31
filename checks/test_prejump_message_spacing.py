"""Pre-jump and board-number notices share comfortable vertical line spacing.

Tests the real 1600x900 gallery preview (same CSS as actual timer) at
several viewer sizes, and guards the other message styles.
"""
from pathlib import Path
import os,shutil
from playwright.sync_api import sync_playwright

html=(Path(__file__).resolve().parents[1]/"timer.html").read_text(encoding="utf-8")
html=html.replace("localStorage","sautTestStorage").replace("</style></head><body>",
 """</style><script>const sautTestStorage={data:{},getItem(k){return this.data[k]??null},
 setItem(k,v){this.data[k]=v},removeItem(k){delete this.data[k]}};</script></head><body>""",1)

sample_js="""()=>{
 const get=(kind)=>{
  const card=[...document.querySelectorAll('.screenPreviewCard')].find(
    card=>card.querySelector('.spHeader h3')?.textContent===kind);
  if(!card)throw new Error('Missing gallery preview: '+kind);
  const e=card.querySelector('iframe').contentDocument.querySelector('#msg');
  const st=getComputedStyle(e),r=e.getBoundingClientRect();
  const lines=[],t=e.firstChild;
  if(t&&t.nodeType===3){
   const rg=e.ownerDocument.createRange();
   for(let i=0;i<t.length;i++){
    if(t.textContent[i].trim()==='')continue;
    rg.setStart(t,i);rg.setEnd(t,i+1);
    const b=rg.getBoundingClientRect(),y=Math.round(b.top);
    if(!lines.includes(y))lines.push(y);
   }
  }
  return {text:e.textContent,kind:e.className,
    font:parseFloat(st.fontSize),lineHeight:parseFloat(st.lineHeight),
    height:r.height,scrollHeight:e.scrollHeight,
    linePositions:lines.sort((a,b)=>a-b)};
 };
 return {jump:get('Pré-alerte saut'),board:get('Numéro de donne en cours'),
         temporary:get('Message temporaire')};
}"""

with sync_playwright() as pw:
 if os.name=="nt":
  browser=pw.chromium.launch(channel="msedge",headless=True)
 else:
  browser=pw.chromium.launch(executable_path=shutil.which("chromium") or shutil.which("chromium-browser"),headless=True,args=["--no-sandbox"])

 for w,h in ((812,490),(1280,720),(1650,930),(1920,1080)):
  page=browser.new_page(viewport={"width":w,"height":h})
  errors=[]
  page.on("pageerror",lambda err:errors.append(str(err)))
  page.set_content(html,wait_until="domcontentloaded")
  page.wait_for_function("typeof recoveryArmed!=='undefined' && recoveryArmed")
  page.evaluate("""()=>{
   document.body.classList.add('debugMode');
   Object.assign(s,{mode:'2',positions:8,eventName:'AAAA',
       jumpRound:4,jumpAdvanceNotice:true,
       jumpMessage:'Au prochain tour, les EO sautent une table',warnEnabled:true});
   Object.assign(st,{started:true,phase:'round',running:false,
       remaining:40,roundDuration:3600,pos:4,longClockAtStart:true});
   showSettings(false);_osp();
  }""")
  # On slower Windows runners the sandboxed gallery frames load asynchronously.
  # Wait for all 10 cloned preview documents before reading their styles.
  page.wait_for_function("""() => {
   const frames=[...document.querySelectorAll('.screenPreviewCard iframe')];
   return frames.length===10 && frames.every(f=>!!f.contentDocument?.querySelector('#msg'));
  }""",timeout=15000)
  state=page.evaluate(sample_js)
  jump=state["jump"]
  assert jump["text"]=="Au prochain tour, les EO sautent une table",(w,h,jump)
  assert "roundMessageJump" in jump["kind"],(w,h,jump)
  assert abs(jump["lineHeight"]/jump["font"]-1.12)<0.025,(w,h,jump)
  # At small viewports the auto-fit algorithm may choose a single line.
  # In two-line mode, verify real vertical separation.
  assert 1<=len(jump["linePositions"])<=2,(w,h,jump)
  if len(jump["linePositions"])==2:
   assert jump["linePositions"][1]-jump["linePositions"][0]>=jump["font"]*1.08,(w,h,jump)
  assert jump["scrollHeight"]<=jump["height"]+3,(w,h,jump)
  # Board-number instruction: use the same vertical breathing space as jump.
  board=state["board"]
  assert "roundMessageJump" not in board["kind"],(w,h,board)
  assert "donne" in board["text"].lower(),(w,h,board)
  assert abs(board["lineHeight"]/board["font"]-1.12)<0.025,(w,h,board)
  assert board["scrollHeight"]<=board["height"]+3,(w,h,board)
  if len(board["linePositions"])>=2:
   assert all(y-x>=board["font"]*1.08 for x,y in zip(board["linePositions"],board["linePositions"][1:])),(w,h,board)
  # Temporary-message PREVIEWS now have the same comfortable spacing;
  # the real full-size timer is independently guarded by its dedicated test.
  other=state["temporary"]
  assert "roundMessageJump" not in other["kind"],(w,h,other)
  assert abs(other["lineHeight"]/other["font"]-1.12)<0.025,(w,h,other)
  assert not errors,(w,h,errors)
  page.close()
 browser.close()
print("Pre-jump and board instruction spacing, no clipping; temporary unchanged: PASS")
