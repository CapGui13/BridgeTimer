"""Regression: long countdown uses real colon glyph, not hand-drawn dots.

Guard the baseline's strict homothety and 56%-height seconds.
"""
from pathlib import Path
import os,shutil
from playwright.sync_api import sync_playwright

html=Path("timer.html").read_text(encoding="utf-8")
assert ".clockSeparator::before" not in html
assert ".clockSeparator::after" not in html
html=html.replace("localStorage","clockAuditStorage").replace("</style></head><body>",
 """</style><script>const clockAuditStorage={data:{},getItem(k){return this.data[k]??null},
 setItem(k,v){this.data[k]=v},removeItem(k){delete this.data[k]}};</script></head><body>""",1)

def setup(page,remaining=3909,start=3909):
 page.evaluate("""([remaining,start])=>{
   Object.assign(s,{mode:'2',positions:6,hours:1,minutes:5,seconds:9,
     eventName:'Festival - Final',boardProgressNotice:true});
   Object.assign(st,{started:true,phase:'round',running:true,pos:1,
     remaining,roundDuration:start,longClockAtStart:start>=3600});
   showTimer();render();
 }""",[remaining,start])

def sample(page):
 return page.evaluate("""()=>{
  const c=document.querySelector('#clock'),
        p=c.querySelector('.clockPrimary'),
        colon=c.querySelector('.clockSeparator'),
        sec=c.querySelector('.clockSeconds');
  const rect=e=>{let r=e.getBoundingClientRect();return {x:r.x,y:r.y,w:r.width,h:r.height,right:r.right}};
  return {text:c.textContent,hasColon:!!colon,
    style:c.className,gap:getComputedStyle(c).gap,
    root:rect(c),primary:p&&rect(p),colon:colon&&rect(colon),sec:sec&&rect(sec),
    rootFont:parseFloat(getComputedStyle(c).fontSize),
    primaryFont:p&&parseFloat(getComputedStyle(p).fontSize),
    secFont:sec&&parseFloat(getComputedStyle(sec).fontSize),
    colonFont:colon&&parseFloat(getComputedStyle(colon).fontSize),
    pseudo:colon&&getComputedStyle(colon,"::before").content
  };
 }""")

with sync_playwright() as pw:
 if os.name=="nt":browser=pw.chromium.launch(channel="msedge",headless=True)
 else:browser=pw.chromium.launch(executable_path=shutil.which("chromium") or shutil.which("chromium-browser"),headless=True,args=["--no-sandbox"])
 for w,h in ((812,490),(960,540),(1600,900),(1920,1080)):
  page=browser.new_page(viewport={"width":w,"height":h})
  errs=[];page.on("pageerror",lambda e:errs.append(str(e)))
  page.set_content(html,wait_until="domcontentloaded")
  setup(page)
  a=sample(page)
  assert a["text"]=="1:05:09",a
  assert a["hasColon"] and a["gap"]=="0px",a
  assert a["pseudo"]=="none",a
  assert abs(a["secFont"]/a["primaryFont"]-.56)<.002,a
  assert abs(a["colonFont"]/a["primaryFont"]-.4)<.002,a
  assert a["primary"]["right"]<=a["colon"]["x"]+.5,a
  assert a["colon"]["right"]<=a["sec"]["x"]+.5,a
  assert abs(a["colon"]["w"]-70*min(w/1600,h/900))<2,a
  assert a["root"]["x"]>=-2 and a["root"]["right"]<=w+2,a
  # Only the glyph is new: title and message remain part of the reference.
  assert page.locator("#status").count()==1
  assert page.locator("#msg").count()==1

  # Once a long round begins, retain H:MM:SS after 59:59.
  setup(page,3599,3909)
  assert sample(page)["text"]=="0:59:59"
  # A round initially under 1 hour keeps unchanged MM:SS layout.
  setup(page,2700,2700)
  b=page.evaluate("""()=>({text:document.getElementById('clock').textContent,
             long:document.getElementById('clock').classList.contains('longStartClock'),
             separators:document.querySelectorAll('.clockSeparator').length})""")
  assert b=={"text":"45:00","long":False,"separators":0},b

  setup(page)
  win=sample(page)
  page.evaluate("q25(true);render()")
  full=sample(page)
  assert full["text"]=="1:05:09"
  for k in ("primaryFont","secFont","colonFont"):
   assert abs(win[k]-full[k])<1.3,(w,h,k,win[k],full[k])
  for key in ("primary","colon","sec"):
   for coord in ("w","h"):
    assert abs(win[key][coord]-full[key][coord])<1.3,(w,h,key,coord)
  assert not errs,errs
  page.close()
 browser.close()
print("Real typographic colon, 56% seconds, no faux dots, strict window/full parity: PASS")
