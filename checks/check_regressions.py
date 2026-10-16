from pathlib import Path
import json
import re
import sys

root = Path(__file__).resolve().parents[1]
html = (root / "timer.html").read_text(encoding="utf-8")
main = (root / "main.go").read_text(encoding="utf-8")
manifest = (root / "BridgeTimer.manifest").read_text(encoding="utf-8")
release_workflow = (root / ".github" / "workflows" / "release-unsigned.yml").read_text(encoding="utf-8")
sign_workflow = (root / ".github" / "workflows" / "sign-release.yml").read_text(encoding="utf-8")
vi = json.loads((root / "versioninfo.json").read_text(encoding="utf-8"))

version = vi["StringFileInfo"]["ProductVersion"]
file_version = vi["StringFileInfo"]["FileVersion"]

required_html = [
    '#clock{font:700 100px/.78 Bahnschrift,Consolas,monospace;letter-spacing:0;white-space:nowrap;transform:translateY(10px);font-variant-numeric:tabular-nums;visibility:hidden}',
    '#msg{font-weight:950;font-size:clamp(26px,4.2vw,64px);line-height:1.05;min-height:1.1em;max-width:1300px}',
    'id="accent" type="color"',
    'id="background" type="color"',
    'id="menu" type="color"',
    'id="text" type="color"',
    'e.key==="F7"',
    'e.key==="F8"',
    'e.key==="F9"',

    'e.key==="ArrowRight"',
    'nativeSetAwake',
    'nativeDiagnostics',
    'const monotonicNow=()=>performance.now()',
    'function playRoundEndSound()',
    'TOUR EN COURS',
    'CHANGEMENT DE TOUR',
    'if(el.id!=="pairCount")el.addEventListener("input",scheduleAutosave)',
    'raw!==""&&Number.isInteger(n)&&n>=6&&n<=36',
    '.btn:active{filter:brightness(.94);transform:translateY(1px)}',
    'el.focus({preventScroll:true});try{el.select()}catch(err){}',
    'window.scrollTo(0,0);document.documentElement.scrollTop=0;document.body.scrollTop=0',
    'input:disabled,select:disabled{background:#030712!important',
    '.compactSelect{width:128px!important}',
    '.movementSelect{width:108px!important}',
    '.optionCards{display:grid;grid-template-columns:1.2fr 1fr;',
    'function transitionAfterRound(){',
    'id="saveColorsBtn"',
    'id="savedColorsBtn"',
    'COLORKEY="bridgeTimerWebView2.savedColors"',
    'function saveCurrentColors()',
    'function loadSavedColors()',
    '#submsg.tempMessage{color:var(--accent)',
    '$("submsg").classList.remove("tempMessage","jumpUpcoming")',
    '$("tempmsg").textContent=s.quickMessage||"Saisir les scores"',
    'id="miniTimer"',
    'body.settingsLive #miniTimer',
    'document.body.classList.toggle("settingsLive",live)',
    '$("drawerClose").onclick=showTimer',
]

required_main = [
    f'appVersion = "{version}"',
    '--disable-lcd-text',
    'SetThreadExecutionState',
    'port = 43831',
    'w.SetSize(defaultWindowWidth, defaultWindowHeight, webview.HintMin)',
    'return 0, 0, defaultWindowWidth, defaultWindowHeight, false',
    'monitorFromWindow.Call(hwnd, monitorDefaultToNearest)',
]

errors = []
for token in required_html:
    if token not in html:
        errors.append("timer.html missing: " + token[:100])
for token in required_main:
    if token not in main:
        errors.append("main.go missing: " + token[:100])

# Tournament profiles and configuration import/export remain removed.
# Optional club logo was intentionally restored. Keep the custom saved-color preset.
for token in ('id="logoInput"', 'id="removeLogo"', 'id="logo"', '<h2>Profils</h2>', 'id="exportConfig"', 'id="importConfig"', 'profileSave0', 'function emptyProfiles', 'function exportConfiguration', 'function importConfiguration', 'PROFILEKEY', 'LKEY'):
    if token in html:
        errors.append("removed personalization feature returned: " + token)

# Retired native configuration/screen-cycle/window-state plumbing must not return.
for token in (
    'nativeCycleMonitor', 'nativeSetMonitor', 'nativeExportConfig', 'nativeImportConfig',
    'cycleProjectionMonitor(', 'setProjectionMonitor(', 'exportBridgeTimerFile(',
    'importBridgeTimerFile(', 'restoreWindowState(', 'loadWindowState(',
    'readWindowStateFile(', 'saveWindowState(', 'windowStatePath(', 'atomicWriteFile(',
    'selectedMonitor', 'projectionMonitor'
):
    if token in main or token in html:
        errors.append("retired native feature returned: " + token)

