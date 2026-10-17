"""Guard important BridgeTimer behavior, not obsolete pixel-perfect CSS."""
from pathlib import Path
import re

html=Path("timer.html").read_text(encoding="utf-8")
main=Path("main.go").read_text(encoding="utf-8")
for ident in ("mode","positions","startPosition","boards","boardMinutes","boardSeconds",
"boardProgressNotice","jumpAdvanceNotice","warnEnabled","jumpDisplaySecs","accent",
"background","menu","text","themeTest","themeTestGrid","sessionRecovery",
"restoreSession","discardSession","saveColorsBtn","savedColorsBtn",
"themeTestBtn","randomColorsBtn","screenPreviewGallery"):
    assert len(re.findall(r'\bid="'+re.escape(ident)+r'"',html))==1, f"Missing/duplicate: {ident}"
for snippet in (
"function transitionAfterRound()","function tick()","function pause()",
"function start()","function persistSessionSnapshot(",
"function offerSessionRecovery()","function contrastRatio(",
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
print("Current BridgeTimer regressions OK")
