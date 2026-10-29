"""End-to-end functional audit on the shipped Bridge Timer HTML, using Edge.
No application code changes; this test protects the validated release.
"""
from pathlib import Path
import os
import shutil
from playwright.sync_api import sync_playwright

html=Path(__file__).resolve().parents[1].joinpath("timer.html").read_text(encoding="utf-8")
html=html.replace("localStorage","bridgeAuditStorage").replace("</style></head><body>",
  """</style><script>const bridgeAuditStorage={data:{},
getItem(k){return this.data[k]??null},setItem(k,v){this.data[k]=v},
removeItem(k){delete this.data[k]}};</script></head><body>""",1)

def snap(page):
    return page.evaluate("""() => ({
      mode:s.mode,positions:s.positions,pos:st.pos,phase:st.phase,
      started:st.started,running:st.running,remaining:st.remaining,
      roundDuration:st.roundDuration,longStart:st.longClockAtStart,
      screen:document.querySelector('#timer').classList.contains('hidden')?'settings':'timer',
      resumeHidden:document.querySelector('#resumeOverlay').classList.contains('hidden')
    })""")

def setup(page,mode="2",between=15,positions=3,secs=120,jumpRound=0):
    page.evaluate("""x=>{
      if(st.running)pause();
      clearInterval(st.interval);st.interval=null;
      st.started=true;showTimer();
      Object.assign(s,{mode:x.mode,positions:x.positions,hours:0,
        minutes:Math.floor(x.secs/60),seconds:x.secs%60,
        between:x.between,jumpRound:x.jumpRound,jumpDisplaySecs:8,
        startPosition:1,sound:false,resumeTime:''});
      st.pos=1;qa();q4a(1,false);st.running=false;st.endAt=null;render()
    }""",{"mode":mode,"between":between,"positions":positions,"secs":secs,"jumpRound":jumpRound})

def pairs_break_end(page):
    setup(page,between=18)
    page.evaluate("zadvance(0)")
    a=snap(page)
    assert (a["phase"],a["remaining"],a["pos"])==("break",18,1),a
    page.evaluate("zadvance(0)")
    b=snap(page)
    assert (b["phase"],b["remaining"],b["pos"])==("round",120,2),b
    page.evaluate("q4a(3,false);zadvance(0)")
    c=snap(page)
    assert c["phase"]=="ended" and not c["running"],c

def pairs_jump_break(page):
    setup(page,between=18,jumpRound=1)
    expected=[("jump",8),("break",18),("round",120)]
    for phase,time in expected:
        page.evaluate("zadvance(0)")
        a=snap(page)
        assert (a["phase"],a["remaining"])==(phase,time),a

def overshoot_carry(page):
    setup(page,between=10,positions=4)
    page.evaluate("zadvance(12)")
    a=snap(page)
    assert (a["pos"],a["phase"],a["remaining"])==(2,"round",118),a
    page.evaluate("zadvance(141)")
    b=snap(page)
    assert (b["pos"],b["phase"],b["remaining"])==(4,"round",119),b

def mp4_round_end(page):
    setup(page,mode="4",between=0)
    page.evaluate("zadvance(0)")
    a=snap(page)
    assert a["phase"]=="roundEnd" and not a["running"],a
    page.evaluate("next()")
    b=snap(page)
    assert (b["pos"],b["phase"],b["running"])==(2,"round",True),b
    page.evaluate("pause();q4a(3,false);zadvance(0);next()")
    c=snap(page)
    assert (c["pos"],c["phase"])==(3,"roundEnd"),c

def pause_live_settings(page):
    setup(page,mode="4",between=0,positions=4)
    page.evaluate("start();pause()")
    a=snap(page)
    assert not a["running"] and 118<a["remaining"]<=121,a
    page.evaluate("start();showSettings(false)")
    b=snap(page)
    assert b["screen"]=="settings" and b["running"],b
    page.evaluate("showTimer()")
    c=snap(page)
    assert c["screen"]=="timer" and c["running"] and c["pos"]==1,c
    page.evaluate("pause()")