# Retired 10-second preview and empty active-session persistence stubs must stay gone.
for token in (
    'startPreview(', 'endPreview(', 'previewMode', 'previewSavedState', 'previewTimer',
    'persistState(', 'clearPersistedState(', 'endMessage'
):
    if token in html:
        errors.append("retired timer feature returned: " + token)

# Screen selector button and side-drawer settings mode were deliberately removed.
for token in ('id="screenBtn"', 'cycleNativeMonitor', 'drawerOpen()', 'closeSettingsDrawer()', 'openFullSettings()', 'Paramètres complets'):
    if token in html:
        errors.append("removed screen/drawer UI returned: " + token)

# Tournament type is configuration-only and must not be shown to players.
if '$("submsg").textContent=s.mode==="4"?"Match par 4":"Paires"' in html:
    errors.append("player timer must not display Paires / Match par 4")

# The removed end-of-round delay feature must not return.
for token in ('id="finishSec"', 'id="finishMessage"', 'phase==="finish"', 's.finishSec', 's.finishMessage', 'FINISHDELAYMIGRATIONKEY'):
    if token in html:
        errors.append("removed end-of-round delay feature returned: " + token)

# Numeric fields should select all only when focus first enters the field,
# and do it synchronously to avoid a visible focus-then-selection flicker.
if 'el.addEventListener("focus",selectAll)' in html or 'el.addEventListener("click",selectAll)' in html:
    errors.append("numeric fields must not re-select all text on focus or every click")
if 'setTimeout(()=>{try{el.select()' in html:
    errors.append("numeric selection must not be delayed after focus")

# Prevent accidental loss of the four color controls.
if len(re.findall(r'type="color"', html)) < 4:
    errors.append("expected at least four HTML color inputs")


# Every HTML id must be unique. Duplicate ids silently make document.getElementById
# target the wrong control and previously caused the Donnes par tour preset bug.
html_ids = re.findall(r'id="([^"]+)"', html)
duplicate_ids = sorted({x for x in html_ids if html_ids.count(x) > 1})
if duplicate_ids:
    errors.append("duplicate HTML ids: " + ", ".join(duplicate_ids))

# Tournament-format UI contract.
match_option = '<option value="4" selected>Match par 4</option><option value="2">Paires</option>'
if match_option not in html:
    errors.append("Format must list Match par 4 first and select it by default")
if 'id="betweenLabel">Temps entre tours' not in html or '$("between").disabled=!pairs' not in html:
    errors.append("Temps entre tours must be disabled outside Paires mode")
if html.count('id="boards"') != 1:
    errors.append("Donnes par tour must exist exactly once")
if 'class="inlineSetting boardsInline"><label>Donnes par tour</label><input id="boards"' not in html:
    errors.append("Donnes par tour must stay on the Nb de tours row")
if html.find('class="inlineSetting boardsInline"><label>Donnes par tour</label>') > html.find('class="inlineSetting startInline"><label>Tour de départ</label>'):
    errors.append("Donnes par tour must appear before Tour de départ")
if '.roundConfigRow .boardsInline{margin-left:34px;min-width:0}.roundConfigRow .startInline{margin-left:14px}' not in html:
    errors.append("round row spacing/alignment must stay compact")
if '.unitField input[type=number],.unitField input[type=tel]{width:56px}' not in html or '.compactNumber{width:58px!important}' not in html:
    errors.append("fixed-size tournament controls must stay compact")
if '<select id="positionsSelect" class="compactNumber roundCountSelect hidden"></select>' not in html:
    errors.append("Paires round-count control must keep the Match/4 row geometry")
if '.roundCountSelect{width:58px!important;appearance:none;-webkit-appearance:none;padding:7px 9px;background:var(--field);background-image:none}' not in html:
    errors.append("Paires round-count select must render exactly like the Match/4 numeric field")
if 'boards.disabled=true' not in html:
    errors.append("Paires boards preset must be disabled and grey when it cannot be edited")
if 'sel.disabled=opts.length<=1' not in html:
    errors.append("single-choice round count must be disabled and grey")
if '#status{font-weight:950;letter-spacing:.04em;color:var(--text);font-size:clamp(38px,5vw,74px);transform:translateY(-40px);min-height:1.15em;max-width:calc(100vw - 96px);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}' not in html:
    errors.append("top timer message must follow Text color and stay on one line without moving the timer")
