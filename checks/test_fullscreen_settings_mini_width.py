"""Fullscreen Settings live mini-timer aligns with first menu button at 16:9.

The miniature remains pinned to bottom-left, at the same ratio, and returns
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
  return {mini:rect(mini),first:rect(first),foot:rect(foot),
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
   assert abs(a["mini"]["x"])<=.6 and abs(a["mini"]["bottom"]-height)<=.6,(width,mode,a)
   assert abs(a["mini"]["w"]/a["mini"]["h"]-16/9)<.015,(width,mode,a)
   gap=a["first"]["x"]-a["mini"]["right"]
   assert gap>=10.5,(width,mode,"overlaps menu commands",a)
   # In a desktop-height viewport the mini must almost reach first control.
   if height>=720 and a["first"]["x"]>250:
    assert gap<=15.5,(width,mode,"does not reach menu commands",a)
    assert a["mini"]["w"]>pre["mini"]["w"]*1.08,(width,mode,"not enlarged",a)
   # The 1px preview border clips the scaled iframe by 2px in width.
   assert a["frame"] is not None and abs(a["frame"]["w"]-(a["mini"]["w"]-2))<1.5,(width,mode,a)
   assert abs(a["frame"]["h"]-(a["mini"]["h"]-2))<1.5,(width,mode,a)
   page.evaluate("q25(false);render()")
   b=metric(page)
   assert not b["fullscreen"] and b["live"],(width,mode,b)
   assert b["var"]=="",(width,mode,"fullscreen-only custom width leaked",b)
   assert abs(b["mini"]["w"]-pre["mini"]["w"])<=.5,(width,mode,"windowed mini size changed",pre,b)
   assert abs(b["mini"]["bottom"]-height)<=.6,(width,mode,b)
  assert not errors,(width,errors)
  page.close()
 browser.close()
print("Fullscreen Settings 16:9 mini reaches footer menu at 960,1280,1650,1920; windowed restored")
