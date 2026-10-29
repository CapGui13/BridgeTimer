"""Rendered band/button size and layout parity between windowed Settings and Timer.

The timer uses a uniformly scaled virtual scene; tests MUST measure actual
pixel rectangles and apparent font sizes (not raw virtual CSS font size).
Fullscreen and screen-preview scenes intentionally retain legacy dimensions.
"""
from pathlib import Path
import os
import shutil
from playwright.sync_api import sync_playwright

html=(Path(__file__).resolve().parents[1]/"timer.html").read_text(encoding="utf-8")
html=html.replace("localStorage","bridgeAuditStorage")
html=html.replace("</style></head><body>", """</style><script>
const bridgeAuditStorage={data:{},getItem(k){return this.data[k]??null},
setItem(k,v){this.data[k]=v},removeItem(k){delete this.data[k]}};
</script></head><body>""",1)

def close(actual,expected,label,tolerance=1.25):
 assert abs(actual-expected)<=tolerance, f"{label}: got {actual:.2f}px, expected {expected}px"

def layout(page):
 return page.evaluate("""() => {
  const t=document.querySelector('#timer');
  const scale=parseFloat(t.style.getPropertyValue('--stage-scale'))||1;
  const rect=q=>{const e=document.querySelector(q);
    const r=e.getBoundingClientRect();
    return {l:r.left,r:r.right,t:r.top,b:r.bottom,w:r.width,h:r.height,
      apparentFont:parseFloat(getComputedStyle(e).fontSize)*scale,
      text:e.textContent.trim().slice(0,80)};
  };
  return {top:rect('#timer .top'),bottom:rect('#timer .bottom'),
    brand:rect('#timer .identity'),
    topButtons:rect('#timer .topBtns'),
    resume:rect('#resumeBtn'),message:rect('#messageBtn'),
    settings:rect('#settingsBtn'),fullscreen:rect('#fsBtn'),
    controls:rect('#timer .controls'),
    buttons:['minus','pause','plus','next','resetRound'].map(id=>rect('#'+id)),
    time:rect('#localTime'),round:rect('#round'),main:rect('#timer .main'),
    clock:rect('#clock'),
    scale,viewport:{w:innerWidth,h:innerHeight}};
 }""")

with sync_playwright() as pw:
 if os.name=="nt": browser=pw.chromium.launch(channel="msedge",headless=True)
 else: browser=pw.chromium.launch(executable_path=shutil.which("chromium") or shutil.which("chromium-browser"),
                                headless=True,args=["--no-sandbox"])
 for width,height in [(812,480),(812,520),(960,560),(1280,720)]:
  page=browser.new_page(viewport={"width":width,"height":height})
  errors=[]
  page.on("pageerror",lambda err:errors.append(str(err)))
  page.set_content(html,wait_until="domcontentloaded")
  for mode in ("2","4"):
   page.evaluate("""mode=>{
     s.mode=mode; s.positions=6;st.started=true;st.running=false;
     st.pos=1;st.phase='round';st.remaining=3540;st.roundDuration=3600;
     showTimer();render();
   }""",mode)
   for phase in ("round","break","jump","roundEnd","ended"):
    page.evaluate("p=>{st.phase=p;st.running=false;render()}",phase)
    m=layout(page)
    close(m["top"]["h"],55,f"{width}x{height} {mode} {phase} top")
    close(m["bottom"]["h"],59,f"{width}x{height} {mode} {phase} bottom")
    for name in ("resume","message","settings","fullscreen"):
     close(m[name]["h"],34,f"{width} {mode} {phase} {name} height")
     close(m[name]["apparentFont"],12,f"{width} {mode} {phase} {name} apparent font",1.5)
    for idx,button in enumerate(m["buttons"]):
     close(button["h"],40,f"{width} {mode} {phase} button {idx} height")
     close(button["apparentFont"],13,f"{width} {mode} {phase} button {idx} font",1.5)
    close(m["top"]["t"],0,f"{width} top attachment")
    close(m["bottom"]["b"],height,f"{width} footer attachment")
    assert m["time"]["r"]+5<=m["controls"]["l"],f"Time/footer buttons overlap: {m}"
    assert m["controls"]["r"]+5<=m["round"]["l"],f"Footer buttons/round label overlap: {m}"
    assert m["brand"]["r"]+5<=m["topButtons"]["l"],f"Club/buttons overlap: {m}"
    assert m["main"]["h"]>220,f"Central timer stage collapsed: {m}"
    assert m["clock"]["b"]<=m["bottom"]["t"],f"Clock under bottom bar: {m}"
    assert not errors, f"{width}x{height}: JS errors: {errors}"
   # Restore round before taking fullscreen measurements.
   page.evaluate("()=>{st.phase='round';render()}")
   page.evaluate("()=>{document.body.classList.add('fs');updateStage();render()}")
   fs=layout(page)
   close(fs["top"]["h"],82*fs["scale"],f"{width} fullscreen top unchanged",2)
   close(fs["bottom"]["h"],88*fs["scale"],f"{width} fullscreen bottom unchanged",2)
   page.evaluate("()=>{document.body.classList.remove('fs');updateStage();render()}")
   restored=layout(page)
   close(restored["top"]["h"],55,f"{width} fullscreen return top")
   close(restored["bottom"]["h"],59,f"{width} fullscreen return footer")
  page.close()
 browser.close()
print("Windowed Timer/Settings band parity: all viewports, modes, phases and fullscreen returns OK")