if '#submsg{position:absolute;left:50%;bottom:10px;transform:translateX(-50%);z-index:6;font-weight:800;font-size:clamp(18px,2.3vw,36px);color:var(--text);' not in html:
    errors.append("board-progress message must follow Text color")
# The central layout is proportional in both presentation modes; clock glyphs are fitted
# to the actual available space using a fixed HH:MM:SS width for both formats.
for token in [
    '#timer .main{display:grid;grid-template-columns:minmax(0,1fr);grid-template-rows:minmax(0,10fr) minmax(0,58fr) minmax(14px,3fr) minmax(0,9fr) minmax(0,9fr) minmax(0,11fr);',
    '#timer #status{transform:none;min-height:0;max-width:100%;align-self:start;margin-top:clamp(2px,.6vh,8px);font-size:clamp(38px,4.2vw,64px);line-height:1.05;position:relative;top:calc(-1 * clamp(10px,1.8vh,18px))}',
    '#timer #clock{transform:none;align-self:center;justify-self:center;letter-spacing:-.055em;font-stretch:condensed;position:relative;top:clamp(9px,1.5vh,16px)}',
    '#timer #msg{min-height:0;max-width:calc(100% - 32px);align-self:center;position:relative;top:clamp(8px,1.25vh,12px)}',
    '#timer #submsg{position:relative;left:auto;bottom:auto;transform:none;',
    '#timer #tempmsg{min-height:0;max-width:calc(100% - 32px);width:100%;justify-self:center;align-self:center;'
    'pointer-events:none;position:relative;top:clamp(11px,1.55vh,16px)',
    '<div id="submsg"></div><div id="tempmsg" role="status" aria-live="polite"></div>',
    '$("tempmsg").textContent="";$("alert").className=""',
    'if(tempMessageActive()&&st.phase!=="ended"){$("tempmsg").textContent=s.quickMessage||"Saisir les scores"}',
    '#timer #alert{position:absolute;bottom:17%;',
    'p.textContent="01:00:00"',
    'const k=width+"x"+height+"x"+fs',
    'const maxWidth=Math.max(100,Math.min(width-24,innerWidth*.96)),clockSlotHeight=height*.57',
    'p.style.fontStretch="condensed";p.style.fontVariantNumeric="tabular-nums"',
    'letter-spacing:-.055em;white-space:nowrap;transform:none',
    'z.transform="none";z.visibility="visible"',
]:
    if token not in html:
        errors.append("proportional central layout / clock fitting regression: " + token)
if 'c.textContent.length' in html[html.index('function fc()'):html.index('function render()')] or 'p.textContent=c.textContent' in html:
    errors.append("clock size must NOT depend on 59:59 vs 01:00:00 format")
if 'scaleX(' in html[html.index('function fc()'):html.index('function render()')]:
    errors.append("timer clock must never be horizontally distorted")
# The M shortcut must not replace the board progress text or jump reminder.
if '$("submsg").textContent=s.quickMessage' in html or '$("submsg").classList.add("tempMessage")' in html:
    errors.append("temporary M message must use its independent line, not the board notice")
# The clock itself and progress bar are not resized/moved as a group; only title and clock clearance change.
for token in ['#timer .progress{align-self:center}', '#timer #msg{min-height:0;max-width:calc(100% - 32px);align-self:center;position:relative;top:clamp(8px,1.25vh,12px)}']:
    if token not in html:
        errors.append('upper text adjustment changed progress or competition layout: '+token)

# The top and bottom frame dimensions must be unaffected by central reflow.
for token in ['.top{display:grid;grid-template-columns:1fr auto;align-items:center;gap:15px;padding:14px 22px;border-bottom:1px solid var(--line);',
              '.bottom{position:relative;height:82px;min-height:82px;padding:11px 190px 15px;border-top:1px solid var(--line);']:
    if token not in html:
        errors.append("timer frame border geometry changed: " + token)

if 's=x?{...def,...x,mode:"4",positions:6,startPosition:1,boards:8,between:0,pairCount:26,movement:"mitchell"}:{...def}' not in html:
    errors.append("startup tournament presets must be restored on every launch")
if 'boards:8,boardMinutes:7,boardSeconds:30,positions:6,startPosition:1,between:0,pairCount:26,mode:"4",movement:"mitchell"' not in html:
    errors.append("default Match par 4 preset must be 6 rounds, start 1, 8 boards, 0 seconds between rounds")
