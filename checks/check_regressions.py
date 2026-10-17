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
if "swpNoCopyBits" in main:
    missing.append("unexpected native pixel-discard behavior")
if "instantFullscreen" not in html:
    missing.append("instantaneous fullscreen CSS transition guard")
if "DWMWA_CLOAK" in main:
    missing.append("unexpected cloak")
preview_required=[
    '<option value="all">Tous</option><option value="prejump">',
    'id="screenPreviewGallery"',
    'function renderScreenPreviewGallery()',
    'function screenPreviewCardMarkup(kind)',
    'function previewEscapeHtml(value)',
    'screenPreviewGallery").classList.toggle("hidden",!isAll)',
    'setScreenPreview("all");',
    'screenPreviewGallery").classList.add("hidden");',
    'screenPreviewGallery{pointer-events:auto}',
]
for item in preview_required:
    if item not in html:
        missing.append("Preview gallery missing: "+item)
if missing:
    raise SystemExit("Preferred baseline regression: "+", ".join(missing))
print("Preferred EXE baseline and native fullscreen frame guard OK")
