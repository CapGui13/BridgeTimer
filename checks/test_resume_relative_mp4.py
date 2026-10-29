"""User acceptance: MP4 Reprise à HH:MM OU [1..99] minutes after match end.

Use real Edge browser, inspect actual editable fields, both timer and settings,
and preserve PAIRS behavior and the 1600x900 visual contract.
"""
from pathlib import Path
import os, shutil
from playwright.sync_api import sync_playwright

src=Path(__file__).resolve().parents[1].joinpath("timer.html").read_text(encoding="utf-8")
src=src.replace("localStorage","resumeTestStorage").replace("</style></head><body>",
 """</style><script>const resumeTestStorage={d:{},getItem(k){return this.d[k]??null},
 setItem(k,v){this.d[k]=v},removeItem(k){delete this.d[k]}};</script></head><body>""",1)

def get(page):
 return page.evaluate("""()=>({
   time:document.querySelector("#resumeTime").value,
   delay:document.querySelector("#resumeDelayMinutes").value,
   saved:s.resumeDelayMinutes,
   endLabel:document.querySelector("#finishResume").textContent,
   hidden:document.querySelector("#resumeDelayChoice").classList.contains("hidden"),
   valid:document.querySelector("#resumeDelayMinutes").validity.valid,
   required:document.querySelector("#resumeTime").required,
   hourValid:document.querySelector("#resumeTime").validity.valid,
   unit:document.querySelector("#resumeDelayChoice .unitField .unit")?.textContent,
   nested:document.querySelector("#resumeDelayMinutes").parentElement.classList.contains("unitField"),
   unitGap:getComputedStyle(document.querySelector("#resumeDelayChoice .unitField")).gap,
   mainGap:getComputedStyle(document.querySelector(".tournamentCard #timingLayout .unitField")).gap
 })""")
def insert(page,x):
 page.locator("#resumeDelayMinutes").fill(x)
 return get(page)