if 'id="between" type="tel" min="0" max="240" value="00"' not in html:
    errors.append("Temps entre tours must default to zero")
if 'return {positions:13,startPosition:1,boards:boards,hours:Math.floor(total/3600),minutes:Math.floor(total%3600/60),seconds:total%60,between:0,pairCount:26,movement:"mitchell"}' not in html:
    errors.append("first switch to Paires must preset 26 pairs and 13 rounds")
if 'activeFormat="4",formatSession={"4":null,"2":null}' not in html:
    errors.append("format settings must use session-only memory")
for token in [
    'function captureFormatState(mode)',
    'function defaultFormatState(mode)',
    'function applyFormatState(mode,state)',
    'formatSession[activeFormat]=captureFormatState(activeFormat)',
    'const state=formatSession[target]||defaultFormatState(target)',
    'formatSession={"4":captureFormatState("4"),"2":null}',
]:
    if token not in html:
        errors.append("format session memory contract missing: " + token)
if 'calcBoardDuration();read();render();scheduleAutosave()' not in html:
    errors.append("format/movement preset changes must keep round time coherent with boards x time per board")
if '<div class="messageInline"><label for="mainMessage">Message en direct</label>' not in html:
    errors.append("Message en direct must stay inline with its input")
if '$("status").textContent=s.mainMessage;$("msg").textContent=(s.eventName||"").trim();' not in html:
    errors.append("timer must show Message en direct in the top status slot and Evenement in the former live-message slot")
if '<button id="jumpMsgBtn" class="btn jumpMsgBtn hidden" type="button"' not in html or '<div id="jumpMsgOverlay" class="jumpMsgOverlay hidden"' not in html:
    errors.append("MSG button and its dialog must exist")
if 'function openJumpMsg()' not in html or 'function closeJumpMsg()' not in html or '$("jumpMsgOverlay").onclick=e=>' not in html:
    errors.append("MSG submenu must open and close, including backdrop click")
if 'if(e.key==="Escape"&&!$("jumpMsgOverlay").classList.contains("hidden"))' not in html:
    errors.append("MSG submenu must close with Escape before timer shortcuts")
if 'document.querySelectorAll("#settings input,#settings select,#settings textarea")' not in html:
    errors.append("MSG textarea edits must be included in autosave")
if '<div class="boardOptionsRow"><div class="boardProgressOption"><label>Affichage n° donne en cours</label><input id="boardProgressNotice" type="checkbox" checked></div><div class="soundOption"><label>Son</label><input id="sound" type="checkbox" checked></div></div>' not in html or '<label class="jumpAdvanceOption alertOption pairOnly jumpOnly"><span>Pré-alerte saut</span><input id="jumpAdvanceNotice" type="checkbox" checked></label>' not in html:
    errors.append("board tracking/sound row or pre-jump alert beside red threshold regressed")
if '.boardOptionsRow{grid-column:1/-1;display:flex;align-items:center;gap:8px 48px}' not in html or '.soundOption{margin-left:0}' not in html:
    errors.append("sound must stay in its approved compact position")
if 'Afficher dès la zone orange du tour précédent' in html or 'Prévenir avant le saut' in html:
    errors.append("pre-jump explanatory wording must stay removed")
if '>Activé</div>' in html:
    errors.append("sound option must use only its checkbox, without an Activé caption")
if 'boardProgressLabel' in html:
    errors.append("board tracking explanatory text must stay removed")
if 'cb.disabled=!ok;if(!ok){cb.checked=false;s.boardProgressNotice=false}' not in html:
    errors.append("disabled board tracking must be unchecked and visibly disabled")
if '<button id="defaults" class="btn danger">Reset param.</button>' not in html:
    errors.append("reset button label must be Reset param.")
if 'id="jumpRoundSetting"' not in html or '$("jumpRoundSetting").classList.toggle("hidden",!jumpAfter)' not in html:
    errors.append("Saut après tour must disappear when the movement has no jump")
if 'document.querySelectorAll(".jumpOnly").forEach(el=>{el.classList.toggle("hidden",!jumpAfter)})' not in html or 'document.querySelectorAll(".jumpOnly").forEach(el=>{el.classList.add("hidden")})' not in html:
    errors.append("jump-only controls must not reserve layout space when unavailable")
if '#undoToast{position:fixed;z-index:40;right:18px;bottom:121px;zoom:.78;' not in html or '.fs #undoToast{bottom:94px;zoom:1}' not in html:
    errors.append("undo toast must preserve its approved windowed/fullscreen alignment")
