"""Up-to-date static safeguards for the shipping BridgeTimer code.
Old checks referenced functions removed in previous refactors; those checks
were not part of CI, so they could give false confidence.
"""
from collections import Counter
from pathlib import Path
import re

html=Path("timer.html").read_text(encoding="utf8")
native=Path("main.go").read_text(encoding="utf8")
css=html.split("<style>",1)[1].split("</style>",1)[0]
markup=html.split("</style></head><body>",1)[1].split("<script>",1)[0]
ids=Counter(re.findall(r'\bid="([A-Za-z][A-Za-z0-9_-]*)"',markup))
for key in ("mode","positions","startPosition","boards","boardMinutes","boardSeconds",
 "warnEnabled","jumpDisplaySecs","accent","background","menu","text",
 "miniTimer","faithfulMiniFrame","recoveryOverlay","recoveryResume",
 "recoveryNew","settings","timer","fresh","quitAppBtn"):
 # faithfulMiniFrame is dynamically created by syncFaithfulMini().
 count=ids[key] if key!="faithfulMiniFrame" else html.count("f.id='faithfulMiniFrame'")
 assert count==1,(key,count)
for name in ("start","pause","tick","qe","zadvance","q4a","updateStage",
 "fc","showTimer","showSettings","syncFullscreenMiniWidth",
 "syncFaithfulMini","recoveryAutoSave","recoveryReadPending",
 "recoveryResume","syncTournamentAwake"):
 assert re.search(r'\b(?:async\s+)?function\s+'+name+r'\s*\(',html),name
for needle in ('#miniTimer.spView','body.fs.settingsLive #miniTimer.spView',
 'aspect-ratio:16/9!important',
 'bottom:0!important;top:auto!important',
 'body.fs #settings .wrap>.head',
 'padding-bottom:var(--settings-fullscreen-bottom-padding,100px)!important',
 'recoveryAutoSave(true)','const RECOVERY_KEY="bridgeTimerV2.activeSession"'):
 assert needle in html,needle
for needle in ('runtime.LockOSThread()', 'newAwakeController()',
 'setThreadExecutionState.Call(flags)','awakeControl.close()',
 'os.Rename(tmpPath, path)', 'nativeStateReadAll',
 'w.SetSize(defaultWindowWidth, defaultWindowHeight, webview.HintMin)'):
 assert needle in native,needle
# CSS cleanup is intentionally small. Each superseded declaration still
# exists ONCE, in the later rule. A global stylesheet rewrite is forbidden.
for rule in (
 'body.settingsLive #settings .actions{grid-template-columns:minmax(0,1fr) 110px;grid-template-rows:140px auto;min-height:210px;padding:8px 12px;row-gap:6px}',
 'body.settingsLive #settings .actions .settingsActionButtons{grid-column:1/-1;grid-row:2;justify-self:center}',
 'body.settingsLive #settings .actions #quitAppBtn{grid-column:2;grid-row:1;justify-self:end}',
 'body.settingsLive #settings .actions .settingsActionButtons{flex-wrap:wrap}',
 '#colorMenuOverlay .personalizeLayout{grid-template-columns:1fr;gap:20px}'):
 assert css.count(rule)==1,(rule,css.count(rule))
print(f"Static contracts OK: {len(ids)} HTML ids, current API, crash recovery, anti-sleep, five CSS no-op eliminations")
