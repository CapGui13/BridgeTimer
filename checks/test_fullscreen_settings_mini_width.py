"""Fullscreen Settings live mini-timer touches the LEFT edge of the Tournament card at 16:9.

The miniature stays at the WINDOW bottom-left, at the same ratio, and returns
to its previous size when fullscreen ends. The timer / jump phases are not
modified. Test against REAL CSS geometry in Edge, not a DOM string alone.
"""
from pathlib import Path
import os,shutil
from playwright.sync_api import sync_playwright

html=(Path(__file__).resolve().parents[1]/"timer.html").read_text(encoding="utf8")
html=html.replace("localStorage","bridgeAuditStorage").replace(
 "</style></head><body>",
 """</style><script>const bridgeAuditStorage={data:{},
 getItem(k){return this.data[k]??null},setItem(k,v){this.data[k]=v},
 removeItem(k){delete this.data[k]}};</script></head><body>""",1)

def metric(page):
 return page.evaluate("""()=>{
  const rect=x=>{const r=x.getBoundingClientRect();
   return {x:r.x,y:r.y,w:r.width,h:r.height,right:r.right,bottom:r.bottom}};
  const mini=document.querySelector('#miniTimer'),first=document.querySelector('#fresh');
  const iframe=document.querySelector('#faithfulMiniFrame');
  const foot=document.querySelector('#settings .actions');
  const tournamentCard=document.querySelector('#settings .tournamentCard');
  return {mini:rect(mini),first:rect(first),foot:rect(foot),
   tournamentCard:rect(tournamentCard),
   frame:iframe?rect(iframe):null,
   fullscreen:document.body.classList.contains('fs'),
   live:document.body.classList.contains('settingsLive'),
   var:mini.style.getPropertyValue('--fullscreen-mini-width'),
   visible:getComputedStyle(mini).display,
   viewport:{w:innerWidth,h:innerHeight}};
 }""")

with sync_playwright() as pw:
 if os.name=="nt":browser=pw.chromium.launch(channel="msedge",headless=True)
 else:browser=pw.chromium.launch(executable_path=shutil.which("chromium") or shutil.which("chromium-browser"),
                                     headless=True,args=["--no-sandbox"])
 for width,height in ((960,600),(1280,720),(1650,928),(1920,1080)):
  page=browser.new_page(viewport={"width":width,"height":height})
  errors=[]
  page.on("pageerror",lambda e:errors.append(str(e)))
  page.set_content(html,wait_until="domcontentloaded")
  for mode in ("4","2"):
   page.evaluate("""mode=>{
     s.mode=mode;s.positions=6;s.between=30;st.started=true;
     st.running=false;st.phase='round';st.remaining=3590;st.roundDuration=3600;
     showTimer();showSettings(false);render();
   }""",mode)
   pre=metric(page)
   assert pre["live"] and not pre["fullscreen"],(width,mode,pre)
   assert pre["mini"]["w"]<=260.2 and pre["mini"]["w"]>0,(width,mode,pre)
   page.evaluate("q25(true);render();syncFaithfulMini(true)")
   page.wait_for_function("document.querySelector('#faithfulMiniFrame')?.contentDocument?.body?.children.length>0")
   a=metric(page)
   assert a["fullscreen"] and a["live"] and a["visible"]=="block",(width,mode,a)
   assert abs(a["mini"]["x"])<=.6,(width,mode,a)
   assert abs(a["mini"]["w"]/a["mini"]["h"]-16/9)<.015,(width,mode,a)
   assert abs(a["mini"]["right"]-a["tournamentCard"]["x"])<=1.1,(width,mode,"mini must touch LEFT BORDER of settings cards",a)
   assert abs(a["mini"]["bottom"]-height)<=.6,(width,mode,"mini must be flush with window bottom",a)
   assert a["mini"]["right"]<=a["first"]["x"],(width,mode,"mini must not cover first footer command",a)
   # The 1px preview border clips the scaled iframe by 2px in width.
   assert a["frame"] is not None and abs(a["frame"]["w"]-(a["mini"]["w"]-2))<1.5,(width,mode,a)
   assert abs(a["frame"]["h"]-(a["mini"]["h"]-2))<1.5,(width,mode,a)
   # Fixed bands remain opaque, and the maximum scroll stops at an equal
   # spacing: header-to-first-card == last-card-to-footer.
   top=page.evaluate("""() => {
     const rect=s=>document.querySelector(s).getBoundingClientRect();
     const header=document.querySelector('#settings .wrap>.head');
     const c=getComputedStyle(header).backgroundColor;
     return {gap:rect('#settings .tournamentCard').top-header.getBoundingClientRect().bottom,
       color:c,opacity:getComputedStyle(header).opacity};
   }""")
   assert top["color"].startswith("rgb(") or top["color"].endswith(", 1)"),(width,mode,"Header must be opaque",top)
   assert top["opacity"]=="1",(width,mode,top)
   page.evaluate("window.scrollTo(0,document.documentElement.scrollHeight)")
   page.wait_for_function("window.scrollY > 20")
   scrolled=page.evaluate("""() => {
     const rect=s=>document.querySelector(s).getBoundingClientRect();
     const last=document.querySelector('#settings .wrap > .card:last-child');
     const h=document.querySelector('#settings .wrap>.head');
     return {gap:rect('#settings .actions').top-last.getBoundingClientRect().bottom,
       scrollY:window.scrollY,max:document.documentElement.scrollHeight-innerHeight,
       headTop:h.getBoundingClientRect().top,
       color:getComputedStyle(h).backgroundColor};
   }""")
   assert abs(scrolled["gap"]-top["gap"])<=2.5,(width,mode,"Max-scroll bottom margin must match top margin",top,scrolled)
   assert scrolled["color"]==top["color"],(width,mode,"Header changed while scrolling",scrolled)
   assert abs(scrolled["scrollY"]-scrolled["max"])<=2.0,(width,mode,"Scroll wasn't at bottom",scrolled)
   # Double-click on the FULLSCREEN mini must return to the TIMER.
   if (width,height)==(1650,928) and mode=="4":
    page.screenshot(path="mini-preview-scrolled-1650x928.png",full_page=False)
   page.locator("#miniTimer").dblclick()
   assert page.evaluate("document.getElementById('settings').classList.contains('hidden')"),(width,mode,"Mini double-click did not return to timer")
   assert page.evaluate("!document.getElementById('timer').classList.contains('hidden')"),(width,mode)
   page.evaluate("showSettings(false);render()")
   page.evaluate("window.scrollTo(0,0)")

   # Chromium/Edge screenshot at the user's exact reference resolution;
   # CI publishes it separately for visual inspection, not as a substitute
   # for the native Windows executable check.
   if (width,height)==(1650,928) and mode=="4":
    page.screenshot(path="mini-preview-1650x928.png",full_page=False)
   page.evaluate("q25(false);render()")
   b=metric(page)
   assert not b["fullscreen"] and b["live"],(width,mode,b)
   assert b["var"]=="",(width,mode,"fullscreen-only custom size leaked",b)
   assert abs(b["mini"]["w"]-pre["mini"]["w"])<=.5,(width,mode,"windowed mini size changed",pre,b)
   assert abs(b["mini"]["bottom"]-height)<=.6,(width,mode,b)
  assert not errors,(width,errors)
  page.close()
 browser.close()
print("Fullscreen mini geometry, double-click, opaque header and balanced scrolling: 4 viewports x 2 modes OK")
