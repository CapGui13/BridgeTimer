"""Pixel-for-pixel regression check against the approved pre-maintenance timer.

CI checks out the APPROVED commit into baseline_for_compare. Edge renders each
identical scenario at the same viewport with animations disabled. Only the
real-time clock label and live mini content are masked (the mini's footprint
and its position remain compared). The CSS cascade should be visually inert.
"""
import hashlib,os,shutil,sys
from pathlib import Path
from playwright.sync_api import sync_playwright

APP=Path("timer.html").read_text(encoding="utf8")
REF=Path("baseline_for_compare/timer.html").read_text(encoding="utf8")
def prepare(html):
 return html.replace("localStorage","maintenanceTestStorage").replace(
  "</style></head><body>",
  """</style><script>const maintenanceTestStorage={data:{},
   getItem(k){return this.data[k]??null},setItem(k,v){this.data[k]=v},
   removeItem(k){delete this.data[k]}};</script></head><body>""",1)

SCENARIOS=[
 ("settings-windowed-MP4",812,520,"4","settings",False,False,False),
 ("settings-windowed-pairs",960,680,"2","settings",False,False,False),
 ("settings-fullscreen-MP4",1650,928,"4","settings",True,True,False),
 ("settings-fullscreen-pairs",1920,1080,"2","settings",True,True,False),
 ("timer-windowed-short",1280,720,"4","timer",False,True,False),
 ("timer-windowed-long",960,680,"2","timer",False,True,True),
 ("timer-fullscreen-short",1650,928,"2","timer",True,True,False),
 ("timer-fullscreen-long",1920,1080,"4","timer",True,True,True),
]
def screenshot(browser,html,item):
 name,width,height,mode,view,fs,live,longclock=item
 page=browser.new_page(viewport={"width":width,"height":height},device_scale_factor=1)
 errors=[]
 page.on("pageerror",lambda e:errors.append(str(e)))
 page.set_content(prepare(html),wait_until="domcontentloaded")
 page.wait_for_function("typeof recoveryArmed!=='undefined' && recoveryArmed")
 page.evaluate("""v=>{
  const [mode,view,fs,live,longclock]=v;
  Object.assign(s,{mode,positions:6,startPosition:1,boards:8,between:15,
   hours:longclock?1:0,minutes:longclock?20:25,seconds:0,
   clubName:"Tournoi test",eventName:"Épreuve de comparaison",
   sound:false,boardProgressNotice:false});
  fill();
  if(live){st.started=true;q4a(2,false);st.remaining=535;st.running=false;}
  if(view==="timer"){showTimer();}else if(live){showTimer();showSettings(false);}
  q25(fs);render();
 }""",[mode,view,fs,live,longclock])
 page.wait_for_timeout(70)
 from playwright.sync_api import TimeoutError as PTTimeout
 if view=="settings" and live:
  try:page.wait_for_function("document.getElementById('faithfulMiniFrame')?.contentDocument?.body?.children.length>0",timeout=2000)
  except PTTimeout:pass
 masks=[page.locator("#localTime"),page.locator("#miniTimer")]
 # The ONLY approved visual difference is the new sound test control.
 # Return its bounding box to mask the union of the old/new local areas.
 sound=page.locator(".soundOption")
 sound_box=sound.bounding_box() if view=="settings" and sound.count() else None
 image=page.screenshot(animations="disabled",mask=masks,caret="hide")
 if errors:raise AssertionError(f"{name}: JS errors {errors}")
 page.close()
 return image,sound_box

with sync_playwright() as pw:
 browser=pw.chromium.launch(channel="msedge",headless=True) if os.name=="nt" else pw.chromium.launch(
  executable_path=shutil.which("chromium") or shutil.which("chromium-browser"),headless=True,args=["--no-sandbox"])
 for item in SCENARIOS:
  a,old_sound=screenshot(browser,REF,item)
  b,new_sound=screenshot(browser,APP,item)
  from PIL import Image,ImageChops,ImageDraw
  from io import BytesIO
  x,y=Image.open(BytesIO(a)).convert("RGBA"),Image.open(BytesIO(b)).convert("RGBA")
  # Only the union of the two sound-option rectangles is exempted. Every
  # surrounding card, timer band, footer and mini footprint must match.
  if old_sound and new_sound:
   left=max(0,int(min(old_sound["x"],new_sound["x"])-2))
   top=max(0,int(min(old_sound["y"],new_sound["y"])-2))
   right=min(x.width,int(max(old_sound["x"]+old_sound["width"],new_sound["x"]+new_sound["width"])+3))
   bottom=min(x.height,int(max(old_sound["y"]+old_sound["height"],new_sound["y"]+new_sound["height"])+3))
   if right>left and bottom>top:
    for img in (x,y):ImageDraw.Draw(img).rectangle((left,top,right,bottom),fill=(0,0,0,255))
  d=ImageChops.difference(x,y)
  if d.getbbox():
   Path("visual-baseline-before.png").write_bytes(a)
   Path("visual-baseline-after.png").write_bytes(b)
   d.save("visual-baseline-diff.png")
   raise AssertionError(f"Visual regression outside sound button {item[0]}: {d.getbbox()}")
  print("Pixel-identical outside sound test control:",item[0],flush=True)
 browser.close()
print(f"Visual baseline: {len(SCENARIOS)} scenarios unchanged outside the new sound control")
