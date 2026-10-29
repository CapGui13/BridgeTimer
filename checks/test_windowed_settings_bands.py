"""Guard approved native-size Settings bands in *windowed* mode.

Measures rendered boxes, not just CSS font-size, because transform:scale()
previously made all buttons visually tiny while UI tests still passed.
"""
from pathlib import Path
import os
import shutil
from playwright.sync_api import sync_playwright

html = (Path(__file__).resolve().parents[1] / "timer.html").read_text(encoding="utf-8")
html = html.replace("localStorage", "bridgeAuditStorage")
marker = "</style></head><body>"
assert marker in html
html = html.replace(marker, """</style><script>
const bridgeAuditStorage={data:{},getItem(k){return this.data[k]??null},
setItem(k,v){this.data[k]=v},removeItem(k){delete this.data[k]}};
</script></head><body>""", 1)

def close_to(value, target, name, tolerance=1.25):
    assert abs(value - target) <= tolerance, f"{name}: {value:.2f}px, expected {target}px"

def measure(page):
    return page.evaluate("""() => {
      const rect=q=>{const e=document.querySelector(q),
        r=e.getBoundingClientRect(),cs=getComputedStyle(e);
        return {left:r.left,right:r.right,top:r.top,bottom:r.bottom,
          height:r.height,font:parseFloat(cs.fontSize),visible:cs.visibility!=="hidden"};
      };
      return {
        top:rect('#settings .wrap>.head'),
        title:rect('#settings .wrap>.head h1'),
        topBtn:rect('#settingsFullscreenBtn'),
        footer:rect('#settings .actions'),
        start:rect('#fresh'),
        quit:rect('#quitAppBtn'),
        label:rect('#settings .grid label'),
        mini:rect('#miniTimer')
      };
    }""")

with sync_playwright() as pw:
    if os.name == "nt":
        browser = pw.chromium.launch(channel="msedge", headless=True)
    else:
        executable = shutil.which("chromium") or shutil.which("chromium-browser")
        browser = pw.chromium.launch(executable_path=executable, headless=True,
                                     args=["--no-sandbox"])
    for width, height in [(684,546),(812,640),(960,640)]:
        page=browser.new_page(viewport={"width":width,"height":height})
        errors=[]
        page.on("pageerror",lambda e: errors.append(str(e)))
        page.set_content(html,wait_until="domcontentloaded")
        page.wait_for_timeout(150)
        for live in (False, True):
            page.evaluate("live=>document.body.classList.toggle('settingsLive',live)",live)
            if live:
                page.evaluate("document.getElementById('miniTimer').classList.add('spView')")
            m=measure(page)
            assert not errors, f"{width}px JavaScript errors: {errors[:2]}"
            for element,size in (("top",55),("footer",59),
                                 ("topBtn",34),("start",40),("quit",40)):
                close_to(m[element]["height"], size, f"{width}px live={live} {element}")
            for element,size in (("title",34),("topBtn",12),("start",13),("quit",13)):
                close_to(m[element]["font"], size, f"{width}px live={live} {element} font", 1.5)
            close_to(m["label"]["font"], 13, f"{width}px label font")
            for element in ("top","footer"):
                assert abs(m[element]["left"])<1 and m[element]["right"]<=width+1, \
                    f"{width}px {element} detached from viewport: {m[element]}"
            assert m["topBtn"]["right"] <= width-5, f"{width}px Fullscreen button clipped"
            assert m["quit"]["right"] <= width-5, f"{width}px Quitter clipped"
            assert m["start"]["right"] < m["quit"]["left"], \
                f"{width}px footer buttons overlap"
            if live:
                close_to(m["mini"]["left"],0,f"{width}px mini left")
                close_to(m["mini"]["bottom"],height,f"{width}px mini bottom")
        page.close()
    # 812x520 is the outer Windows frame. A standard caption removes about
    # 30-40 logical pixels, so exercise the effective 480px WebView height.
    # Tournament must fit ABOVE the permanent footer in both formats.
    page=browser.new_page(viewport={"width":812,"height":480})
    page.set_content(html,wait_until="domcontentloaded")
    for mode in ("4","2"):
        page.evaluate("mode=>{s.mode=mode;fill();updateStage()}",mode)
        m=page.evaluate("""() => {
          const card=document.querySelector('.tournamentCard').getBoundingClientRect();
          const footer=document.querySelector('#settings .actions').getBoundingClientRect();
          const bar=document.querySelector('#settings .head').getBoundingClientRect();
          return {cardBottom:card.bottom,footerTop:footer.top,footerBottom:footer.bottom,
            headBottom:bar.bottom,scrollHeight:document.scrollingElement.scrollHeight};
        }""")
        assert m["cardBottom"]<=m["footerTop"]-8,             f"812x520 native frame hides Tournament bottom ({mode}): {m}"
        assert m["scrollHeight"]>480, "Advanced settings must remain scrollable"
    page.close()
    browser.close()
print("Settings band geometry OK: 684/812/960px + Tournament visible in 812x520")
