from pathlib import Path

html = Path("variants/BridgeTimer_MSG_bandeau.html").read_text(encoding="utf-8")
required = [
    "function syncFullscreenUI(on)",
    "function fitFullscreenOnce()",
    "async function fs(){if(fullscreenInFlight)return;",
    'document.addEventListener("fullscreenchange",()=>syncFullscreenUI(!!document.fullscreenElement))',
    "if(!e.repeat)fs()",
    "if(window.nativeFullscreen)",
    "document.fullscreenElement?await document.exitFullscreen():await document.documentElement.requestFullscreen()",
    'function showTempMessage(){if(!st.started||st.phase==="ended")return;if(tempMessageActive()){clearTempMessage();return render()}',
    "st.started=true;start();showTimer()",
    "body:not(.fs) #timer #fsBtn{width:auto",
]
for token in required:
    assert token in html, f"Missing fullscreen or preserved feature: {token}"
for obsolete in (
    "fsTransition",
    "fsReveal",
    "fullscreenTransitionId",
    "await new Promise(r=>setTimeout(r,190))",
    'setTimeout(()=>document.body.classList.remove("fsTransition"',
    "opacity:.82",
    "opacity:.12;transform:scale(.985)",
    "transform:scale(.985)",
):
    assert obsolete not in html, f"Obsolete or artificial fullscreen animation reintroduced: {obsolete}"
print("Fullscreen direct transition checks passed")
