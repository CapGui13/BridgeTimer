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

    # Reprise a / OU n M are for one launch only: stale settings loaded
    # from a prior local or native Windows store must never pre-fill them.
    settings_key="bridgeTimerV2.settings"
    stale_settings=json.dumps({"resumeTime":"16:20","resumeDelayMinutes":15,
                               "clubName":"Club conserve","sound":True})
    for storage_source in ("local","native"):
        local_settings={settings_key:stale_settings} if storage_source=="local" else {}
        native_settings={settings_key:stale_settings} if storage_source=="native" else {}
        reopened=open_page(browser,local=local_settings,native=native_settings)
        out=reopened.evaluate("""()=>({
          hour:document.querySelector("#resumeTime").value,
          minutes:document.querySelector("#resumeDelayMinutes").value,
          stateHour:s.resumeTime,stateMinutes:s.resumeDelayMinutes,
          club:s.clubName,mode:s.mode,
          overlay:document.querySelector("#finishResume").textContent
        })""")
        assert out["hour"]=="" and out["minutes"]=="",(storage_source,"visible restart fields",out)
        assert out["stateHour"]=="" and out["stateMinutes"]==0,(storage_source,"internal fields",out)
        assert out["club"]=="Club conserve",(storage_source,"unrelated preference lost",out)
        reopened.close()

    # A new checkpoint must not record per-launch restart values, even
    # though the active running session may still have a relative delay.
    source=open_page(browser)
    checkpoint=source.evaluate("""()=>{
       s.mode="4";s.positions=6;s.resumeTime="";s.resumeDelayMinutes=15;
       fill();st.started=true;q4a(2,false);st.running=false;st.remaining=1900;
       const checkpoint=recoverySnapshot();
       return {checkpoint,activeDelay:s.resumeDelayMinutes};
    }""")
    assert checkpoint["activeDelay"]==15,"Recording checkpoint must not change current session"
    assert checkpoint["checkpoint"]["settings"]["resumeTime"]==""
    assert checkpoint["checkpoint"]["settings"]["resumeDelayMinutes"]==0
    source.close()

    # Old Bridge Timer builds saved the delay inside crash checkpoints.
    # Reopening and choosing "Reprendre la séance" must NEVER resurrect
    # those stale values, whether the old checkpoint stored HH:MM,
    # minutes, or both.
    for old_hour,old_delay in (("17:45",0),("",15),("17:45",15)):
        legacy=checkpoint["checkpoint"]
        legacy=json.loads(json.dumps(legacy))
        legacy["settings"]["resumeTime"]=old_hour
        legacy["settings"]["resumeDelayMinutes"]=old_delay
        legacy["settings"]["clubName"]="Tournoi en cours"
        resumed=open_page(browser,local={RECOVERY_KEY:json.dumps(legacy)})
        assert ready(resumed)["modal"],"Legacy interrupted match recovery prompt missing"
        resumed.locator("#recoveryResume").click()
        out=resumed.evaluate("""()=>({
          hour:document.querySelector("#resumeTime").value,
          minutes:document.querySelector("#resumeDelayMinutes").value,
          stateHour:s.resumeTime,stateMinutes:s.resumeDelayMinutes,
          club:s.clubName,round:st.pos,phase:st.phase,started:st.started
        })""")
        assert out["hour"]=="" and out["minutes"]=="",(old_hour,old_delay,"visible fields",out)
        assert out["stateHour"]=="" and out["stateMinutes"]==0,(old_hour,old_delay,"internal state",out)
        assert out["club"]=="Tournoi en cours" and out["round"]==2 and out["started"],out
        resumed.evaluate("showSettings(false)")
        assert resumed.locator("#resumeTime").input_value()==""
        assert resumed.locator("#resumeDelayMinutes").input_value()==""
        resumed.evaluate("recoveryAutoSave(true)")
        clean=json.loads(resumed.evaluate("bridgeAuditStorage.getItem(RECOVERY_KEY)"))
        assert clean["settings"]["resumeTime"]=="" and clean["settings"]["resumeDelayMinutes"]==0
        resumed.close()

    browser.close()
print("Recovery test OK: interrupted session, fresh settings and both Reprise a fields cleared on every reopen")
