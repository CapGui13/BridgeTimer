"""Edition epuree: color customization and Screen Tests are absent from the
visible, keyboard-accessible UI, including in Debug and fullscreen.

All existing timer controls, identity fields and stored color theme remain
functional. Run on Windows Edge (or local Chromium).
"""
from pathlib import Path
import os,shutil
from playwright.sync_api import sync_playwright

html=(Path(__file__).resolve().parents[1]/"timer.html").read_text(encoding="utf-8")
html=html.replace("localStorage","epureeStorage").replace("</style></head><body>",
 """</style><script>const epureeStorage={data:{},getItem(k){return this.data[k]??null},
 setItem(k,v){this.data[k]=v},removeItem(k){delete this.data[k]}};</script></head><body>""",1)

SAMPLE="""()=>{
 const id=k=>document.getElementById(k),visible=k=>{
   const el=id(k),cs=getComputedStyle(el),r=el.getBoundingClientRect();
   return cs.display!=="none"&&cs.visibility!=="hidden"&&r.width>0&&r.height>0;
 };
 return {
  colorButton:visible("colorMenuBtn"),
  colorLabelVisible:(()=>{
    const el=document.querySelector('label[for="colorMenuBtn"]');
    return getComputedStyle(el).display!=="none"&&!!el.getClientRects().length;
  })(),
  screenButton:visible("spb"),
  clubName:visible("clubName"),eventName:visible("eventName"),
  identityCard:id("clubName").closest(".card").querySelector("h2").textContent,
  controls:Object.fromEntries(["fresh","defaults","debugBtn","quitAppBtn"].map(k=>[k,visible(k)])),
  colorDialog:id("colorMenuOverlay").classList.contains("hidden"),
  themeTest:id("themeTest").classList.contains("hidden"),
  screensGallery:id("spg").classList.contains("hidden"),
  theme:getComputedStyle(document.documentElement).getPropertyValue("--accent").trim(),
  heading:id("status").textContent,
  time:id("clock").textContent,
  settingsShown:!id("settings").classList.contains("hidden")
 };
}"""

with sync_playwright() as pw:
 if os.name=="nt":browser=pw.chromium.launch(channel="msedge",headless=True)
 else:browser=pw.chromium.launch(executable_path=shutil.which("chromium") or shutil.which("chromium-browser"),
   headless=True,args=["--no-sandbox"])
 for width,height in ((812,490),(1280,720),(1600,900),(1920,1080)):
  page=browser.new_page(viewport={"width":width,"height":height})
  errors=[];page.on("pageerror",lambda e:errors.append(str(e)))
  page.set_content(html,wait_until="domcontentloaded")
  for mode in ("2","4"):
   page.evaluate("""mode=>{
    Object.assign(s,{mode,positions:6,pairCount:26,
      eventName:"Senior Mixte /2 - Finale de Comité",
      clubName:"FFB - Comité de Provence",hours:0,minutes:45,seconds:0,
      boardProgressNotice:false,jumpAdvanceNotice:false,sound:false});
    Object.assign(st,{started:false,running:false,phase:"round",pos:1,
      remaining:2700,roundDuration:2700,longClockAtStart:false});
    document.body.classList.remove("debugMode");
    showSettings(false);
   }""",mode)
   sample=page.evaluate(SAMPLE)
   assert sample["identityCard"]=="Informations affichées",(width,height,mode,sample)
   assert sample["settingsShown"] and sample["clubName"] and sample["eventName"],(width,height,mode,sample)
   assert not sample["colorButton"] and not sample["colorLabelVisible"],(width,height,mode,sample)
   assert not sample["screenButton"],(width,height,mode,sample)
   assert all(sample["controls"].values()),(width,height,mode,sample)
   assert sample["colorDialog"] and sample["themeTest"] and sample["screensGallery"],(width,height,mode,sample)
   # Hidden entries must not gain keyboard focus or reappear in Debug.
   page.evaluate("""()=>{
    document.body.classList.add("debugMode");
    document.getElementById("colorMenuBtn").focus();
   }""")
   assert not page.evaluate("document.activeElement?.id==='colorMenuBtn'"),(width,height,mode,"color button focusable")
   debug=page.evaluate(SAMPLE)
   assert not debug["colorButton"] and not debug["screenButton"],(width,height,mode,debug)
   # Preserve existing saved colors, but never expose palette controls.
   page.evaluate("""()=>{
    Object.assign(s,{accent:"#654321",background:"#0f172a",
      menu:"#111827",text:"#f8fafc"});
    fill();
   }""")
   recolored=page.evaluate(SAMPLE)
   assert recolored["theme"]=="#654321",(width,height,mode,recolored)
   assert not recolored["colorButton"],(width,height,mode,recolored)
   # Switching to a real running countdown and back to Settings is safe.
   page.evaluate("""()=>{
    Object.assign(st,{started:true,running:false,phase:"round",pos:1,
       remaining:2700,roundDuration:2700,longClockAtStart:false});
    showTimer();render();
   }""")
   live=page.evaluate(SAMPLE)
   assert not live["settingsShown"] and "Senior Mixte" in live["heading"] and "45:00" in live["time"],(width,height,mode,live)
   page.evaluate("showSettings(false);q25(true)")
   fullscreen=page.evaluate(SAMPLE)
   assert fullscreen["settingsShown"] and not fullscreen["colorButton"] and not fullscreen["screenButton"],(width,height,mode,fullscreen)
   page.evaluate("q25(false)")
   assert not errors,(width,height,mode,errors)
  page.close()
 browser.close()
print("EDITION EPUREE PASS: hidden palettes/screens even in Debug; visible identity, settings, live timer and saved theme (4 viewports x 2 modes)")