with sync_playwright() as pw:
 if os.name=="nt":browser=pw.chromium.launch(channel="msedge",headless=True)
 else:browser=pw.chromium.launch(executable_path=shutil.which("chromium") or shutil.which("chromium-browser"),args=["--no-sandbox"],headless=True)
 n=0
 for width,height in ((812,456),(960,540),(1280,720),(1600,900),(1920,1080)):
  page=browser.new_page(viewport={"width":width,"height":height})
  page.set_content(src,wait_until="domcontentloaded")
  page.wait_for_function("typeof recoveryArmed!=='undefined' && recoveryArmed")
  # Force the current match's actual end to be at exactly 13:00.
  page.evaluate("""()=>{
    Date.now=()=>new Date(2026,9,29,13,0,0).getTime();
    document.querySelector("#mode").value="4";
    s.mode="4";s.resumeTime="";s.resumeDelayMinutes=0;
    st.started=true;st.running=false;st.phase="roundEnd";
    st.roundEndSince=performance.now();st.endAt=null;st.remaining=0;
    showSettings();
  }""")
  assert not get(page)["hidden"],(width,"MP4 relative field should be visible")
  d=insert(page,"15")
  assert d["time"]=="" and d["saved"]==15,(width,d)
  assert d["delay"]=="15" and d["endLabel"]=="REPRISE À 13:15",(width,d)
  assert not d["required"] and d["hourValid"],(width,"blank HH:MM should not be invalid",d)
  assert d["unit"]=="M" and d["nested"] and d["unitGap"]==d["mainGap"],(width,"M unit style",d)
  n+=1
  # At midnight, 99 minutes must wrap to next day without DST/UTC ambiguity.
  page.evaluate("""()=>{
    Date.now=()=>new Date(2026,9,29,23,50,0).getTime();
    st.roundEndSince=performance.now();
  }""")
  d=insert(page,"99")
  assert d["time"]=="" and d["saved"]==99 and d["endLabel"]=="REPRISE À 01:29",(width,"wrap",d)
  n+=1
  # Direct time has precedence and cancels the relative option.
  page.locator("#resumeTime").fill("14:10")
  d=get(page)
  assert d["time"]=="14:10" and d["delay"]=="" and d["saved"]==0 and d["endLabel"]=="REPRISE À 14:10" and d["required"],(width,"manual",d)
  n+=1
  # A number typed while the match is running uses projected match end.
  page.evaluate("""()=>{
    Date.now=()=>new Date(2026,9,29,12,0,0).getTime();
    st.started=true;st.phase="round";st.running=false;st.remaining=3600;
  }""")
  d=insert(page,"15")
  assert d["time"]=="" and d["endLabel"]=="REPRISE À 13:15",(width,"paused end",d)
  n+=1
  # Different configured time reflects the current round remaining, not
  # number of rounds or the clock when the first minute was entered.
  page.evaluate("""()=>{
    st.remaining=1800;render();
  }""")
  d=get(page)
  assert d["time"]=="" and d["endLabel"]=="REPRISE À 12:45",(width,"remaining change",d)
  n+=1
  # Returning from Settings and rendering after end gives real finish
  # time + delay, not "now + duration".
  page.evaluate("""()=>{
    st.phase="roundEnd";st.roundEndSince=performance.now();
    Date.now=()=>new Date(2026,9,29,13,0,0).getTime();render();
  }""")
  assert get(page)["time"]=="" and get(page)["endLabel"]=="REPRISE À 13:15",(width,"match end",get(page))
  n+=1
  # Clearing the relative choice does not silently copy the calculated
  # restart time into the first field: both become empty.
  d=insert(page,"")
  assert d["saved"]==0 and d["time"]=="" and d["endLabel"]=="REPRISE À --:--" and d["required"],(width,"clear",d)
  n+=1
  # An invalid 0, 100 or text is not accepted as a delay.
  for bad in ("0","abc"):
   d=insert(page,bad)
   assert d["time"]=="" and d["saved"]==0,(width,bad,d)
  page.locator("#resumeDelayMinutes").blur()
  d=get(page)
  assert d["delay"]=="" and d["time"]=="" and d["required"],(width,"invalid blur",d)
  n+=1
  # An explicitly entered HH:MM must be blanked as soon as the
  # alternative minutes are typed; never repopulate via a redraw.
  page.locator("#resumeTime").fill("18:20")
  d=insert(page,"5")
  assert d["time"]=="" and d["delay"]=="5" and not d["required"],(width,"exclusive override",d)
  page.evaluate("render();fill();render();")
  d=get(page)
  assert d["time"]=="" and d["saved"]==5,(width,"exclusive persists after render/fill",d)
  page.locator("#resumeDelayMinutes").fill("")
  assert get(page)["time"]=="" and get(page)["saved"]==0
  n+=1
  # The Settings label now ends at virtually the same distance from its
  # time box as Temps par match ends from its first numeric box.
  gap=page.evaluate("""()=>{
     const rightOfText=sel=>{
       const l=document.querySelector(sel);const range=document.createRange();
       range.selectNodeContents(l);return range.getBoundingClientRect().right;
     };
     return {
       match:document.querySelector("#hours").getBoundingClientRect().left-
           rightOfText(".durationSetting>label .mp4TimeTitle"),
       reprise:document.querySelector("#resumeTime").getBoundingClientRect().left-
           rightOfText(".resumeTimeOption>label"),
       vis:getComputedStyle(document.querySelector(".resumeTimeOption")).display
     };
   }""")
  assert abs(gap["match"]-gap["reprise"])<6,(width,"label gaps",gap)
  n+=1
  # PAIRS must never show the relative option, but keep the existing manual
  # time field and its input handler available.
  page.evaluate("""()=>{
    document.querySelector("#mode").value="2";s.mode="2";_upu();read();render();
  }""")
  assert get(page)["hidden"] and get(page)["required"],(width,"pairs should hide relative option")
  page.locator("#resumeTime").fill("17:42")
  assert get(page)["time"]=="17:42",(width,"pairs manual",get(page))
  n+=1
  # Saved settings intentionally clear the session-specific resume time and
  # relative offset when launching Bridge Timer again.
  vals=page.evaluate("""()=>{
    const raw=resumeTestStorage.getItem(KEY);return JSON.parse(raw);
  }""")
  assert vals["resumeTime"]=="" and vals["resumeDelayMinutes"]==0,(width,"session persistence",vals)
  n+=1
  page.close()
 browser.close()
print(f"MP4 relative restart: {n} browser acceptance checks passed (exclusive HH:MM and M unit)")
