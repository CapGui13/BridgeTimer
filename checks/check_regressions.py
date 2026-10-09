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
    '#clock{font-family:Bahnschrift,Consolas,monospace;font-weight:700;font-size:clamp(210px,37vw,620px);line-height:.78;letter-spacing:0;white-space:nowrap;transform:translateY(10px)}',
    '#msg{font-weight:950;font-size:clamp(26px,4.2vw,64px);line-height:1.05;min-height:1.1em;max-width:1300px}',
    'id="accent" type="color"',
    'id="background" type="color"',
    'id="menu" type="color"',
    'id="text" type="color"',
    'e.key==="F7"',
    'e.key==="F8"',
    'e.key==="F9"',
    'e.key==="F10"',
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
    '.compactSelect{width:135px!important}',
    '.movementSelect{width:112px!important}',
    '.optionCards{display:grid;grid-template-columns:1.2fr 1fr;',
    'function transitionAfterRound(){',
    'id="saveColorsBtn"',
    'id="savedColorsBtn"',
    'COLORKEY="bridgeTimerWebView2.savedColors"',
    'function saveCurrentColors()',
    'function loadSavedColors()',
    '#submsg.tempMessage{color:var(--accent)',
    '$("submsg").classList.remove("tempMessage","jumpUpcoming")',
    '$("submsg").textContent=s.quickMessage||"Saisir les scores"',
    'id="miniTimer"',
    'body.settingsLive #miniTimer',
    'document.body.classList.toggle("settingsLive",live)',
    '$("drawerClose").onclick=showTimer',
]

required_main = [
    f'appVersion = "{version}"',
    '--disable-lcd-text',
    'SetThreadExecutionState',
    'MoveFileExW',
    'window.json',
    'window state: recovered from backup',
    'windowLayoutVersion = 2',
    'port = 43831',
    'w.SetSize(defaultWindowWidth, defaultWindowHeight, webview.HintMin)',
    'return 0, 0, defaultWindowWidth, defaultWindowHeight, false',
]

errors = []
for token in required_html:
    if token not in html:
        errors.append("timer.html missing: " + token[:100])
for token in required_main:
    if token not in main:
        errors.append("main.go missing: " + token[:100])

# Logo, tournament profiles and configuration import/export were deliberately removed
# from the user interface. Keep the custom saved-color preset instead.
for token in ('id="logoInput"', 'id="removeLogo"', 'id="logo"', '<h2>Profils</h2>', 'id="exportConfig"', 'id="importConfig"', 'profileSave0', 'function emptyProfiles', 'function exportConfiguration', 'function importConfiguration', 'PROFILEKEY', 'LKEY', 'logoData'):
    if token in html:
        errors.append("removed personalization feature returned: " + token)

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

# Startup must use a stable origin, a dark WebView2 backing color, and native
# coordinates before the first ShowWindow. This avoids both white flashes and
# visible center->saved-position jumps without hiding the HWND.
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
    errors.append("saved window position must be supplied before WebView creation")
if "nativeReady" in main or "nativeReady" in html:
    errors.append("failed hidden-window startup handshake must not return")
if 'net.JoinHostPort(host, "0")' in main:
    errors.append("ephemeral WebView origin would break persistent localStorage")

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

# FROZEN RENDERING CONTRACT — approved after V3.2 side-by-side comparison.
frozen_render_tokens = [
    '--disable-lcd-text',
    '#clock{font-family:Bahnschrift,Consolas,monospace;font-weight:700;font-size:clamp(210px,37vw,620px);line-height:.78;letter-spacing:0;white-space:nowrap;transform:translateY(10px)}',
    '#msg{font-weight:950;font-size:clamp(26px,4.2vw,64px);line-height:1.05;min-height:1.1em;max-width:1300px}',
    '#submsg{font-weight:800;font-size:clamp(18px,2.3vw,36px);color:var(--muted);height:clamp(42px,4.8vw,80px);line-height:1.08;max-width:1300px;width:100%;display:flex;align-items:center;justify-content:center;overflow:hidden}',
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
