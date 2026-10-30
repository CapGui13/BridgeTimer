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
viewports = [(1600,900),(812,456),(812,500),(960,540),(960,720),(1280,720),(1920,1080)]
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

def check_footer_balance(page, scenario):
    """The side gaps measured FROM the fixed labels must match to <= 1.1 px."""
    d=page.evaluate("""() => {
      const rect=id=>document.querySelector(id).getBoundingClientRect();
      const time=rect('#localTime'),round=rect('#round'),buttons=rect('#timer .controls');
      const scale=Number(document.querySelector('#timer').style.getPropertyValue('--stage-scale'))||1;
      return {left:buttons.left-time.right,right:round.left-buttons.right,
        gap:round.left-time.right,buttonsWidth:buttons.width,
        centerDelta:(buttons.left+buttons.right-time.right-round.left)/2,
        scale};
    }""")
    assert abs(d["left"]-d["right"])<=1.1, f"{scenario}: unbalanced footer gaps: {d}"
    assert d["left"]>3 and d["right"]>3, f"{scenario}: buttons overlap permanent labels: {d}"


FIXED_BUTTON_IDS = ["fresh","stopTimer","defaults","debugBtn"]

def settings_button_slots(page):
    return page.evaluate("""ids => Object.fromEntries(ids.map(id => {
      const b=document.getElementById(id),r=b.getBoundingClientRect(),s=getComputedStyle(b);
      return [id,{x:r.x,y:r.y,w:r.width,h:r.height,display:s.display,visible:s.visibility}];
    }))""", FIXED_BUTTON_IDS)

def assert_stable_settings_slots(a,b,label):
    for id in FIXED_BUTTON_IDS:
        # The main button legitimately changes its label from "Lancer"
        # to "Timer" when a session starts; its center and baseline must
        # stay fixed, but its intrinsic text width is allowed to change.
        if id=="fresh":
            a_center=a[id]["x"]+a[id]["w"]/2
            b_center=b[id]["x"]+b[id]["w"]/2
            assert abs(a_center-b_center)<=1.1, f"{label}: fresh center moved"
            dimensions=("y","h")
        else:
            # Subsequent buttons follow the first label's RIGHT edge;
            # when "Lancer" becomes "Timer", the centered row contracts
            # symmetrically but each internal gap remains unchanged.
            first_a=a["fresh"]["x"]+a["fresh"]["w"]
            first_b=b["fresh"]["x"]+b["fresh"]["w"]
            gap_a=a[id]["x"]-first_a
            gap_b=b[id]["x"]-first_b
            assert abs(gap_a-gap_b)<=1.1, f"{label}: {id} relative position changed"
            dimensions=("y","w","h")
        for dimension in dimensions:
            delta=abs(a[id][dimension]-b[id][dimension])
            assert delta<=1.1, f"{label}: {id}.{dimension} shifted by {delta:.2f}: {a[id]} -> {b[id]}"

def stage_visual_geometry(page):
    """Normalized 1600x900 stage geometry, independent of viewport and fullscreen."""
    selectors=[
      "#timer .top","#timer .bottom","#status","#clock","#club",
      "#localTime","#round","#timer .controls","#minus","#pause",
      "#plus","#next","#resetRound","#settingsBtn","#fsBtn"
    ]
    return page.evaluate("""selectors => {
      const t=document.getElementById("timer"),stage=t.getBoundingClientRect();
      const k=Number(t.style.getPropertyValue("--stage-scale"))||1;
      return Object.fromEntries(selectors.map(q=>{
        const el=document.querySelector(q),r=el.getBoundingClientRect(),c=getComputedStyle(el);
        return [q,{x:(r.x-stage.x)/k,y:(r.y-stage.y)/k,
          w:r.width/k,h:r.height/k,font:parseFloat(c.fontSize),padding:c.padding}];
      }));
    }""",selectors)

def assert_same_stage_geometry(a,b,label,cross_viewport=False):
    # Independent Edge windows show different running clock values and
    # can measure colon glyphs differently. Compare rendered font size
    # and vertical geometry, not intrinsic width of dynamic text.
    # Same-viewport transitions remain strictly checked.
    for sel in a:
        dimensions=("x","y","w","h","font")
        if cross_viewport:
            # A non-16:9 window now grows the central grid instead of leaving
            # blank areas around the header/footer. Different reference-stage
            # widths/center positions are expected, but virtual font sizes
            # and the HEIGHTS of both persistent bands remain unchanged.
            dimensions=("h","font")
            if sel in ("#timer .top","#timer .bottom",
                       "#timer .controls","#minus","#pause","#plus","#next",
                       "#resetRound","#settingsBtn","#fsBtn"):
                # The approved compact windowed UI uses FIXED physical
                # 55/59px bars and 34/40px buttons. Their VIRTUAL sizes
                # necessarily vary with viewport scale. These dimensions
                # are independently checked by test_windowed_timer_band_parity.
                dimensions=()
            elif sel=="#clock":
                # The central clock can grow into extra vertical space.
                dimensions=()
            elif sel=="#status":
                dimensions=("font",)
        for dimension in dimensions:
            delta=abs(a[sel][dimension]-b[sel][dimension])
            assert delta<=1.1, f"{label}: {sel}.{dimension} changed by {delta:.2f}: {a[sel]} -> {b[sel]}"
        # N°11: only the natural-width footer controls have smaller
        # horizontal padding in compact (<=850px) native windows. This
        # intentional exception MUST NOT permit any other visual drift.
        compact_footer=(cross_viewport and label.startswith(("812x","850x"))
            and sel in ("#pause","#next","#resetRound")
            and a[sel]["padding"]=="0px 12px"
            and b[sel]["padding"]=="0px 7px")
        assert compact_footer or a[sel]["padding"]==b[sel]["padding"], f"{label}: {sel} padding changed: {a[sel]} -> {b[sel]}"