# End-of-round alerts are strictly time-based; text alerts and percentages are gone.
for token in [
    '<div class="grid alertGrid"><label>Orange à</label>',
    'id="warnMinutes" type="tel" min="0" max="60" value="02"',
    '<span>Activé</span><input id="warnEnabled" type="checkbox" checked>',
    'warnEnabled:true',
    'warnEnabled:$("warnEnabled").checked',
    'ws=s.warnEnabled===false?0:warnThreshold(total)',
    'id="dangerMinutes" type="tel" min="0" max="60" value="01"',
    'function warnThreshold(){return Math.max(0,(Number(s.warnMinutes)||0)*60+(Number(s.warnSeconds)||0))}',
    'function dangerThreshold(){return Math.max(0,(Number(s.dangerMinutes)||0)*60+(Number(s.dangerSeconds)||0))}',
    'const jumpNoticeAt=ds',
    's.jumpAdvanceNotice&&s.jumpRound',
    '$("submsg").classList.add("jumpUpcoming")',
]:
    if token not in html:
        errors.append("fixed-time alert or jump-preview regression: " + token)
for token in [
    'id="warnPercentMode"', 'id="dangerPercentMode"', 'id="warnPercent"', 'id="dangerPercent"',
    'id="warnMessageEnabled"', 'id="dangerMessageEnabled"', 'id="dangerMessage"',
    'function updateAlertRulesUI()', 'function zoneThreshold(', 's.warnMessageEnabled&&',
    's.dangerMessageEnabled&&', 'alertPercentToggle', 'alertMsgToggle',
]:
    if token in html:
        errors.append("retired end-of-round percentage or message returned: " + token)
if '.optionCards .grid.alertGrid{grid-template-columns:72px 1fr;gap:8px 6px}' not in html or '.alertRule{display:flex;align-items:center;gap:12px}' not in html or '.alertRule .alertOption{display:inline-flex;' not in html:
    errors.append("compact fixed-time alert controls layout regression")

if 'const jumpNoticeAt=warnThreshold(total)||ds' in html or 'const jumpNoticeAt=ws||ds' in html:
    errors.append("pre-jump notice must start at the red threshold, not orange")

# Default club identity.
for token in [
    'clubName:"FFB - Comité de Provence"',
    '<input id="clubName" type="text" value="FFB - Comité de Provence">',
    'clubName:$("clubName").value.trim()||"FFB - Comité de Provence"',
    '<div id="club">FFB - Comité de Provence</div>',
]:
    if token not in html:
        errors.append("default club name regression: " + token)
if 'eventName:""' not in html or '<input id="eventName" type="text" value="">' not in html:
    errors.append("default event must stay empty")
if 'if(s.eventName==="TTTT")s.eventName=""' in html:
    errors.append("saved event values must never be erased by a special-case migration")

# Debug mode is an emergency UI override. Normal structural defaults must still
# be calculated after format/pair-count changes, while the resulting fields remain editable.
for token in [
    'id="debugBtn" class="btn">Debug</button>',
    'const debugActive=()=>document.body.classList.contains("debugMode")',
    'function applyDebugUnlock()',
    'function withNormalRulesInDebug(fn)',
    'withNormalRulesInDebug(()=>updatePairModeUI(true))',
    'withNormalRulesInDebug(()=>{const target=$("mode").value',
    'fill();read();updateSavedColorsUI();setLiveStructureLock(st.started&&document.body.classList.contains("settingsLive"))',
    'opts=["mitchell","gueridon","howell"]',
    'if(debugActive()){read();safeJSONWrite(KEY,s);if(!st.started){st.remaining=duration();render()}return}',
    'function applyDebugSettingsToCurrentTimer()',
    'else applyDebugSettingsToCurrentTimer();showTimer();render()',
    'save();applyDebugSettingsToCurrentTimer()}',
    'if(debugActive())applyDebugUnlock();fc()',
    'if(!st.started&&!$("settings").classList.contains("hidden"))return',
]:
    if token not in html:
        errors.append("Debug-mode contract missing: " + token)
if 'body.debugMode .drawerClose{display:inline-flex!important}' in html:
    errors.append("Debug must not expose Retour au timer before a timer exists")
if 'body.debugMode #stopTimer.hidden{visibility:visible!important}' in html:
    errors.append("Debug must not show Arrêter before the timer is started")
