"""Checks UI invariants in a real Chromium/Edge browser, including screen previews."""
from pathlib import Path
import os
import shutil
from playwright.sync_api import sync_playwright

html = Path(__file__).resolve().parents[1].joinpath("timer.html").read_text(encoding="utf-8")
# about:blank has no localStorage; substitute a disposable test-only store.
html = html.replace("localStorage", "bridgeAuditStorage")
marker = "</style></head><body>"
assert marker in html
html = html.replace(marker, '</style><script>const bridgeAuditStorage={data:{},getItem(k){return this.data[k]??null},setItem(k,v){this.data[k]=v},removeItem(k){delete this.data[k]}};</script></head><body>', 1)
sels = ["#timer", "#timer>.top", "#timer .bottom", "#timer .identity",
        "#timer .topBtns", "#timer .controls", "#localTime", "#round", "#club"]
viewports = [(812,500),(960,720),(1280,720),(1600,900),(1920,1080)]
phases = ["round","break","round","jump","round","roundEnd","round","ended","round"]

def measure(page):
    return page.evaluate("""sels => Object.fromEntries(sels.map(sel => {
      const e=document.querySelector(sel),r=e.getBoundingClientRect(),s=getComputedStyle(e);
      return [sel,[r.x,r.y,r.width,r.height].map(x=>Math.round(x*100)/100).concat([s.fontSize,s.display])];
    }))""", sels)

def equal(before, after, context, exclusions=()):
    for sel in sels:
        if sel not in exclusions and before[sel] != after[sel]:
            raise AssertionError(f"{context}: {sel} moved: {before[sel]} -> {after[sel]}")

def phase(page, p):
    page.evaluate("p=>{st.phase=p;st.remaining=10;st.breakDuration=30;render()}",p)