def test_timer_bands_fill_window(browser):
    """Native user screenshot: no giant blank strips above/below the timer."""
    page=browser.new_page(viewport={"width":812,"height":580})
    page.set_content(html,wait_until="domcontentloaded")
    for mode in ("4","2"):
        page.evaluate("""mode => {
          s.mode=mode;st.started=true;st.phase='round';st.running=false;
          st.remaining=3599;st.roundDuration=3600;
          showTimer();render();
        }""",mode)
        for width,height in ((812,580),(812,700),(960,540),(1210,646),(1280,720),(1600,900)):
            page.set_viewport_size({"width":width,"height":height})
            page.evaluate("updateStage();render()")
            r=page.evaluate("""() => {
              const q=sel=>{const x=document.querySelector(sel).getBoundingClientRect();
                return {x:x.left,y:x.top,right:x.right,bottom:x.bottom,w:x.width,h:x.height}};
              return {stage:q('#timer'),top:q('#timer .top'),bottom:q('#timer .bottom'),
                w:innerWidth,h:innerHeight,scale:parseFloat(document.querySelector('#timer').style.getPropertyValue('--stage-scale'))};
            }""")
            assert abs(r["stage"]["x"])<=1.1 and abs(r["stage"]["y"])<=1.1, f"Timer canvas detached: {mode} {r}"
            assert abs(r["stage"]["right"]-width)<=1.1 and abs(r["stage"]["bottom"]-height)<=1.1, f"Timer canvas letterboxed: {mode} {r}"
            assert abs(r["top"]["y"])<=1.1 and abs(r["top"]["right"]-width)<=1.1, f"Timer header detached: {mode} {r}"
            assert abs(r["bottom"]["bottom"]-height)<=1.1 and abs(r["bottom"]["right"]-width)<=1.1, f"Timer footer detached: {mode} {r}"
            assert r["top"]["h"]>15 and r["bottom"]["h"]>15, f"Persistent bars collapsed: {mode} {r}"
    page.close()

def test_exit_and_live_settings(browser):
    # Real browser execution; exercise the same event paths as users.
    page=browser.new_page(viewport={"width":960,"height":540})
    page.set_content(html,wait_until="domcontentloaded")
    page.evaluate("""() => {
      window.__exitCalls=0;
      window.nativeExit=async()=>{window.__exitCalls++;return true};
      window.nativeStateWrite=async()=>true;
    }""")
    assert page.evaluate("document.getElementById('exitConfirmOverlay').classList.contains('hidden')")
    # Clicking Quitter opens a modal but NEVER exits directly.
    page.locator("#quitAppBtn").click()
    assert page.evaluate("q1d() && window.__exitCalls===0"), "Quitter bypassed confirmation"
    page.keyboard.press("Escape")
    assert page.evaluate("!q1d() && window.__exitCalls===0"), "Escape didn't cancel exit dialog"
    # A direct call to the private confirmation action cannot exit unless
    # the user has actually opened the confirmation dialog.
    page.evaluate("q46()")
    assert page.evaluate("window.__exitCalls===0"), "Direct exit call bypassed dialog gate"
    # A Windows X/Alt+F4 request is consumed by the existing Win32 queue.
    page.evaluate("""() => {
      window.__nativeClosePending=true;
      window.nativeConsumeCloseRequest=async()=>{
        const p=window.__nativeClosePending;window.__nativeClosePending=false;return p;
      };
    }""")
    page.wait_for_function("q1d()",timeout=2000)
    assert page.evaluate("window.__exitCalls===0"), "Native X request exited without confirmation"
    page.locator("#exitNoBtn").click()
    assert page.evaluate("!q1d() && window.__exitCalls===0"), "Cancel on native close exited"
    # Confirming 'Oui' is the ONLY permitted successful close.
    page.locator("#quitAppBtn").click()
    page.locator("#exitYesBtn").click()
    page.wait_for_function("window.__exitCalls===1",timeout=2000)
    page.close()

    # Duration changes must be identical on all live Settings return paths.
    for action in ("top-button","footer-button","F9","Escape","miniature"):
        page=browser.new_page(viewport={"width":960,"height":540})
        page.set_content(html,wait_until="domcontentloaded")
        page.evaluate("""() => {
          s.mode="2";s.between=0;fill();
          st.started=true;st.running=true;st.phase="round";
          st.remaining=123.5;st.roundDuration=3600;st.breakDuration=30;
          st.roundBetween=0;st.endAt=performance.now()+123500;
          showSettings();
          document.getElementById("between").value="18";
          window.__before={
            remaining:st.remaining,endAt:st.endAt,running:st.running,
            duration:st.roundDuration,breakDuration:st.breakDuration,phase:st.phase
          };
        }""")
        if action=="top-button":
            page.locator("#drawerClose").click()
        elif action=="footer-button":
            page.locator("#fresh").click()
        elif action=="F9":
            page.keyboard.press("F9")
        elif action=="Escape":
            page.keyboard.press("Escape")
        else:
            page.evaluate("document.getElementById('miniTimer').ondblclick()")
        status=page.evaluate("""() => ({
          hidden:document.getElementById('settings').classList.contains('hidden'),
          between:s.between,roundBetween:st.roundBetween,
          remaining:st.remaining,endAt:st.endAt,running:st.running,
          duration:st.roundDuration,breakDuration:st.breakDuration,phase:st.phase,
          before:window.__before
        })""")
        assert status["hidden"] and status["between"]==18 and status["roundBetween"]==18, f"{action}: interval not applied: {status}"
        for field in ("remaining","endAt","running","duration","breakDuration","phase"):
            assert status[field]==status["before"][field], f"{action}: ongoing round unexpectedly changed {field}: {status}"
        page.close()
    # Existing initialization still computes eight boards x duration/board.
    page=browser.new_page(viewport={"width":960,"height":540})
    page.set_content(html,wait_until="domcontentloaded")
    defaults=page.evaluate("""() => ({
      hours:s.hours,minutes:s.minutes,seconds:s.seconds,boards:s.boards,
      perBoard:s.boardMinutes*60+s.boardSeconds
    })""")
    assert defaults["boards"]==8 and defaults["hours"]*3600+defaults["minutes"]*60+defaults["seconds"]==8*defaults["perBoard"], f"Default start duration changed: {defaults}"
    page.close()


