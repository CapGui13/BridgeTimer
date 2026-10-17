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
# The exit control is confined to Settings, not the projected timer.
assert '<button id="screenPreviewBtn" class="btn" title="Tester les écrans du chronomètre">Écrans tests</button><button id="quitAppBtn" class="btn" type="button">Quitter</button>' in html, "Quitter must be inside fixed footer"
assert '#settings .actions #quitAppBtn{position:absolute;right:18px;top:50%;transform:translateY(-50%)' in html, "Quitter must be pinned to right side of bottom bar"
assert 'id="exitControlRow"' not in html, "Old detached quit row must not return"
assert html.index('id="quitAppBtn"') < html.index('id="jumpMsgOverlay"'), "Quitter must be confined to settings"
assert '#quitAppBtn.btn{background:#ff1744' in html, "Quitter must be brighter than Arrêter"
for token in ('id="exitConfirmOverlay"', 'id="exitYesBtn"', 'id="exitNoBtn"',
              'Voulez-vous vraiment fermer cet excellent logiciel, codé par Guillaume Capron et ChatGPT ? 😭',
              'Oui, NTM FDP, la FFB te own', "Non, c'était une erreur 🤗🤗🤗",
              'function openExitConfirm()', 'function closeExitConfirm()', 'async function confirmExit()',
              'if(exitConfirmIsOpen()){if(e.key==="Escape")'):
    assert token in html, "Exit confirmation regression: "+token
assert 'window.nativeExit()' in html, "Exit must call native Windows closing"
assert 'w.Bind("nativeExit"' in main and 'postMessageW.Call(hwnd, wmClose, 0, 0)' in main, "Graceful native WM_CLOSE binding missing"
assert 'if(e.key==="Escape"){e.preventDefault();e.stopPropagation();if(e.repeat)return;' in html, "Escape must be handled before other keyboard shortcuts"
assert 'document.body.classList.contains("fs")||!!document.fullscreenElement' in html, "Escape must leave fullscreen first"
assert 'else openExitConfirm();' in html, "Escape in windowed mode must open exit confirmation"
assert 'if(await window.nativeConsumeCloseRequest())openExitConfirm()' in html, "Windows title bar close must open the same dialog"
assert 'w.Bind("nativeConsumeCloseRequest"' in main, "Native close request handshake missing"
assert 'closePromptPending.Store(true)' in main and 'if msg == wmClose && !closeApproved.Load()' in main, "WM_CLOSE must be intercepted, not destroy window"
assert 'closeApproved.Store(true)' in main and 'postMessageW.Call(hwnd, wmClose, 0, 0)' in main, "Confirmed exit must bypass confirmation and close"
print("Current BridgeTimer regressions OK")
