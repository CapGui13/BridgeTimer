"""Bridge Timer keyboard guard E2E on the delivered JS (Edge / WebView2 engine).

Press actual keys, and dispatch KeyboardEvent(repeat=true) for held-key
conditions. Never modify timer.html during tests.
"""
from pathlib import Path
import os,shutil
from playwright.sync_api import sync_playwright

html=Path("timer.html").read_text(encoding="utf8")
html=html.replace("localStorage","keyAuditStorage").replace(
 "</style></head><body>",
 """</style><script>const keyAuditStorage={d:{},getItem(k){return this.d[k]??null},
 setItem(k,v){this.d[k]=v},removeItem(k){delete this.d[k]}};</script></head><body>""",1)

def repeat(page,key,code=None,**modifiers):
 return page.evaluate("""({key,code,modifiers})=>{
  const ev=new KeyboardEvent("keydown",{key,code:code||key,repeat:true,
   bubbles:true,cancelable:true,...modifiers});
  document.activeElement.dispatchEvent(ev);
  return ev.defaultPrevented;
 }""",{"key":key,"code":code,"modifiers":modifiers})

def verify():
 with sync_playwright() as pw:
  if os.name=="nt":browser=pw.chromium.launch(channel="msedge",headless=True)
  else:browser=pw.chromium.launch(executable_path=shutil.which("chromium") or shutil.which("chromium-browser"),
                                 args=["--no-sandbox"],headless=True)
  page=browser.new_page(viewport={"width":1260,"height":720})
  errors=[]
  page.on("pageerror",lambda e:errors.append(str(e)))
  page.set_content(html,wait_until="domcontentloaded")
  page.wait_for_function("typeof recoveryArmed !== 'undefined' && recoveryArmed")
  page.evaluate("""()=>{
   Object.assign(s,{mode:"4",positions:5,boards:8,hours:0,minutes:15,seconds:0,
      between:0,sound:false,quickMessage:"Test message clavier"});
   fill();st.started=true;q4a(2,false);st.running=false;st.remaining=900;st.endAt=null;
   showTimer();
   document.body.tabIndex=-1;document.body.focus();
   window.__hits={next:0,restart:0};
   const originalNext=next,originalRestart=q48;
   next=function(...args){__hits.next++;return originalNext(...args)};
   q48=function(...args){__hits.restart++;return originalRestart(...args)};
  }""")

  # Space: one press = one toggle. A held key must NOT generate extra toggles.
  page.keyboard.press("Space")
  assert page.evaluate("st.running"),"Space must start a paused timer"
  assert repeat(page," ","Space"),"Repeated Space should be prevented"
  assert page.evaluate("st.running"),"Repeated Space unexpectedly paused clock"
  page.keyboard.press("Space")
  assert not page.evaluate("st.running"),"Second Space must pause clock"

  # F7/F8 with and without key repeat, and aliases - / +.
  page.evaluate("st.remaining=900;st.endAt=null")
  page.keyboard.press("F8")
  assert round(page.evaluate("st.remaining"))==960
  assert repeat(page,"F8")
  assert round(page.evaluate("st.remaining"))==960,"Held F8 modified timer"
  page.keyboard.press("F7")
  assert round(page.evaluate("st.remaining"))==900
  assert repeat(page,"F7")
  assert round(page.evaluate("st.remaining"))==900,"Held F7 modified timer"

  # Position/round and restart are one-shot, especially after a long hold.
  page.keyboard.press("ArrowRight")
  assert page.evaluate("st.pos")==3
  assert repeat(page,"ArrowRight")
  assert page.evaluate("st.pos")==3,"Held ArrowRight skipped another round"
  page.keyboard.press("r")
  assert page.evaluate("__hits.restart")==1,"R must restart current position once"
  assert repeat(page,"r")
  assert page.evaluate("__hits.restart")==1,"Held R restarted twice"
  page.evaluate("pause()")

  # M opens a text editor. Typing R/F/space/plus/arrows inside it cannot
  # restart, fullscreen, pause or change the tour. Esc closes the editor.
  page.keyboard.press("m")
  assert page.evaluate("!document.getElementById('tempMessageOverlay').classList.contains('hidden')")
  counts=page.evaluate("({hits:{...__hits},pos:st.pos,remaining:st.remaining,running:st.running})")
  page.locator("#tempMessageInput").fill("R F + - M")
  page.keyboard.press("Space")
  page.keyboard.press("ArrowRight")
  page.keyboard.press("F7")
  page.keyboard.press("F8")
  after=page.evaluate("({hits:{...__hits},pos:st.pos,remaining:st.remaining,running:st.running})")
  assert counts==after,("Editing text launched a timer shortcut",counts,after)
  page.keyboard.press("Escape")
  assert page.evaluate("document.getElementById('tempMessageOverlay').classList.contains('hidden')")

  # Space on a focused native button should click that button, not PAUSE.
  page.evaluate("""()=>{
   const b=document.createElement("button");b.id="keyboardDemo";
   b.textContent="keyboard test";window.__buttonClicks=0;
   b.onclick=()=>__buttonClicks++;document.body.append(b);b.focus();
  }""")
  paused=page.evaluate("st.running")
  page.keyboard.press("Space")
  assert page.evaluate("__buttonClicks")==1,"Space did not activate native focused button"
  assert page.evaluate("st.running")==paused,"Space on button paused timer"

  # Ctrl/Alt/Meta combos pass to the OS/browser and must never restart.
  page.evaluate("document.body.focus()")
  calls=page.evaluate("__hits.restart")
  for opts in [{"key":"r","ctrlKey":True},{"key":"r","altKey":True},{"key":"m","metaKey":True}]:
   blocked=page.evaluate("""o=>{
     const e=new KeyboardEvent("keydown",{...o,bubbles:true,cancelable:true});
     document.dispatchEvent(e);return e.defaultPrevented;
   }""",opts)
   assert not blocked,("OS modifier commande was hijacked",opts)
  assert page.evaluate("__hits.restart")==calls

  # F9 remains available, including from an editing control, but no
  # held-F9 oscillation between Settings and Timer.
  page.keyboard.press("F9")
  assert page.evaluate("!document.getElementById('settings').classList.contains('hidden')")
  page.locator("#quickMessage").focus()
  assert repeat(page,"F9")
  assert page.evaluate("!document.getElementById('settings').classList.contains('hidden')")
  page.keyboard.press("F9")
  assert page.evaluate("document.getElementById('settings').classList.contains('hidden')")
  page.evaluate("document.body.focus()")

  # Each modal must swallow timer keyboard actions:
  # exit confirmation, recovery choice, diagnostics, theme tests, between-turn.
  def modal_inert(label,setup,cleanup):
   page.evaluate(setup)
   before=page.evaluate("({pos:st.pos,running:st.running,remaining:st.remaining,hits:{...__hits}})")
   # Dispatch events rather than keyboard.press("Space") on the modal's
   # focused action button: Space is supposed to CLICK that button, not
   # be silently swallowed by the dialog.
   page.evaluate("""keys=>{
    for(const key of keys){
     const ev=new KeyboardEvent("keydown",{key,bubbles:true,cancelable:true});
     document.dispatchEvent(ev);
    }
   }""",[" ","ArrowRight","r","F7","F8","m","F9"])
   after=page.evaluate("({pos:st.pos,running:st.running,remaining:st.remaining,hits:{...__hits}})")
   assert before==after,(label,before,after)
   page.evaluate(cleanup)

  modal_inert("exit-confirmation","q34()","q21()")
  modal_inert("recovery-confirmation","""()=>{
   recoveryDecisionOpen=true;
   document.getElementById("recoveryOverlay").classList.remove("hidden");
   document.getElementById("recoveryResume").focus();
  }""","""()=>{
   recoveryDecisionOpen=false;
   document.getElementById("recoveryOverlay").classList.add("hidden");
   document.body.focus();
  }""")
  modal_inert("diagnostic","document.getElementById('diagOverlay').classList.add('on')",
   "document.getElementById('diagOverlay').classList.remove('on')")
  modal_inert("theme-test","document.getElementById('themeTest').classList.remove('hidden')",
   "document.getElementById('themeTest').classList.add('hidden')")
  modal_inert("between-round dialog",
   "document.getElementById('betweenMsgOverlay').classList.remove('hidden')",
   "document.getElementById('betweenMsgOverlay').classList.add('hidden')")
  page.evaluate("document.getElementById('betweenMsgOverlay').classList.remove('hidden')")
  page.keyboard.press("Escape")
  assert page.evaluate("document.getElementById('betweenMsgOverlay').classList.contains('hidden')")
  assert page.evaluate("document.getElementById('settings').classList.contains('hidden')")

  # Diagnostic shortcut remains explicit, and repeated Ctrl+Shift+D only
  # requests one dialog (no duplicate repeated actions).
  page.evaluate("window.__diagCalls=0;window.__diagStacks=[];q2b=()=>{__diagCalls++;__diagStacks.push(new Error().stack)}")
  # Headless Edge can reserve Ctrl+Shift+D for its own bookmark command
  # before delivering it to the page; dispatch explicitly to test the app.
  page.evaluate("""()=>{
   document.dispatchEvent(new KeyboardEvent("keydown",
    {key:"d",ctrlKey:true,shiftKey:true,bubbles:true,cancelable:true}));
  }""")
  diag=page.evaluate("""()=>{
   return {calls:__diagCalls,stacks:__diagStacks,exit:q1d(),recovery:recoveryDecisionOpen,
    recoveryHidden:document.getElementById('recoveryOverlay').classList.contains('hidden'),
    between:betweenMsgIsOpen(),resume:resumeEditorOpen(),
    tempHidden:document.getElementById('tempMessageOverlay').classList.contains('hidden'),
    jump:q3b(),color:colorMenuOpen(),
    themeHidden:document.getElementById('themeTest').classList.contains('hidden'),
    diagOpen:document.getElementById('diagOverlay').classList.contains('on'),
    screenPreview:!!_sps,active:document.activeElement?.id};
  }""")
  assert diag["calls"]==1,diag
  assert repeat(page,"d",ctrlKey=True,shiftKey=True)
  assert page.evaluate("__diagCalls")==1
  # Screen-test gallery blocks timer commands even on key repeat.
  page.evaluate("_sps={};document.body.focus()")
  before=page.evaluate("st.pos")
  page.keyboard.press("ArrowRight")
  assert page.evaluate("st.pos")==before
  page.evaluate("_sps=null")

  assert not errors,errors
  page.close();browser.close()
 print("Keyboard E2E OK: 7 one-shot keys, editing, browser modifiers, 5 modals, focused buttons, F9, diagnostics and gallery")

verify()