def test_settings_window_resize(browser):
    """Reproduce user bug: native window resized in ONE axis or BOTH."""
    page=browser.new_page(viewport={"width":812,"height":456})
    page.set_content(html,wait_until="domcontentloaded")
    changes=[
      (812,456), # initial 16:9
      (812,646), # screenshot: vertical ONLY, header previously floated
      (1040,646), # wider and taller
      (1210,646), # horizontal ONLY, letterboxed timer
      (1210,840), # vertical ONLY again
      (960,540), # reduce both
      (960,720), # separate axis
      (812,456), # full round trip
    ]
    for width,height in changes:
        page.set_viewport_size({"width":width,"height":height})
        page.wait_for_function("""() => {
          const s=Number(document.documentElement.style.getPropertyValue('--settings-window-scale'));
          return Math.abs(s*1600-innerWidth)<.01;
        }""")
        metrics=page.evaluate("""() => {
          const rect=q=>{const b=document.querySelector(q).getBoundingClientRect();
            return {x:b.x,y:b.y,right:b.right,bottom:b.bottom,w:b.width,h:b.height}};
          const pad=parseFloat(getComputedStyle(document.querySelector('#settings .wrap')).paddingTop);
          return {head:rect('#settings .wrap>.head'),footer:rect('#settings .actions'),
            heading:rect('#settings .wrap>.head h1'),
            form:rect('#settings .tournamentCard'),
            pad,scale:Number(document.documentElement.style.getPropertyValue('--settings-window-scale')),
            vw:innerWidth,vh:innerHeight};
        }""")
        head,footer=metrics["head"],metrics["footer"]
        for metric in ("x","y"):
            assert abs(head[metric])<1.1, f"{width}x{height}: title band detached: {metrics}"
        assert abs(head["right"]-width)<1.1, f"{width}x{height}: header must fill native width: {metrics}"
        assert abs(footer["x"])<1.1 and abs(footer["right"]-width)<1.1, f"{width}x{height}: footer detached horizontally: {metrics}"
        assert abs(footer["bottom"]-height)<1.1, f"{width}x{height}: footer detached vertically: {metrics}"
        # The approved Settings layout keeps 4px of breathing space below its
        # 55px fixed header (59px reserved at compact sizes). A strict 0px
        # difference incorrectly rejects this intentional safe spacing.
        assert -1.1 <= metrics["pad"]-head["h"] <= 5.1, f"{width}x{height}: heading overlaps or has excessive gap: {metrics}"
        # Ensure neither bar moves when scrolling settings between resizes.
        page.evaluate("window.scrollTo(0,450)")
        scrolled=page.evaluate("""() => {
          const r=q=>{const p=document.querySelector(q).getBoundingClientRect();
            return [p.x,p.y,p.right,p.bottom]};
          return {head:r('#settings .wrap>.head'),footer:r('#settings .actions')};
        }""")
        for name in ("head","footer"):
            original=[metrics[name][x] for x in ("x","y","right","bottom")]
            assert all(abs(a-b)<1.1 for a,b in zip(original,scrolled[name])), f"{width}x{height}: {name} moved during scroll"
        page.evaluate("window.scrollTo(0,0)")
    # A resize while LIVE must preserve timer state upon return.
    page.evaluate("""() => {
      st.started=true;st.running=true;st.phase='round';st.remaining=151.4;
      st.endAt=performance.now()+151400;s.mode='2';s.between=12;
      showSettings();window.__snapshot={remaining:st.remaining,endAt:st.endAt,phase:st.phase};
    }""")
    page.set_viewport_size({"width":1090,"height":650})
    page.wait_for_function("""() => Math.abs(Number(document.documentElement.style.getPropertyValue('--settings-window-scale'))*1600-innerWidth)<.01""")
    page.evaluate("showTimer()")
    unchanged=page.evaluate("""() => window.__snapshot.remaining===st.remaining &&
      window.__snapshot.endAt===st.endAt && window.__snapshot.phase===st.phase""")
    assert unchanged,"Resizing and returning from Settings unexpectedly modified timer"
    page.close()