if 'sel.value=chosen;sel.disabled=true;const jumpAfter=computePairJumpAfter(p,chosen);$("jumpRound").value=jumpAfter||"—";$("jumpRound").disabled=true;' not in html:
    errors.append("leaving Debug must restore normal locks on Mouvement and Saut après tour")
if 'if(debugActive()){read();applyDebugUnlock();render();scheduleAutosave();return}' in html:
    errors.append("Debug format changes must not bypass normal format defaults")
if '$("pairCount").onchange=()=>{updatePairModeUI(true);' in html:
    errors.append("Debug pair-count changes must not bypass normal pair defaults")

# Fullscreen transition and numpad time hotkeys.
for token in [
    'body.fsTransition #timer{opacity:.12;transform:scale(.985);transform-origin:center;transition:opacity .18s ease,transform .18s ease}',
    'body.fsTransition.fsReveal #timer{opacity:1;transform:scale(1);transition:opacity .30s cubic-bezier(.22,.61,.36,1),transform .30s cubic-bezier(.22,.61,.36,1)}',
    'document.body.classList.remove("fsReveal");document.body.classList.add("fsTransition");await new Promise(r=>setTimeout(r,190))',
    'function finishFsTransition(){C=null;requestAnimationFrame(()=>requestAnimationFrame(()=>setTimeout(()=>{fc();requestAnimationFrame(()=>{document.body.classList.add("fsReveal");setTimeout(()=>document.body.classList.remove("fsTransition","fsReveal"),330)})},70)))}',
    'e.key==="F7"||e.code==="NumpadSubtract"',
    'e.key==="F8"||e.code==="NumpadAdd"',
    'if(tv&&(e.key==="F7"||e.code==="NumpadSubtract"||e.key==="-"))',
]:
    if token not in html:
        errors.append("fullscreen/numpad contract missing: " + token)

# Timer seconds must stay phase-aligned with the displayed wall clock.
for token in [
    'function alignedWallDelayMs(wallNow,remaining)',
    'function syncEndAtToWallSecond()',
    'setInterval(()=>{updateLocalTime();tick()},50)',
    'if(delta<=0)',
    'setInterval(()=>{if(!st.running)updateLocalTime()},200)',
]:
    if token not in html:
        errors.append("wall-clock synchronization regression: " + token)

# Live tournament settings: structure is locked, while timing changes are queued
# naturally for the next round through the active-round timing snapshot.
for token in [
    'const structuralSettingIds=["mode","pairCount","movement","positions","positionsSelect","startPosition","boards"]',
    'function setLiveStructureLock(live)',
    'function snapshotRoundSettings()',
    'function currentRoundDuration()',
    'function currentRoundBetween()',
    'function currentRoundBoardTimingMatches()',
]:
    if token not in html:
        errors.append("live settings contract missing: " + token)
if 'fill();setLiveStructureLock(live);render()' not in html:
    errors.append("settings structure must be locked while a tournament is live")
if 'st.remaining=currentRoundDuration()' not in html:
    errors.append("new rounds must use the snapshotted round duration")
if 'function restoreUndoState(x)' not in html or 'roundDuration:x.roundDuration' not in html or 'roundBetween:x.roundBetween' not in html or 'roundBoardDuration:x.roundBoardDuration' not in html or 'roundBoards:x.roundBoards' not in html:
    errors.append("Undo must restore the complete active-round timing snapshot")

# The jump announcement uses a dedicated, configurable, full-timer overlay.
for token in ['id="jumpDisplaySecs"', 'id="jumpSplash"', 'st.phase==="jump"', 's.jumpDisplaySecs', '$("jumpSplash").classList.toggle("on",jumpSplashOn)']:
    if token not in html:
        errors.append("jump announcement overlay missing: " + token)
if 'const between=currentRoundBetween()' not in html:
    errors.append("between-round duration must be snapshotted for the active round")

# F1 must remain a real toggle and its on-screen help should document all active shortcuts.
for token in [
    '$("hint").classList.toggle("hintVisible")',
    'F11 : plein écran',
    'F9 : paramètres',

]:
    if token not in html:
        errors.append("F1 help regression: " + token)

# Guard the tournament/card/dialog hierarchy using a real HTML structure parser.
# Previously a missing </div> silently broke the whole settings grid.
from html.parser import HTMLParser