def short_long_adjustments(page):
    setup(page,secs=3590)
    page.evaluate("zshift(60)")
    a=snap(page)
    assert a["remaining"]==3599 and not a["longStart"],a
    page.evaluate("zshift(-60)")
    assert snap(page)["remaining"]==3539
    setup(page,secs=3600)
    page.evaluate("zshift(60)")
    b=snap(page)
    assert b["remaining"]==3660 and b["longStart"],b

def undo_restart(page):
    setup(page,between=0,positions=4)
    page.evaluate("next()")
    assert snap(page)["pos"]==2
    page.evaluate("q4d()")
    assert snap(page)["pos"]==1
    page.evaluate("q48()")
    a=snap(page)
    assert a["pos"]==1 and a["running"] and 118<a["remaining"]<121,a
    page.evaluate("pause()")

def keyboard(page):
    setup(page,between=10,positions=4)
    page.locator("#timer").click(position={"x":10,"y":220})
    page.keyboard.press("F8")
    assert snap(page)["remaining"]==180
    page.keyboard.press("F7")
    assert snap(page)["remaining"]==120
    page.keyboard.press("ArrowRight")
    assert snap(page)["pos"]==2
    page.keyboard.press("r")
    assert snap(page)["running"]
    page.keyboard.press("Space")
    assert not snap(page)["running"]
    page.keyboard.press("Space")
    assert snap(page)["running"]
    page.evaluate("pause()")

def resume_editor(page):
    setup(page,positions=4)
    page.evaluate("start();pause()")
    page.locator("#resumeBtn").click()
    assert not snap(page)["resumeHidden"]
    page.keyboard.press("Escape")
    assert snap(page)["resumeHidden"] and snap(page)["screen"]=="timer"
    page.evaluate("""()=>{
      openResumeEditor();const input=document.getElementById("resumeInput");
      input.value="14:25";commitResumeTime({preventDefault(){}})
    }""")
    assert page.evaluate("s.resumeTime")=="14:25"

def temporary_message(page):
    setup(page,positions=4)
    page.evaluate('s.quickMessage="Initial";q2c()')
    page.locator("#tempMessageInput").fill("Nouveau")
    assert page.evaluate("s.quickMessage")=="Initial"
    page.evaluate("q20()")
    assert page.evaluate("s.quickMessage")=="Initial"
    page.evaluate("q2c()")
    page.locator("#tempMessageInput").fill("Nouveau")
    page.locator("#tempMessageSubmit").click()
    assert page.evaluate("s.quickMessage")=="Nouveau"

scenarios=[
 ("pairs_break_end",pairs_break_end),
 ("pairs_jump_break",pairs_jump_break),
 ("overshoot_carry",overshoot_carry),
 ("mp4_round_end",mp4_round_end),
 ("pause_live_settings",pause_live_settings),
 ("short_long_adjustments",short_long_adjustments),
 ("undo_restart",undo_restart),
 ("keyboard_shortcuts",keyboard),
 ("resume_editor",resume_editor),
 ("temporary_message",temporary_message),
]
with sync_playwright() as pw:
    if os.name=="nt":
        browser=pw.chromium.launch(channel="msedge",headless=True)
    else:
        path=shutil.which("chromium") or shutil.which("chromium-browser")
        browser=pw.chromium.launch(executable_path=path,headless=True,args=["--no-sandbox"])
    for name,func in scenarios:
        page=browser.new_page(viewport={"width":812,"height":490})
        errors=[]
        page.on("pageerror",lambda e:errors.append(str(e)))
        try:
            page.set_content(html,wait_until="domcontentloaded")
            page.wait_for_timeout(80)
            page.evaluate("window.beep=()=>{}")
            func(page)
            assert not errors,f"{name}: JS runtime errors {errors}"
        except Exception as e:
            raise AssertionError(f"Functional audit {name} failed: {e}") from e
        finally:
            page.close()
    browser.close()
print("Functional end-to-end audit OK: 10 actual timer scenarios in Edge")
