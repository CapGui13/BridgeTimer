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
                background=page.evaluate("getComputedStyle(document.getElementById('timer')).backgroundColor")
                for p in phases:
                    phase(page,p)
                    equal(before,measure(page),f"{width}x{height}, {mode}, {p}")
                    if p in ("break","jump"):
                        col=page.evaluate("getComputedStyle(document.getElementById('timer')).backgroundColor")
                        assert col==background, "Transition recolored permanent bands"
                        visible=page.evaluate("getComputedStyle(document.getElementById('jumpSplash')).display")
                        assert visible!="none", "Transition overlay vanished"
                beforeNative=page.evaluate("window.__viewCalls.length")
                page.evaluate("q25(true)")
                assert page.evaluate("window.__viewCalls.length")==beforeNative, "Entering fullscreen changed native window"
                page.evaluate("q25(false)")
                assert page.evaluate("window.__viewCalls.at(-1).mode")=="timer", "Leaving fullscreen lost timer mode"
                equal(before,measure(page),f"{width}x{height}, {mode}, fullscreen toggle")
                # Each transition phase must leave the NATIVE window alone.
                assert page.evaluate("window.__viewCalls.length")==1, "Phase changed native window unexpectedly"
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
