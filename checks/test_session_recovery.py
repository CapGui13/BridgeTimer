"""Recovery from abnormal exits; tests the actual shipped inline JavaScript in Edge.
Uses a mock storage bridge: opening a second page simulates process termination.
No changes to the production HTML occur in these tests.
"""
import json, os, shutil
from pathlib import Path
from playwright.sync_api import sync_playwright

src=(Path(__file__).resolve().parents[1]/"timer.html").read_text(encoding="utf8")
src=src.replace("localStorage","bridgeAuditStorage")
RECOVERY_KEY="bridgeTimerV2.activeSession"

def open_page(browser,local=None,native=None,width=1280,height=720):
    local=local or {}
    native=native or {}
    prelude="""<script>
      const bridgeAuditStorage={
        data:LOCAL,
        getItem(k){return this.data[k]??null},
        setItem(k,v){this.data[k]=String(v)},
        removeItem(k){delete this.data[k]}
      };
      window.__nativeRecovery=NATIVE;
      window.__nativeCalls=[];
      window.nativeStateReadAll=async()=>({...window.__nativeRecovery});
      window.nativeStateWrite=async(k,v)=>{window.__nativeRecovery[k]=v;window.__nativeCalls.push(["write",k]);return true};
      window.nativeStateDelete=async k=>{delete window.__nativeRecovery[k];window.__nativeCalls.push(["delete",k]);return true};
    </script>"""
    prelude=prelude.replace("LOCAL",json.dumps(local)).replace("NATIVE",json.dumps(native))
    html=src.replace("<body>","<body>"+prelude,1)
    page=browser.new_page(viewport={"width":width,"height":height})
    page.set_content(html,wait_until="domcontentloaded")
    page.wait_for_function("typeof recoveryArmed!=='undefined' && recoveryArmed")
    return page

def ready(p):
    return p.evaluate("""() => ({
      active:st.started,running:st.running,phase:st.phase,pos:st.pos,
      mode:s.mode,remaining:st.remaining,
      modal:!document.querySelector('#recoveryOverlay').classList.contains('hidden'),
      native:window.__nativeRecovery[RECOVERY_KEY],
      local:bridgeAuditStorage.getItem(RECOVERY_KEY)
    })""")

with sync_playwright() as pw:
    if os.name=="nt":browser=pw.chromium.launch(channel="msedge",headless=True)
    else:browser=pw.chromium.launch(executable_path=shutil.which("chromium") or shutil.which("chromium-browser"),
                                  args=["--no-sandbox"],headless=True)
    p=open_page(browser)
    assert not ready(p)["modal"], "Normal first launch must not show recovery prompt"
    p.evaluate("""() => {
      Object.assign(s,{mode:"2",positions:6,startPosition:1,between:30,
        hours:0,minutes:45,seconds:0,boards:6,boardMinutes:7,boardSeconds:30,
        clubName:"Club Test",eventName:"Coupe Test"});
      fill();st.started=true;q4a(3,false);st.running=true;
      st.endAt=performance.now()+123456;render();recoveryAutoSave(true);
    }""")
    stored=p.evaluate("bridgeAuditStorage.getItem(RECOVERY_KEY)")
    assert stored and json.loads(stored)["state"]["pos"]==3
    assert json.loads(stored)["settings"]["eventName"]=="Coupe Test"
    p.wait_for_function("window.__nativeRecovery['bridgeTimerV2.activeSession'] !== undefined")
    native=p.evaluate("window.__nativeRecovery")
    assert RECOVERY_KEY in native
    p.close() # Simulated kill without normal cleanup

    restart=open_page(browser,local={RECOVERY_KEY:stored},native=native,width=1650,height=928)
    a=ready(restart)
    assert a["modal"] and not a["active"] and not a["running"],a
    assert restart.locator("#recoveryRound").inner_text()=="Tour 3 sur 6"
    assert restart.locator("#recoveryState").inner_text()=="En marche"
    restart.locator("#recoveryResume").click()
    a=ready(restart)
    assert a["active"] and not a["running"] and a["phase"]=="round" and a["pos"]==3,a
    assert a["mode"]=="2" and abs(a["remaining"]-123.456)<1,a
    assert not a["modal"]
    assert restart.evaluate("document.querySelector('#timer').classList.contains('hidden')")==False
    restart.evaluate("recoveryAutoSave(true)")
    assert json.loads(restart.evaluate("bridgeAuditStorage.getItem(RECOVERY_KEY)"))["state"]["running"]==False
    restart.evaluate("q22()")
    restart.wait_for_function("!window.__nativeRecovery['bridgeTimerV2.activeSession']")
    assert restart.evaluate("bridgeAuditStorage.getItem(RECOVERY_KEY)") is None
    restart.close()

    # Native disk backup alone must recover if WebView2 storage is unavailable.
    only_disk=open_page(browser,native={RECOVERY_KEY:stored})
    assert ready(only_disk)["modal"]
    only_disk.locator("#recoveryNew").click()
    only_disk.wait_for_function("!window.__nativeRecovery['bridgeTimerV2.activeSession']")
    assert not ready(only_disk)["active"] and not ready(only_disk)["modal"]
    only_disk.close()

    # A damaged checkpoint must never be revived. An intact previous local
    # snapshot is used as a fallback.
    corrupt=open_page(browser,local={RECOVERY_KEY:"{damaged",RECOVERY_KEY+".bak":stored})
    assert ready(corrupt)["modal"]
    corrupt.locator("#recoveryNew").click()
    assert not ready(corrupt)["modal"]
    corrupt.close()
    invalid=open_page(browser,local={RECOVERY_KEY:"{damaged"})
    assert not ready(invalid)["modal"]
    invalid.close()

    # An explicit normal Quitter confirmation clears the crash checkpoint,
    # including when it was written by the native Windows bridge.
    p=open_page(browser,local={RECOVERY_KEY:stored})
    p.locator("#recoveryResume").click()
    p.evaluate("window.nativeExit=async()=>true")
    p.evaluate("q34()")
    p.locator("#exitYesBtn").click()
    p.wait_for_function("!window.__nativeRecovery['bridgeTimerV2.activeSession']")
    assert p.evaluate("bridgeAuditStorage.getItem(RECOVERY_KEY)") is None
    p.close()
    browser.close()
print("Recovery test OK: crash, pause, tour/time, native fallback, corruption and explicit shutdown")
