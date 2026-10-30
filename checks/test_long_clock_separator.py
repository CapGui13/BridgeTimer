"""Long start rounds show H:MM:SS without resizing any existing digits."""
from pathlib import Path
import os,shutil
from playwright.sync_api import sync_playwright

html=Path("timer.html").read_text(encoding="utf-8")
html=html.replace("localStorage","clockAuditStorage").replace("</style></head><body>",
 """</style><script>const clockAuditStorage={data:{},getItem(k){return this.data[k]??null},
 setItem(k,v){this.data[k]=v},removeItem(k){delete this.data[k]}};</script></head><body>""",1)

def dimensions(page):
 return page.evaluate("""() => {
  const r=selector=>{
   const e=document.querySelector(selector),b=e.getBoundingClientRect();
   return [b.x,b.y,b.width,b.height,getComputedStyle(e).fontSize];
  };
  return Object.fromEntries(
   ['#clock','.clockPrimary','.clockSeconds','#timer .top','#timer .bottom']
   .map(selector=>[selector,r(selector)]));
 }""")

def long_case(page, seconds):
 page.evaluate("""seconds=>{
  Object.assign(s,{mode:'2',positions:6,hours:1,minutes:10,seconds:0,
    eventName:'Event',sound:false});
  Object.assign(st,{started:true,running:true,phase:'round',
    roundDuration:4200,remaining:seconds,pos:1,longClockAtStart:true});
  showTimer();render();
 }""",seconds)
 return page.evaluate("""() => {
  const c=document.getElementById("clock"),sep=c.querySelector(".clockSeparator");
  return {text:c.textContent,primary:c.querySelector(".clockPrimary").textContent,
    small:c.querySelector(".clockSeconds").textContent,
    smallSize:parseFloat(getComputedStyle(c.querySelector(".clockSeconds")).fontSize),
    largeSize:parseFloat(getComputedStyle(c.querySelector(".clockPrimary")).fontSize),
    separator:!!sep,
    dot1:sep&&getComputedStyle(sep,"::before").content,
    dot2:sep&&getComputedStyle(sep,"::after").content,
    gap:getComputedStyle(c).gap};
 }""")

with sync_playwright() as pw:
 if os.name=="nt":
  browser=pw.chromium.launch(channel="msedge",headless=True)
 else:
  browser=pw.chromium.launch(executable_path=shutil.which("chromium") or shutil.which("chromium-browser"),headless=True,args=["--no-sandbox"])
 for w,h in [(812,490),(960,540),(1600,900),(1920,1080)]:
  page=browser.new_page(viewport={"width":w,"height":h})
  errors=[]
  page.on("pageerror",lambda err:errors.append(str(err)))
  page.set_content(html,wait_until="domcontentloaded")
  x=long_case(page,3909)
  assert x["text"]=="1:05:09", (w,h,x)
  assert x["primary"]=="1:05" and x["small"]==":09",x
  assert x["separator"] and x["dot1"]!='none' and x["dot2"]!='none',x
  assert x["gap"]=="22px",x
  assert abs(x["smallSize"]/x["largeSize"]-.56)<.002,x

  full_before=dimensions(page)
  # The positioned separator must have NO layout footprint.
  page.evaluate("document.querySelector('.clockSeparator').remove()")
  full_without=dimensions(page)
  for key in full_before:
   for a,b in zip(full_before[key][:4],full_without[key][:4]):
    assert abs(a-b)<.1,(w,h,key,a,b)

  # The start-of-round rule must stay locked after dropping under one hour.
  x=long_case(page,3599)
  assert x["text"]=="0:59:59" and x["small"]==":59",x

  # But a round whose configured duration starts under 1 hour stays MM:SS.
  page.evaluate("""()=>{
    Object.assign(s,{hours:0,minutes:45,seconds:0});
    Object.assign(st,{roundDuration:2700,remaining:2700,longClockAtStart:false});
    render();
  }""")
  assert page.evaluate("document.getElementById('clock').textContent")=="45:00"
  assert page.locator(".clockSeparator").count()==0

  # Restore long format; compare windowed/fullscreen at the same viewport.
  x=long_case(page,3600)
  windowed=dimensions(page)
  page.evaluate("q25(true);render()")
  fullscreen=dimensions(page)
  for key in windowed:
   for a,b in zip(windowed[key][2:5],fullscreen[key][2:5]):
    if isinstance(a,str): assert a==b,(w,h,key,a,b)
    else: assert abs(a-b)<1.5,(w,h,key,a,b)
  assert not errors,(w,h,errors)
  page.close()
 browser.close()
print("Long clock H:MM:SS + identical geometry + 56% seconds + short timer unchanged: PASS")