class LayoutGuard(HTMLParser):
    def __init__(self):
        super().__init__()
        self.stack = []
        self.loc = {}
        self.structure_errors = []
        self.void = {"area","base","br","col","embed","hr","img","input","link","meta","param","source","track","wbr"}

    def handle_starttag(self, tag, attrs):
        data = dict(attrs)
        ident = data.get("id")
        if ident:
            if ident in self.loc:
                self.structure_errors.append("duplicate id: " + ident)
            self.loc[ident] = (tag, list(self.stack))
        if tag not in self.void:
            self.stack.append((tag, ident, data.get("class", "")))

    def handle_endtag(self, tag):
        if not self.stack or self.stack[-1][0] != tag:
            self.structure_errors.append("mismatched closing tag: " + tag)
            return
        self.stack.pop()

guard = LayoutGuard()
guard.feed(html)
if guard.stack:
    errors.append("unclosed HTML tags: " + str(guard.stack[-4:]))
errors.extend(guard.structure_errors[:6])

def parent_chain(ident):
    return guard.loc.get(ident, (None, []))[1]

def within(ident, ancestor):
    return any(node[1] == ancestor for node in parent_chain(ident))

if not within("jumpMsgBtn", "jumpRoundSetting"):
    errors.append("MSG button must appear directly beside the jump round input")
for field in ("jumpSplashTitleSetting","jumpSplashBodySetting","jumpDisplaySecs","jumpCountdownLabel","jumpMessage"):
    if not within(field, "jumpMsgOverlay") or within(field, "tournamentCard"):
        errors.append("jump setting must belong to MSG dialog only: " + field)
if not any("optionCards" in n[2].split() for n in parent_chain("warnMinutes")):
    errors.append("alert cards must stay outside tournament grid")
for field in ("warnMinutes","dangerMinutes","boardMinutes","boards","between"):
    if field not in guard.loc:
        errors.append("main tournament field went missing: " + field)
if not within("jumpMsgOverlay", "settings"):
    errors.append("MSG floating dialog must be within settings section")
# MSG layout and Debug mode contracts.
for token in [
    'jumpMessage:"Au prochain tour, les EO sautent une table"',
    'id="jumpMessage" type="text" value="Au prochain tour, les EO sautent une table"',
    's.jumpMessage==="ATTENTION : les EO sautent une table"',
    'function applyDebugUnlock(){if(!debugActive())return false;document.querySelectorAll("button,input,select,textarea").forEach(el=>el.disabled=false);$("jumpMsgBtn").classList.remove("hidden")',
    'function openJumpMsg(){if(!debugActive()&&(',
    '<div class="jumpMsgTitleRow"><label for="jumpSplashTitleSetting">Titre</label>',
    'id="jumpSplashBodySetting" rows="2"',
    'class="jumpMsgTimeRow"',
    '<div class="jumpMsgPreAlert"><label for="jumpMessage">Message de pré-alerte du saut</label>',
    '.jumpMsgFields textarea{height:60px;min-height:60px;max-height:60px;resize:none;',
    '.jumpMsgClose{width:32px;height:32px;min-width:32px;display:flex;align-items:center;justify-content:center;',
    '.jumpMsgTimeCol .unitField input{width:56px;min-width:56px}',
]:
    if token not in html:
        errors.append("MSG dialog polish or Debug availability regression: " + token)
for classname, fields in [
    ("jumpMsgTitleRow", ("jumpSplashTitleSetting",)),
    ("jumpMsgTimeRow", ("jumpDisplaySecs", "jumpCountdownLabel")),
    ("jumpMsgPreAlert", ("jumpMessage",)),
]:
    for field in fields:
        if not any(classname in ancestor[2].split() for ancestor in parent_chain(field)):
            errors.append("MSG layout grouping regressed: " + classname + "/" + field)

if 'Message du saut</label>' in html or 'Affichage saut</label>' in html or 'class="jumpCustomization"' in html:
    errors.append("old inline jump controls must be gone")
ordered_fields = ['for="jumpSplashTitleSetting">Titre','for="jumpSplashBodySetting">Message au moment du saut','for="jumpDisplaySecs">Nb secondes pour le saut','for="jumpCountdownLabel">Texte du décompte','for="jumpMessage">Message de pré-alerte du saut']
indexes = [html.find(fragment) for fragment in ordered_fields]
if -1 in indexes or indexes != sorted(indexes):
    errors.append("MSG five controls must remain in the requested order")

# Keep all Windows/release version metadata aligned.
if f'version="{file_version}"' not in manifest:
    errors.append(f"BridgeTimer.manifest version must be {file_version}")
if f"default: '{version}'" not in release_workflow:
    errors.append(f"release workflow default version must be {version}")
if f"default: '{version}'" not in sign_workflow:
    errors.append(f"sign workflow default version must be {version}")
