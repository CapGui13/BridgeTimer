"""HTTP-served browser smoke tests for GitHub Pages BridgeTimer Light.

This deliberately opens index.html over a real local HTTP origin, not a
WebView2/native mock or a data: URL. Checks both tournament modes and short/
long clocks, settings, full-screen CSS behavior and the absence of UI errors.
"""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
import os, shutil
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
HTML=(ROOT/"index.html").read_text(encoding="utf-8")
FULL=(ROOT/"timer.html").read_text(encoding="utf-8")
assert "BridgeTimer Light — navigateur" in HTML
assert 'window.location.assign("https://github.com/CapGui13/BridgeTimer")' in HTML
assert "<h1>BridgeTimer Light</h1>" in HTML
assert "EDITION EPUREE" in HTML
assert "EDITION EPUREE" not in FULL, "Full Windows must not use the Light UI"
assert "window.close();throw new Error" in FULL, "Full Windows exit behavior changed"
assert "window.close();throw new Error" not in HTML

class Handler(SimpleHTTPRequestHandler):
 def log_message(self,*args):pass

server=ThreadingHTTPServer(("127.0.0.1",0),partial(Handler,directory=str(ROOT)))
Thread(target=server.serve_forever,daemon=True).start()
base=f"http://127.0.0.1:{server.server_address[1]}/"
try:
 with sync_playwright() as pw:
  if os.name=="nt":browser=pw.chromium.launch(channel="msedge",headless=True)
  else:browser=pw.chromium.launch(executable_path=shutil.which("chromium") or shutil.which("chromium-browser"),headless=True,args=["--no-sandbox"])
  for width,height in ((812,490),(1280,720),(1600,900)):
   for mode,longclock in (("2",False),("4",True)):
    context=browser.new_context(viewport={"width":width,"height":height})
    page=context.new_page()
    errors=[]
    page.on("pageerror",lambda e:errors.append(str(e)))
    response=page.goto(base,wait_until="domcontentloaded",timeout=30000)
    assert response.status==200,(width,height,mode,response.status)
    page.wait_for_function("typeof recoveryArmed!=='undefined'&&recoveryArmed",timeout=25000)
    assert page.locator("h1").first.inner_text()=="BridgeTimer Light"
    assert page.locator("#settings").is_visible()
    assert not page.locator("#colorMenuBtn").is_visible()
    assert not page.locator("#spb").is_visible()
    assert page.locator("#clubName").is_visible()
    assert page.locator("#eventName").is_visible()
    page.evaluate("""args=>{
     Object.assign(s,{mode:args.mode,positions:6,
       eventName:"Finale du Comité — Essai navigateur",
       hours:args.isLong?1:0,minutes:args.isLong?5:45,seconds:0,
       pairCount:26,boardProgressNotice:false,jumpAdvanceNotice:false,sound:false});
     Object.assign(st,{started:false,phase:"round",running:false,
       longClockAtStart:args.isLong});
     fill();
    }""",{"mode":mode,"isLong":longclock})
    page.click("#fresh")
    page.wait_for_function("document.getElementById('timer')?.classList.contains('roundReading')",timeout=20000)
    live=page.evaluate("""()=>{
      const t=document.querySelector("#timer"),c=document.querySelector("#clock");
      return {visible:!t.classList.contains("hidden"),running:st.running,
        text:c.textContent,long:c.classList.contains("longStartClock"),
        title:document.querySelector("#status").textContent,
        stage:t.style.getPropertyValue("--stage-scale")}
    }""")
    assert live["visible"] and live["running"],(width,height,mode,live)
    assert live["long"]==longclock,(width,height,mode,live)
    assert ("Finale du Comité" in live["title"]),(width,height,mode,live)
    assert live["stage"],(width,height,mode,live)
    page.click("#pause")
    page.wait_for_function("!st.running")
    assert page.locator("#pauseOverlay").evaluate("(e)=>e.classList.contains('on')")
    page.click("#pause")
    assert page.evaluate("st.running")
    page.evaluate("q25(true)")
    assert page.evaluate("document.body.classList.contains('fs')")
    page.evaluate("q25(false)")
    assert not page.evaluate("document.body.classList.contains('fs')")
    page.evaluate("showSettings(false)")
    assert page.locator("#settings").is_visible()
    page.evaluate("document.body.classList.add('debugMode');_adu()")
    assert not page.locator("#colorMenuBtn").is_visible()
    assert not page.locator("#spb").is_visible()
    assert page.locator("#quitAppBtn").is_visible()
    assert not errors,(width,height,mode,errors)
    context.close()
  browser.close()
 print("BROWSER LIGHT PASS: live HTTP, 3 windows x 2 modes, pause/resume, full-screen, hidden Light controls")
finally:
 server.shutdown()
 server.server_close()
