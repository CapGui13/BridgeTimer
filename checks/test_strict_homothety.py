"""One 1600x900 scale for timer in all window/fullscreen viewports."""
from pathlib import Path
import os, shutil
from playwright.sync_api import sync_playwright

html=(Path(__file__).resolve().parents[1]/"timer.html").read_text(encoding="utf8")
assert "--windowed-footer-stage-height" not in html
html=html.replace("localStorage","testLocalStorage").replace("</style></head><body>",
 """</style><script>const testLocalStorage={data:{},getItem(k){return this.data[k]??null},
 setItem(k,v){this.data[k]=v},removeItem(k){delete this.data[k]}}</script></head><body>""",1)
sels=["#timer .top","#club","#timer .topBtns","#timer .topBtns .btn",
      "#timer .bottom","#timer .controls","#minus","#pause","#plus",
      "#next","#resetRound","#localTime","#round","#clock","#msg"]
measure="""sels=>{const elements={};for(const sel of sels){
 const e=document.querySelector(sel),r=e.getBoundingClientRect(),cs=getComputedStyle(e);
 elements[sel]={x:r.x,y:r.y,w:r.width,h:r.height,font:parseFloat(cs.fontSize),
 opacity:parseFloat(cs.opacity)}}
 return {scale:Number(document.querySelector("#timer").style.getPropertyValue("--stage-scale")),
 elements}}"""
setup="""()=>{Object.assign(s,{mode:"2",positions:6,eventName:"Event",boardProgressNotice:true});
 Object.assign(st,{started:true,running:true,phase:"round",remaining:3598,pos:1,
 roundDuration:3600,roundBoards:8,longClockAtStart:true});showTimer();render()}"""
with sync_playwright() as pw:
 if os.name=="nt":browser=pw.chromium.launch(channel="msedge",headless=True)
 else:browser=pw.chromium.launch(executable_path=shutil.which("chromium") or shutil.which("chromium-browser"),headless=True,args=["--no-sandbox"])
 for w,h in [(682,415),(800,450),(812,490),(960,540),(1280,720),(1600,900),(1920,1080)]:
  page=browser.new_page(viewport={"width":w,"height":h})
  errors=[];page.on("pageerror",lambda e:errors.append(str(e)))
  page.set_content(html,wait_until="domcontentloaded");page.evaluate(setup);page.wait_for_timeout(120)
  win=page.evaluate(measure,sels)
  assert abs(win["scale"]-min(w/1600,h/900))<1e-7,(w,h,win["scale"])
  page.evaluate("q25(true);render()");page.wait_for_timeout(90)
  full=page.evaluate(measure,sels)
  for sel in sels:
   for dimension in ("w","h","font"):
    assert abs(win["elements"][sel][dimension]-full["elements"][sel][dimension])<1.4,(w,h,sel,dimension)
  before=full["elements"]["#timer .controls"]
  page.evaluate("st.pos=10;render()");page.wait_for_timeout(100)
  after=page.evaluate(measure,sels)["elements"]["#timer .controls"]
  for dimension in ("x","y","w","h"):
   assert abs(before[dimension]-after[dimension])<.3,(w,h,dimension,before,after)
  page.evaluate("q36()");page.wait_for_timeout(270)
  shown=page.evaluate(measure,sels)
  page.evaluate('document.body.classList.remove("showControls")')
  page.wait_for_timeout(95);midway=page.evaluate(measure,sels)
  assert .02<midway["elements"]["#timer .controls"]["opacity"]<.98
  page.wait_for_timeout(180);hidden=page.evaluate(measure,sels)
  assert hidden["elements"]["#timer .controls"]["opacity"]==0
  for sel in ("#timer .controls","#timer .topBtns","#clock"):
   for dimension in ("x","y","w","h"):
    assert abs(shown["elements"][sel][dimension]-midway["elements"][sel][dimension])<.3
    assert abs(shown["elements"][sel][dimension]-hidden["elements"][sel][dimension])<.3
  assert not errors,errors
  page.close()
 browser.close()
print("Strict homothety + controls fade + stable footer: seven viewport checks PASS")