def main():
    errors=[]
    # Prior tests toggled .fs without changing browser viewport. That never
    # exposed window-width media queries. Reference the REAL 1600x900
    # window and compare against independently loaded smaller viewports.
    reference_by_mode={}
    with sync_playwright() as pw:
        if os.name=="nt":
            browser=pw.chromium.launch(channel="msedge",headless=True)
        else:
            path=shutil.which("chromium") or shutil.which("chromium-browser")
            browser=pw.chromium.launch(executable_path=path,headless=True,args=["--no-sandbox"])
        test_exit_and_live_settings(browser)
        test_timer_bands_fill_window(browser)
        test_settings_window_resize(browser)
        for width,height in viewports:
            page=browser.new_page(viewport={"width":width,"height":height})
            page.on("pageerror",lambda err: errors.append(str(err)))
            page.set_content(html,wait_until="domcontentloaded")
            assert page.evaluate("typeof render")=="function", "Timer failed to initialize"
            # Fixed footer is opaque even when tournament controls scroll
            # underneath in the 16:9 settings-window geometry.
            def solid_settings_footer():
                return page.evaluate("""() => {
                  const el=document.querySelector("#settings .actions");
                  const b=getComputedStyle(el).backgroundColor;
                  const match=b.match(/^rgba?\\(([^)]+)\\)$/);
                  if(!match)return false;
                  const parts=match[1].split(",").map(v=>v.trim());
                  return parts.length===3||(parts.length===4&&Number(parts[3])===1);
                }""")
            assert solid_settings_footer(), "Windowed Settings footer must be fully opaque"
            initial_slots=settings_button_slots(page)
            assert page.evaluate("getComputedStyle(document.getElementById('spb')).display==='none'"), "Écrans tests must be hidden when Debug is off"
            for id in FIXED_BUTTON_IDS:
                assert initial_slots[id]["display"]!="none" and initial_slots[id]["w"]>5, f"Slot absent at startup: {id}={initial_slots[id]}"
            assert initial_slots["stopTimer"]["visible"]=="hidden", "Arrêter must be invisible but RESERVE its slot at startup"
            # Nothing exists to return to until the first session is launched.
            assert page.evaluate("""() => {
              const b=document.getElementById("drawerClose"),s=getComputedStyle(b);
              return !document.body.classList.contains("settingsLive") &&
                s.visibility==="hidden"&&s.pointerEvents==="none";
            }"""), "Startup shows an inactive Retour button"
            firstFooter=page.evaluate("""() => {
              const r=document.querySelector("#settings .actions").getBoundingClientRect();
              return {h:r.height,expected:59,actual:r.bottom,
                x:r.x,right:r.right,viewport:innerHeight,width:innerWidth};
            }""")
            assert abs(firstFooter["h"]-firstFooter["expected"])<=1.1, f"Windowed Settings footer must remain 59px at every viewport: {firstFooter}"
            assert abs(firstFooter["actual"]-firstFooter["viewport"])<=1.1, "Settings footer detaches from bottom on non-16:9 window"
            assert abs(firstFooter["x"])<=1.1 and abs(firstFooter["right"]-firstFooter["width"])<=1.1, "Settings footer must fill full window width"
            # In the real 16:9 settings viewport, fields must scroll BEHIND
            # an opaque, fixed action bar without moving the bar itself.
            initial=page.evaluate("""() => {
              const r=document.querySelector("#settings .actions").getBoundingClientRect();
              return [r.x,r.y,r.width,r.height,document.documentElement.scrollHeight];
            }""")
            page.evaluate("window.scrollTo(0,700)")
            afterScroll=page.evaluate("""() => {
              const r=document.querySelector("#settings .actions").getBoundingClientRect();
              const children=[...document.querySelector(".settingsActionButtons").children];
              return {
                frame:[r.x,r.y,r.width,r.height],
                order:children.map(x=>x.id)
              };
            }""")
            assert all(abs(initial[i]-afterScroll["frame"][i])<0.1 for i in range(4)), "Windowed footer moved when settings scrolled"
            assert initial[4]>height, "Settings became non-scrollable in the shorter 16:9 viewport"
            assert afterScroll["order"].index("fresh")<afterScroll["order"].index("stopTimer"), "Timer button must be before Arrêter"
            assert solid_settings_footer(), "Scrolling introduced transparent footer"
            page.evaluate("window.scrollTo(0,0)")

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
                check_footer_balance(page, f"{width}x{height}, {mode}, initial")
                before_mode=stage_visual_geometry(page)
                if (width,height)==(1600,900):
                    reference_by_mode[mode]=before_mode
                else:
                    assert mode in reference_by_mode, f"Reference stage missing for {mode}"
                    assert_same_stage_geometry(
                        reference_by_mode[mode],before_mode,
                        f"{width}x{height} windowed vs actual 1600x900 reference {mode}",
                        cross_viewport=True
                    )
                page.evaluate("q25(true)")
                in_fullscreen=stage_visual_geometry(page)
                # The approved windowed UI uses fixed 55/59px bands; native
                # fullscreen uses its distinct 80/88px reference bands.
                # Cross-mode identity of these rectangles is NOT expected.
                # Instead check real fullscreen dimensions independently,
                # then strictly verify restoration of the windowed geometry.
                assert abs(in_fullscreen["#timer .top"]["h"]-80)<=1.1, "Fullscreen header is not 80 reference px"
                assert abs(in_fullscreen["#timer .bottom"]["h"]-88)<=1.1, "Fullscreen footer is not 88 reference px"
                assert in_fullscreen["#clock"]["w"]>0, "Fullscreen clock vanished"
                page.evaluate("q25(false)")
                after_fullscreen=stage_visual_geometry(page)
                assert_same_stage_geometry(before_mode,after_fullscreen,
                    f"{width}x{height}, {mode}, virtual 1600x900 round-trip")
                # Test a 2-digit round number: the changing round label width
                # must automatically recenter buttons within the FREE span.
                page.evaluate("""() => {st.pos=12;s.positions=18;render()}""")
                check_footer_balance(page, f"{width}x{height}, {mode}, 12/18")
                page.evaluate("""() => {st.pos=2;s.positions=6;render()}""")
                check_footer_balance(page, f"{width}x{height}, {mode}, 2/6")
                before=measure(page)
                # Windowed settings header must have the SAME computed height
                # as the existing timer band, without changing timer geometry.
                timerHeader=page.evaluate("""() => {
                  const e=document.querySelector("#timer .top"),r=e.getBoundingClientRect();
                  const box=sel=>{const p=document.querySelector(sel).getBoundingClientRect();
                    return {x:p.x,y:p.y,w:p.width,h:p.height};};
                  return {height:r.height,title:e.querySelector("#club").getBoundingClientRect().height,
                    band:box("#timer .top"),settings:box("#settingsBtn"),exit:box("#fsBtn")};
                }""")
                page.evaluate("showSettings()")
                live_slots=settings_button_slots(page)
                assert_stable_settings_slots(initial_slots,live_slots,
                    f"{width}x{height} {mode} Lancer -> Timer, Arrêter appears")
                assert live_slots["stopTimer"]["visible"]=="visible", "Arrêter should be visible in a live session"
                settingsHeader=page.evaluate("""() => {
                  const e=document.querySelector("#settings .wrap>.head");
                  const r=e.getBoundingClientRect(),c=getComputedStyle(e);
                  const h=e.querySelector("h1").getBoundingClientRect();
                  const box=sel=>{const p=document.querySelector(sel).getBoundingClientRect();
                    return {x:p.x,y:p.y,w:p.width,h:p.height};};
                  return {height:r.height,title:h.height,
                    parentPaddingTop:parseFloat(getComputedStyle(document.querySelector("#settings .wrap")).paddingTop),
                    band:box("#settings .wrap>.head"),settings:box("#drawerClose"),exit:box("#settingsFullscreenBtn"),
                    exitVisible:getComputedStyle(document.getElementById("settingsFullscreenBtn")).display!=="none",
                    exitLabel:document.getElementById("settingsFullscreenBtn").textContent,
                    isWired:document.getElementById("settingsFullscreenBtn").onclick===fs,
                    closeLabel:document.getElementById("drawerClose").textContent,
                    returnVisibility:getComputedStyle(document.getElementById("drawerClose")).visibility,
                    footer:box("#settings .actions"),footerButton:box("#fresh")};
                }""")
                # Timer uses min(width/1600,height/900) and may be
                # letterboxed by a few pixels even near 16:9. Settings uses
                # width/1600 and must fit the ENTIRE native window width.
                stage_scale=min(width/1600,height/900)
                settings_scale=width/1600
                ratio=settings_scale/stage_scale
                assert abs(timerHeader["height"]*ratio-settingsHeader["height"])<=1.1, f"Windowed Settings header height drift: {width}x{height} {mode}"
                # The club name is deliberately smaller than the
                # "Bridge Timer" Settings title to accommodate long clubs;
                # their band heights match but their text heights need not.
                assert timerHeader["title"]<=timerHeader["height"]+1.1, "Club title overflows timer band"
                assert settingsHeader["title"]<=settingsHeader["height"]+1.1, "Bridge Timer heading overflows Settings band"
                # Preserve the approved 4px reserve below the 55px header.
                gapBelowTitle=settingsHeader["parentPaddingTop"]-settingsHeader["height"]
                assert -1.1<=gapBelowTitle<=5.1, "Settings title content overlap or excessive gap"
                assert abs(settingsHeader["band"]["y"])<=1.1 and abs(settingsHeader["band"]["x"])<=1.1, "Settings header must touch native top-left"
                assert abs(settingsHeader["band"]["w"]-width)<=1.1, "Settings header must fill native width"
                # Settings has its OWN right-side button group (including
                # Retour au timer), so its x coordinates intentionally differ
                # from Timer's. Protect alignment and non-overlap instead.
                assert settingsHeader["settings"]["x"]+settingsHeader["settings"]["w"] < settingsHeader["exit"]["x"], "Settings header buttons overlap"
                assert settingsHeader["exit"]["x"]+settingsHeader["exit"]["w"] <= width-4, "Fullscreen button clipped in Settings"
                for key in ("settings","exit"):
                    assert settingsHeader[key]["h"]>=30, f"Settings {key} button too short"
                    assert settingsHeader[key]["y"]>=-1 and settingsHeader[key]["y"]+settingsHeader[key]["h"]<=settingsHeader["height"]+1.1, f"Settings {key} button vertically clipped"
                assert settingsHeader["exitVisible"] and settingsHeader["exitLabel"]=="Plein écran" and settingsHeader["isWired"], "Missing working fullscreen button in windowed Settings"
                assert settingsHeader["closeLabel"]=="Retour au timer" and settingsHeader["returnVisibility"]=="visible", "Live windowed return button must be visible"

                # "Arrêter" must fit WITHOUT clipping; its gap before Reset
                # must exceed the ordinary gap without moving Quitter.
                def verify_stop_button():
                    buttons=page.evaluate("""() => {
                      const r=id=>{const b=document.getElementById(id),p=b.getBoundingClientRect();
                        return {x:p.x,right:p.right,w:p.width,y:p.y,h:p.height};};
                      const b=document.getElementById("stopTimer"),txt=document.createRange();
                      txt.selectNodeContents(b);
                      const textRect=txt.getBoundingClientRect();
                      return {
                        fresh:r("fresh"),stop:r("stopTimer"),reset:r("defaults"),
                        quit:r("quitAppBtn"),text:{x:textRect.x,right:textRect.right},
                        visible:getComputedStyle(b).visibility,
                        label:b.textContent.trim()
                      };
                    }""")
                    assert buttons["visible"]=="visible", "Stop button hidden while timer running"
                    assert buttons["label"]=="Arrêter", "Stop button label changed"
                    assert buttons["text"]["x"]-buttons["stop"]["x"]>=5, f"Stop label touches left edge: {buttons}"
                    assert buttons["stop"]["right"]-buttons["text"]["right"]>=5, f"Arrêter clipped on right edge: {buttons}"
                    normalGap=buttons["stop"]["x"]-buttons["fresh"]["right"]
                    largerGap=buttons["reset"]["x"]-buttons["stop"]["right"]
                    assert largerGap>=normalGap+3, f"Missing extra gap after Arrêter: {buttons}"
                    assert buttons["reset"]["right"]<buttons["quit"]["x"], f"Central group overlaps Quitter: {buttons}"
                verify_stop_button()

                timerFooter=page.evaluate("""() => {
                  const b=sel=>{const r=document.querySelector(sel).getBoundingClientRect();
                    return {x:r.x,y:r.y,w:r.width,h:r.height};};
                  // Current approved WINDOWED footer dimensions are
                  // 59px high with 40px buttons in BOTH screens. The old
                  // 88px virtual size belongs exclusively to fullscreen.
                  return {height:59,buttonHeight:40};
                }""")
                assert abs(settingsHeader["footer"]["h"]-timerFooter["height"])<=1.1, f"Windowed live Settings footer must be same height as timer: {width}x{height} {mode}"
                assert abs(settingsHeader["footerButton"]["h"]-timerFooter["buttonHeight"])<=1.1, "Windowed settings buttons must match timer button height"
                assert abs(settingsHeader["footer"]["y"]+settingsHeader["footer"]["h"]-height)<=1.1, "Settings footer must be pinned to bottom of RESIZED viewport"
                assert abs(settingsHeader["footer"]["x"])<=1.1 and abs(settingsHeader["footer"]["w"]-width)<=1.1, "Settings footer must fill width without centering offsets"
                page.evaluate("showTimer()")
                page.evaluate("showSettings()")
                assert_stable_settings_slots(initial_slots,settings_button_slots(page),
                    f"{width}x{height} {mode} settings return")
                page.evaluate("showTimer()")
                afterWindowedSettings=measure(page)
                equal(before,afterWindowedSettings,f"{width}x{height}, {mode}, return from slim Settings title",exclusions=("#round","#timer .controls"))
                check_footer_balance(page, f"{width}x{height}, {mode}, return from Settings")
                # In PAIRS, settings may legitimately re-evaluate the number of rounds.
                # Check that its right anchor stays fixed, then use the NEW
                # text width as baseline for all later phase comparisons.
                oldRound,newRound=before["#round"],afterWindowedSettings["#round"]
                assert abs((oldRound[0]+oldRound[2])-(newRound[0]+newRound[2]))<.1, "Round label anchor changed after settings"
                assert oldRound[1]==newRound[1] and oldRound[3:]==newRound[3:], "Round footer typography changed after settings"
                before=afterWindowedSettings
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
                    equal(before,measure(page),f"{width}x{height}, {mode}, {p}",exclusions=("#timer .controls",))
                    check_footer_balance(page, f"{width}x{height}, {mode}, phase {p}")
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
                equal(before,measure(page),f"{width}x{height}, {mode}, fullscreen toggle",exclusions=("#timer .controls",))
                check_footer_balance(page, f"{width}x{height}, {mode}, fullscreen toggle")

                # Fullscreen settings must share the EXACT 1600x900
                # timer header geometry, despite using distinct content.
                page.evaluate("q25(true)")
                check_footer_balance(page, f"{width}x{height}, {mode}, real fullscreen")
                rects=page.evaluate("""() => {
                  const b=sel=>{const r=document.querySelector(sel).getBoundingClientRect();
                    return {x:r.x,y:r.y,w:r.width,h:r.height};};
                  return {
                    band:b("#timer .top"),title:b("#club"),
                    settings:b("#settingsBtn"),exit:b("#fsBtn"),
                    footer:b("#timer .bottom"),footerButton:b("#pause"),
                    footerFont:getComputedStyle(document.getElementById("pause")).fontSize
                  }
                }""")
                page.evaluate("showSettings()")
                assert solid_settings_footer(), "Fullscreen Settings footer must be fully opaque"
                rects2=page.evaluate("""() => {
                  const b=sel=>{const r=document.querySelector(sel).getBoundingClientRect();
                    return {x:r.x,y:r.y,w:r.width,h:r.height};};
                  return {
                    band:b("#settings .wrap>.head"),title:b("#settings .head h1"),
                    settings:b("#drawerClose"),exit:b("#settingsFullscreenBtn"),
                    footer:b("#settings .actions"),footerButton:b("#fresh"),
                    footerFont:getComputedStyle(document.getElementById("fresh")).fontSize,
                    footerQuit:b("#quitAppBtn"),
                    mini:b("#miniTimer"),settingsCard:b("#settings .tournamentCard"),viewport:{h:innerHeight},
                    miniInBody:document.getElementById("miniTimer").parentElement===document.body,
                    exitWired:document.getElementById("settingsFullscreenBtn").onclick===fs,
                    closeText:document.getElementById("drawerClose").textContent,
                    visible:getComputedStyle(document.getElementById("settingsFullscreenBtn")).display!=="none"
                  }
                }""")
                for key in ["band","settings","exit","footer"]:
                    for metric in ["x","y","w","h"]:
                        diff=abs(rects[key][metric]-rects2[key][metric])
                        assert diff<=2.5, f"Fullscreen header misaligned: {width}x{height} {mode} {key}.{metric} diff {diff:.2f}"
                assert abs(rects["footerButton"]["h"]-rects2["footerButton"]["h"])<=1.1, "Fullscreen settings footer buttons differ from timer buttons"
                assert rects["footerFont"]==rects2["footerFont"], "Settings footer buttons use another font size"
                assert abs(rects2["footerQuit"]["h"]-rects["footerButton"]["h"])<=1.1, "Quit button size differs from timer buttons"
                verify_stop_button()
                assert abs(rects["title"]["h"]-rects2["title"]["h"])<=1.1, "Settings heading font doesn't match club font"
                assert rects2["closeText"]=="Timer" and rects2["visible"] and rects2["exitWired"], "Settings fullscreen header buttons misconfigured"
                assert rects2["miniInBody"], "Miniature still inside the footer"
                assert abs(rects2["mini"]["x"])<0.1, "Miniature must remain anchored to the left"
                assert abs(rects2["mini"]["y"]+rects2["mini"]["h"]-rects2["viewport"]["h"])<1.5, "Fullscreen miniature must touch the BOTTOM of the screen"
                assert abs(rects2["mini"]["x"]+rects2["mini"]["w"]-rects2["settingsCard"]["x"])<1.5, "Fullscreen miniature must reach LEFT border of Tournament/settings cards"
                page.evaluate("showTimer()")
                check_footer_balance(page, f"{width}x{height}, {mode}, return from fullscreen Settings")
                actual=page.evaluate("""() => {
                  const b=sel=>{const r=document.querySelector(sel).getBoundingClientRect();
                    return {x:r.x,y:r.y,w:r.width,h:r.height};};
                  return {band:b("#timer .top"),settings:b("#settingsBtn"),exit:b("#fsBtn")}
                }""")
                for key in ["band","settings","exit"]:
                    for metric in ["x","y","w","h"]:
                        assert abs(rects[key][metric]-actual[key][metric])<=1.1, f"Timer header moved on settings return: {key}.{metric}"
                page.evaluate("q25(false)")
                page.evaluate("showSettings()")
                page.evaluate("showTimer()")
                calls=page.evaluate("window.__viewCalls.slice(-2)")
                assert [c["mode"] for c in calls]==["settings","timer"], f"Incorrect native mode changes: {calls}"
                assert calls[0]["serial"]<calls[1]["serial"], "Native mode requests not ordered"
                check_footer_balance(page, f"{width}x{height}, {mode}, final settings return")
                afterSettings=measure(page)
                # The PAIRS format may recalculate the number of tours on
                # re-entering settings. The footer label's TEXT width can
                # then change, but its right edge and baseline must not move.
                equal(before,afterSettings,f"{width}x{height}, {mode}, settings return",exclusions=("#round","#timer .controls"))

                # Start this independent scenario from a clean active round:
                # earlier phase tests intentionally set 10 seconds and ended.
                page.evaluate("st.phase='round';st.remaining=128;st.roundDuration=3600;st.breakDuration=0")
                # Live settings: lock both duration groups, but never the
                # board-number display checkbox. PAIRS keep between-rounds
                # editable. Debug unlocks both groups. Saving changes must
                # not relaunch the current countdown or active break.
                page.evaluate("showSettings()")
                liveFields=page.evaluate("""() => {
                  const byId=id=>document.getElementById(id).disabled;
                  return {
                    allTimes:["hours","minutes","seconds","boardMinutes","boardSeconds"].map(byId),
                    between:byId("between"),boardNotice:byId("boardProgressNotice"),
                    greyed:[...document.querySelectorAll(".timeEntry.liveTimingLocked")].length
                  };
                }""")
                assert all(liveFields["allTimes"]) and liveFields["greyed"]==2, "Both duration settings must lock during a live session"
                assert not liveFields["boardNotice"], "Board-number checkbox must remain clickable while running"
                assert liveFields["between"]==(mode=="4"), "Inter-round duration lock differs from mode"
                if mode=="2":
                    page.evaluate("""() => {document.getElementById("between").value="45";apply()}""")
                    assert page.evaluate("s.between===45 && st.roundBetween===45 && st.remaining===128"), "Normal PAIRS interval edit unexpectedly restarted the round"
                    page.evaluate("showSettings()")
                page.evaluate("""() => {document.body.classList.add("debugMode");_adu();qc(true)}""")
                debugFields=page.evaluate("""() => ["hours","minutes","seconds","boardMinutes","boardSeconds","between","boardProgressNotice"].every(id=>!document.getElementById(id).disabled)""")
                assert debugFields, "Debug must unlock all duration fields and checkbox"
                page.evaluate("""() => {
                  document.getElementById("hours").value="00";
                  document.getElementById("minutes").value="13";
                  document.getElementById("seconds").value="00";
                  document.getElementById("boardMinutes").value="05";
                  read();
                  apply();
                }""")
                afterDebug=page.evaluate("""() => ({
                  remaining:st.remaining, duration:st.roundDuration,
                  configured:s.minutes, configuredBoard:s.boardMinutes,
                  endAt:st.endAt, phase:st.phase
                })""")
                assert afterDebug["remaining"]==128 and afterDebug["duration"]==3600 and afterDebug["configured"]==13 and afterDebug["configuredBoard"]==5, f"Debug caused hidden restart: {afterDebug}"
                page.evaluate("""() => {document.body.classList.remove("debugMode");showSettings()}""")
                liveRestored=page.evaluate("document.getElementById('minutes').disabled&&document.getElementById('boardMinutes').disabled")
                assert liveRestored, "Disabling Debug must restore the live duration locks"
                page.evaluate("showTimer()")

                oldRound,newRound=before["#round"],afterSettings["#round"]
                assert abs((oldRound[0]+oldRound[2])-(newRound[0]+newRound[2]))<0.1, "Round label right anchor moved"
                assert oldRound[1]==newRound[1] and oldRound[3:]==newRound[3:], "Round label baseline or typography moved"
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
                page.evaluate("document.body.classList.add('debugMode');_osp()")
                page.evaluate("_ssp('jump')")
                page.evaluate("_ssp('between')")
                page.evaluate("_csp();document.body.classList.remove('debugMode')")
                page.evaluate("showTimer()")
                restored=page.evaluate("!document.getElementById('timer').classList.contains('spm') && !document.getElementById('timer').classList.contains('spa')")
                assert restored,"Preview classes leaked to timer"
                # Auto movement may legitimately change round count and text width.
                equal(before,measure(page),"Screen previews return",exclusions=("#round",))
            page.close()
        browser.close()
    assert not errors, f"JavaScript runtime errors: {errors}"
    print("Browser visual regression OK: 7 viewport sizes, both modes, 9 phases, fullscreen and preview returns")

if __name__=="__main__":
    main()
