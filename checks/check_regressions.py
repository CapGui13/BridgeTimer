from pathlib import Path
import json
import re
import sys

root = Path(__file__).resolve().parents[1]
html = (root / "timer.html").read_text(encoding="utf-8")
main = (root / "main.go").read_text(encoding="utf-8")
vi = json.loads((root / "versioninfo.json").read_text(encoding="utf-8"))

version = vi["StringFileInfo"]["ProductVersion"]

required_html = [
    f"WebView2 {version}",
    '#clock{font-variant-numeric:tabular-nums;font-weight:1000;font-size:clamp(110px,24vw,350px);line-height:.84;letter-spacing:-.07em;white-space:nowrap}',
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
]

required_main = [
    f'appVersion = "{version}"',
    '--disable-lcd-text',
    'SetThreadExecutionState',
    'MoveFileExW',
    'window.json',
    'window state: recovered from backup',
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

if errors:
    print("BridgeTimer regression check FAILED:")
    for e in errors:
        print(" -", e)
    sys.exit(1)

print(f"BridgeTimer regression check OK — version {version}")
