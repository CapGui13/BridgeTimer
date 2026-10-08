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
    '#clock{font-family:Bahnschrift,Consolas,monospace;font-weight:650;font-size:clamp(110px,24vw,350px);line-height:.84;letter-spacing:.035em;white-space:nowrap}',
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
    'nativeReady',
]

errors = []
for token in required_html:
    if token not in html:
        errors.append("timer.html missing: " + token[:100])
for token in required_main:
    if token not in main:
        errors.append("main.go missing: " + token[:100])

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

# Startup must remain hidden until the first rendered HTML frame.
patch_source = (root / "patch_webview_dark.py").read_text(encoding="utf-8")
if "src.replace(show_marker, 'applyBridgeTimerDarkBeforeShow(w.hwnd)', 1)" not in patch_source:
    errors.append("WebView startup patch must suppress the library's early ShowWindow")
if 'setTimeout(()=>{try{if(window.nativeReady)window.nativeReady()}catch(e){}},40)' not in html:
    errors.append("timer.html must signal nativeReady after startup render without relying on requestAnimationFrame")
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
    '#clock{font-family:Bahnschrift,Consolas,monospace;font-weight:650;font-size:clamp(110px,24vw,350px);line-height:.84;letter-spacing:.035em;white-space:nowrap}',
    '#msg{font-weight:950;font-size:clamp(26px,4.2vw,64px);line-height:1.05;min-height:1.1em;max-width:1300px}',
    '#submsg{font-weight:800;font-size:clamp(18px,2.3vw,36px);color:var(--muted);min-height:1em;max-width:1300px}',
]
for token in frozen_render_tokens:
    haystack = main if token == '--disable-lcd-text' else html
    if token not in haystack:
        print("Frozen rendering contract FAILED:", token)
        sys.exit(1)

for token in ['safeJSONRead(', 'safeJSONWrite(', 'backupKey(', 'normalizeImportedSettings(']:
    if token not in html:
        print("Storage safety regression FAILED:", token)
        sys.exit(1)

print("Frozen rendering contract OK")
