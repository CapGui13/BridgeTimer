from pathlib import Path

html = Path("variants/BridgeTimer_MSG_bandeau.html").read_text(encoding="utf-8")
required = [
    'body.fsTransition #timer{opacity:.82;',
    'body.fsTransition.fsReveal #timer{opacity:1;',
    '@media(prefers-reduced-motion:reduce)',
    'steady>=2||frames++>=12',
    'C=null;fc();requestAnimationFrame(',
    'if(token===fullscreenTransitionId)document.body.classList.remove("fsTransition","fsReveal")',
    'if(!e.repeat)fs()',
    'if(window.nativeFullscreen)',
    'document.fullscreenElement?await document.exitFullscreen():await document.documentElement.requestFullscreen()',
    'function showTempMessage(){if(!st.started||st.phase==="ended")return;if(tempMessageActive()){clearTempMessage();return render()}',
    'st.started=true;start();showTimer()',
    'body:not(.fs) #timer #fsBtn{width:auto',
]
for token in required:
    assert token in html, f"Missing fullscreen or preserved feature: {token}"
for obsolete in (
    'opacity:.12;transform:scale(.985)',
    'await new Promise(r=>setTimeout(r,190))',
    'setTimeout(()=>document.body.classList.remove("fsTransition","fsReveal"),330)',
):
    assert obsolete not in html, f"Obsolete fullscreen transition reintroduced: {obsolete}"
print("Fullscreen transition checks passed")
