from pathlib import Path
import re

root=Path(__file__).resolve().parents[1]
html=(root/"timer.html").read_text(encoding="utf-8")
main=(root/"main.go").read_text(encoding="utf-8")
required=[
'function syncFullscreenUI(on)',
'function fitFullscreenOnce()',
'async function fs()',
'id="sendTempBtn"',
'function fc()',
'function render()',
]
missing=[x for x in required if x not in html]
if "First move the existing frame to the monitor bounds." not in main:
    missing.append("native resize-before-frame-change")
if "DWMWA_CLOAK" in main:
    missing.append("unexpected cloak")
if missing:
    raise SystemExit("Preferred baseline regression: "+", ".join(missing))
print("Preferred EXE baseline and native fullscreen frame guard OK")