if "--generate-notes" not in release_workflow:
    errors.append("release workflow must not depend on a version-specific notes file")
if "Verify release version" not in release_workflow:
    errors.append("release workflow must verify requested version against versioninfo.json")

# Startup must use a stable origin and dark WebView2/native backing colors.
# The app now always opens centered; the pre-show coordinate patch remains
# available to the wrapper but no saved window position is restored.
patch_source = (root / "patch_webview_dark.py").read_text(encoding="utf-8")
if "HbrBackground: bridgeTimerDarkBrush()" not in patch_source:
    errors.append("WebView parent window must have a dark background brush")
if "UsePosition bool" not in patch_source:
    errors.append("WebView patch must support pre-show saved coordinates")
if "applyBridgeTimerDarkBeforeShow(w.hwnd)\\n\\t' + show_marker" not in patch_source:
    errors.append("dark title must be applied immediately before ShowWindow")
if 'WEBVIEW2_DEFAULT_BACKGROUND_COLOR", "FF0F172A' not in main:
    errors.append("WebView2 default background must be dark before initialization")
if 'UsePosition: hasSavedPosition' not in main:
    errors.append("WebView wrapper position option must remain wired consistently")
if "nativeReady" in main or "nativeReady" in html:
    errors.append("failed hidden-window startup handshake must not return")

if 'w.Dispatch(func() {' not in patch_source or 'VK_F1' not in patch_source:
    errors.append("native F1 handling must dispatch the toggle onto the WebView UI loop")
if 'wp != 1 && w.autofocus' not in patch_source or 'w.browser.Focus()' not in patch_source:
    errors.append("WebView focus must be restored after Windows maximize/restore")
if 'monitorFromWindow.Call(hwnd, monitorDefaultToNearest)' not in main:
    errors.append("fullscreen must use the monitor containing the current BridgeTimer window")
if 'net.JoinHostPort(host, "0")' in main:
    errors.append("ephemeral WebView origin would break persistent localStorage")

# Retired UI paths should stay removed.
for forbidden in [".dockMode", ".dc #settings", "@keyframes drawerIn", "@keyframes drawerOut", ".profileRow"]:
    if forbidden in html:
        errors.append("retired UI CSS returned: " + forbidden)
if "var(--border)" in html:
    errors.append("undefined CSS variable --border returned")

# Prevent reintroduction of the retired active-session recovery popup/state writes.
for forbidden in [
    "STATEKEY",
    "Une session précédente a été retrouvée",
    "function tryRecoverState",
    "function advanceRecoveredState",
]:
    if forbidden in html:
        errors.append("retired session recovery returned: " + forbidden)

# Build tooling should be deterministic.
for workflow_name, workflow in [
    ("build", (root / ".github" / "workflows" / "build.yml").read_text(encoding="utf-8")),
    ("release", release_workflow),
    ("sign", sign_workflow),
]:
    if "goversioninfo@latest" in workflow:
        errors.append(workflow_name + " workflow uses unpinned goversioninfo")
    if "check_js_syntax.py" not in workflow:
        errors.append(workflow_name + " workflow does not check JavaScript syntax")

if errors:
    print("BridgeTimer regression check FAILED:")
    for e in errors:
        print(" -", e)
    sys.exit(1)

print(f"BridgeTimer regression check OK — version {version}")

# RENDERING CONTRACT — central reflow approved; preserve glyphs, color choices, and frame.
frozen_render_tokens = [
    '--disable-lcd-text',
    '#clock{font:700 100px/.78 Bahnschrift,Consolas,monospace;',
    '#status{font-weight:950;letter-spacing:.04em;color:var(--text);',
    '#msg{font-weight:950;font-size:clamp(26px,4.2vw,64px);',
    '#submsg{position:absolute;left:50%;bottom:10px;transform:translateX(-50%);z-index:6;font-weight:800;',
    '#timer #submsg{position:relative;left:auto;bottom:auto;transform:none;',
    '#timer .main{display:grid;',
]
for token in frozen_render_tokens:
    haystack = main if token == '--disable-lcd-text' else html
    if token not in haystack:
        print("Frozen rendering contract FAILED:", token)
        sys.exit(1)

for token in ['safeJSONRead(', 'safeJSONWrite(', 'backupKey(', 'validColorPreset(', 'COLORKEY="bridgeTimerWebView2.savedColors"']:
    if token not in html:
        print("Storage safety regression FAILED:", token)
        sys.exit(1)

print("Frozen rendering contract OK")
