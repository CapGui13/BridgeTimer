"""Guard important BridgeTimer behavior, not obsolete pixel-perfect CSS."""
from pathlib import Path
import re

html=Path("timer.html").read_text(encoding="utf-8")
main=Path("main.go").read_text(encoding="utf-8")
for ident in ("mode","positions","startPosition","boards","boardMinutes","boardSeconds",
"boardProgressNotice","jumpAdvanceNotice","warnEnabled","jumpDisplaySecs","accent",
"background","menu","text","themeTest","themeTestGrid","saveColorsBtn","savedColorsBtn",
"themeTestBtn","randomColorsBtn","screenPreviewGallery"):
    assert len(re.findall(r'\bid="'+re.escape(ident)+r'"',html))==1, f"Missing/duplicate: {ident}"
for snippet in (
"function transitionAfterRound()","function tick()","function pause()",
"function start()","function clearObsoleteSessionRecovery()",
"function contrastRatio(",
"function randomColors()","function _rtt()","function _rspg()",
"function _usd()","function loadSavedColors()","window.nativeSetAwake",
"window.nativeFullscreen","function showTimer()",
"const jumpNoticeAt=Math.min(60,total)",
'if(!x||!Object.prototype.hasOwnProperty.call(x,"boardProgressNotice"))',
"sel.disabled=opts.length<=1","function hydrateNativeState()",
"nativeStateReadAll","nativeStateWrite","nativeStateDelete"):
    assert snippet in html, f"Missing HTML feature: {snippet}"
for snippet in ("--disable-lcd-text","SetThreadExecutionState","startLocalServer()",
"w.SetSize(defaultWindowWidth, defaultWindowHeight, webview.HintMin)",
"nativeStateFileName","nativeStateReadAll","nativeStateWrite",
"nativeStateDelete","errors.Is(err, syscall.EADDRINUSE)",
'net.JoinHostPort(host, "0")'):
    assert snippet in main, f"Missing Windows feature: {snippet}"
assert "const jumpNoticeAt=ds;" not in html
assert 'root.setProperty("--accentFg",hexRgb' not in html
assert "jumpSecs" in html and "jump<tours" in html
assert '#sessionDurationBox{display:none}' in html, "Pairs-only duration must be hidden by default"
assert '#sessionDurationBox.sessionDurationVisible{display:flex' in html, "Pairs mode must show duration"
assert '$("sessionDurationBox").classList.toggle("sessionDurationVisible",pairs)' in html, "Duration visibility must follow mode"
for forbidden in ('id="sessionRecovery"', 'id="restoreSession"', 'id="discardSession"',
                  "function offerSessionRecovery()", "function persistSessionSnapshot(",
                  "function clearSessionSnapshot()", "Séance interrompue"):
    assert forbidden not in html, f"Unwanted session recovery returned: {forbidden}"
assert 'clearObsoleteSessionRecovery();' in html, "Stale recovery data should be cleared"
assert 'function loadSavedColors(){savedColorPreset=safeJSONRead(COLORKEY,validColorPreset)||{accent:def.accent,background:def.background,menu:def.menu,text:def.text};_usc()}' in html, "Custom should start with OG Colors without replacing a saved preset"
assert 'function _scc(){read();savedColorPreset={accent:s.accent,background:s.background,menu:s.menu,text:s.text};safeJSONWrite(COLORKEY,savedColorPreset)' in html, "Custom save must still persist changes"
assert '<button id="saveColorsBtn" class="btn">Svg Custom</button>' in html, "Svg Custom must not be fixed to the primary button style"
assert '#saveColorsBtn{background:var(--bg);color:var(--text);border-color:var(--accent)}' in html, "Svg Custom must reflect current background/text/accent"
assert '<button id="randomColorsBtn" class="btn primary">Random</button>' in html, "Random must use the blue Timer button style"
assert 'root.setProperty("--bg",s.background)' in html and 'root.setProperty("--text",s.text||def.text)' in html, "Current theme CSS variables must update with live colors"
print("Current BridgeTimer regressions OK")