def main():
    errors=[]
    with sync_playwright() as pw:
        if os.name=="nt":
            browser=pw.chromium.launch(channel="msedge",headless=True)
        else:
            path=shutil.which("chromium") or shutil.which("chromium-browser")
            browser=pw.chromium.launch(executable_path=path,headless=True,args=["--no-sandbox"])
        for width,height in viewports:
            page=browser.new_page(viewport={"width":width,"height":height})
            page.on("pageerror",lambda err: errors.append(str(err)))
            page.set_content(html,wait_until="domcontentloaded")
            assert page.evaluate("typeof render")=="function", "Timer failed to initialize"
            # Input in settings selects its existing content even on a click.
            field=page.locator("#quickMessage")
            field.fill("Texte déjà enregistré")
            field.click()
            assert page.evaluate("""() => {
              const e=document.getElementById('quickMessage');
              return e.selectionStart===0 && e.selectionEnd===e.value.length
            }"""), "Settings temporary-message field did not select all content on click"
            page.evaluate("""() => {
              document.getElementById("quickMessage").value="";
              document.activeElement.blur();
            }""")
            page.evaluate("""() => {
              window.__viewCalls=[];
              window.nativeSetView=(mode,serial)=>{window.__viewCalls.push({mode,serial});return Promise.resolve(true)};
            }""")
            for mode in ["4","2"]:
                page.evaluate("""mode=>{
                    s.mode=mode;s.positions=6;s.between=30;s.jumpDisplaySecs=15;
                    s.eventName='Senior Mixte - 1/2 Finale';s.clubName='FFB - Comité de Provence';
                    st.pos=2;st.remaining=128;st.roundDuration=3600;st.roundBetween=30;
                    st.breakDuration=30;st.started=true;st.running=true;st.phase='round';
                    document.getElementById('settings').classList.add('hidden');
                    document.getElementById('timer').classList.remove('hidden');render();
                }""", mode)
                before=measure(page)
                # Pressing M while a message is actually displayed must HIDE it
                # without opening the form or erasing the saved text. A second
                # real key press alone opens the prefilled composer.
                page.evaluate("""() => {
                  s.quickMessage="Message à masquer";
                  tempMessageUntil=Date.now()+60000;
                  render();
                }""")
                page.keyboard.press("m")
                assert page.evaluate("""() => !q16() &&
                  document.getElementById("tempMessageOverlay").classList.contains("hidden") &&
                  s.quickMessage==="Message à masquer"
                """), "First M must dismiss the displayed temporary message only"
                page.keyboard.press("m")
                assert page.evaluate("""() => !document.getElementById("tempMessageOverlay").classList.contains("hidden") &&
                  document.getElementById("tempMessageInput").value==="Message à masquer"
                """), "Second M must open composer with original saved text"
                page.evaluate("q20()")
                page.evaluate("""() => {s.quickMessage="";render()}""")
                background=page.evaluate("getComputedStyle(document.getElementById('timer')).backgroundColor")
                phaseNativeCount=page.evaluate("window.__viewCalls.length")
                for p in phases:
                    phase(page,p)
                    equal(before,measure(page),f"{width}x{height}, {mode}, {p}")
                    if p in ("break","jump"):
                        col=page.evaluate("getComputedStyle(document.getElementById('timer')).backgroundColor")
                        assert col==background, "Transition recolored permanent bands"
                        visible=page.evaluate("getComputedStyle(document.getElementById('jumpSplash')).display")
                        assert visible!="none", "Transition overlay vanished"
                assert page.evaluate("window.__viewCalls.length")==phaseNativeCount, "Phase changed native window unexpectedly"
                beforeNative=page.evaluate("window.__viewCalls.length")
                page.evaluate("q25(true)")
                assert page.evaluate("window.__viewCalls.length")==beforeNative, "Entering fullscreen changed native window"
                page.evaluate("q25(false)")
                assert page.evaluate("window.__viewCalls.at(-1).mode")=="timer", "Leaving fullscreen lost timer mode"
                equal(before,measure(page),f"{width}x{height}, {mode}, fullscreen toggle")
                # Fullscreen settings must share the EXACT 1600x900
                # timer header geometry, despite using distinct content.
                page.evaluate("q25(true)")
                rects=page.evaluate("""() => {
                  const b=sel=>{const r=document.querySelector(sel).getBoundingClientRect();
                    return {x:r.x,y:r.y,w:r.width,h:r.height};};
                  return {
                    band:b("#timer .top"),title:b("#club"),
                    settings:b("#settingsBtn"),exit:b("#fsBtn")
                  }
                }""")
                page.evaluate("showSettings()")
                rects2=page.evaluate("""() => {
                  const b=sel=>{const r=document.querySelector(sel).getBoundingClientRect();
                    return {x:r.x,y:r.y,w:r.width,h:r.height};};
                  return {
                    band:b("#settings .wrap>.head"),title:b("#settings .head h1"),
                    settings:b("#drawerClose"),exit:b("#settingsFullscreenBtn"),
                    mini:b("#miniTimer"),viewport:{h:innerHeight},
                    miniInBody:document.getElementById("miniTimer").parentElement===document.body,
                    exitWired:document.getElementById("settingsFullscreenBtn").onclick===fs,
                    closeText:document.getElementById("drawerClose").textContent,
                    visible:getComputedStyle(document.getElementById("settingsFullscreenBtn")).display!=="none"
                  }
                }""")
                for key in ["band","settings","exit"]:
                    for metric in ["x","y","w","h"]:
                        diff=abs(rects[key][metric]-rects2[key][metric])
                        assert diff<=1.1, f"Fullscreen header misaligned: {width}x{height} {mode} {key}.{metric} diff {diff:.2f}"
                assert abs(rects["title"]["h"]-rects2["title"]["h"])<=1.1, "Settings heading font doesn't match club font"
                assert rects2["closeText"]=="Timer" and rects2["visible"] and rects2["exitWired"], "Settings fullscreen header buttons misconfigured"
                assert rects2["miniInBody"], "Miniature still inside the footer"
                assert abs(rects2["mini"]["x"])<0.1 and abs(rects2["mini"]["y"]+rects2["mini"]["h"]-rects2["viewport"]["h"])<0.1, "Miniature not pinned to bottom-left corner"
                page.evaluate("showTimer()")
                equal(measure(page),measure(page), "sanity")
                page.evaluate("q25(false)")
                page.evaluate("showSettings()")
                page.evaluate("showTimer()")
                calls=page.evaluate("window.__viewCalls.slice(-2)")
                assert [c["mode"] for c in calls]==["settings","timer"], f"Incorrect native mode changes: {calls}"
                assert calls[0]["serial"]<calls[1]["serial"], "Native mode requests not ordered"
                equal(before,measure(page),f"{width}x{height}, {mode}, settings return")
            before=measure(page)
            page.set_viewport_size({"width":1920,"height":1080})
            page.evaluate("q25(true)")
            phase(page,"jump")
            phase(page,"round")
            page.set_viewport_size({"width":width,"height":height})
            page.evaluate("q25(false)")
            equal(before,measure(page),f"{width}x{height}, fullscreen resize return")
            if (width,height)==(960,720):
                page.evaluate("showSettings()")
                page.evaluate("_osp()")
                page.evaluate("_ssp('jump')")
                page.evaluate("_ssp('between')")
                page.evaluate("_csp()")
                page.evaluate("showTimer()")
                restored=page.evaluate("!document.getElementById('timer').classList.contains('spm') && !document.getElementById('timer').classList.contains('spa')")
                assert restored,"Preview classes leaked to timer"
                # Auto movement may legitimately change round count and text width.
                equal(before,measure(page),"Screen previews return",exclusions=("#round",))
            page.close()
        browser.close()
    assert not errors, f"JavaScript runtime errors: {errors}"
    print("Browser visual regression OK: 5 viewport sizes, both modes, 9 phases, fullscreen and preview returns")

if __name__=="__main__":
    main()
