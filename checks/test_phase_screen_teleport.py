"""Check that Saut and Changement de tour REPLACE the center instantly.

This must behave as an actual screen swap (Settings <-> Timer), not as an
overlay animation over still-visible clock content. Run in Edge on Windows.
"""
from pathlib import Path
import os,shutil
from playwright.sync_api import sync_playwright

html=(Path(__file__).resolve().parents[1]/"timer.html").read_text(encoding="utf8")
html=html.replace("localStorage","bridgeAuditStorage").replace(
"</style></head><body>",
"""</style><script>const bridgeAuditStorage={
data:{},getItem(k){return this.data[k]??null},
setItem(k,v){this.data[k]=v},removeItem(k){delete this.data[k]}
};</script></head><body>""",1)

with sync_playwright() as pw:
    if os.name=="nt": browser=pw.chromium.launch(channel="msedge",headless=True)
    else: browser=pw.chromium.launch(
      executable_path=shutil.which("chromium") or shutil.which("chromium-browser"),
      headless=True,args=["--no-sandbox"])

    for width,height in [(812,480),(960,560),(1280,720),(1600,900)]:
        page=browser.new_page(viewport={"width":width,"height":height})
        errors=[]
        page.on("pageerror",lambda e:errors.append(str(e)))
        page.set_content(html,wait_until="domcontentloaded")
        for mode,secs in [("2",3590),("4",3600)]:
            page.evaluate("""([mode,secs])=>{
                s.mode=mode;s.positions=6;s.between=16;s.jumpDisplaySecs=13;
                st.started=true;st.running=false;st.pos=1;st.phase='round';
                st.remaining=secs;st.roundDuration=secs;
                st.longClockAtStart=secs>=3600;
                showTimer();render();
            }""",[mode,secs])

            def geometry():
                return page.evaluate("""()=>{
                  const r=q=>{const b=document.querySelector(q).getBoundingClientRect();
                    return {x:b.x,y:b.y,w:b.width,h:b.height}};
                  return {top:r('#timer .top'),bottom:r('#timer .bottom'),main:r('#timer .main')}
                }""")
            base=geometry()
            for phase,remaining in [
                ("jump",13),("break",16),("round",secs),
                ("jump",9),("round",secs),("break",2),("round",secs)
            ]:
                out=page.evaluate("""([phase,remaining])=>{
                  st.phase=phase;st.remaining=remaining;st.breakDuration=16;render();
                  const main=document.querySelector('#timer .main');
                  const splash=document.querySelector('#jumpSplash');
                  return {
                    swapped:main.classList.contains('phasePage'),
                    splash:getComputedStyle(splash).display,
                    previous:getComputedStyle(document.querySelector('#clock')).display,
                    clockFont:document.querySelector('#clock').style.fontSize,
                    animations:splash.getAnimations({subtree:true}).length,
                    seconds:document.querySelector('#jumpSplashSeconds').textContent
                  }
                }""",[phase,remaining])
                transitioning=phase in ("jump","break")
                assert out["swapped"]==transitioning,(width,mode,phase,out)
                if transitioning:
                    assert out["splash"]=="flex" and out["previous"]=="none",out
                    assert out["animations"]==0,out
                    assert out["seconds"]==str(remaining),out
                else:
                    assert out["splash"]=="none" and out["previous"]!="none",out
                    assert out["clockFont"],out
                current=geometry()
                for area in ("top","bottom","main"):
                    for coord in ("x","y","w","h"):
                        assert abs(current[area][coord]-base[area][coord])<.1,(
                            width,mode,phase,area,coord,current,base)
            page.evaluate("showSettings(false)")
            assert page.evaluate("!document.querySelector('#settings').classList.contains('hidden')")
            page.evaluate("showTimer()")
            assert page.evaluate("!document.querySelector('#timer').classList.contains('hidden')")
            assert not errors,(width,mode,errors)
        page.close()
    browser.close()
print("Teleportation jump/between: 4 sizes x 2 modes x 7 transitions, without band movement")
