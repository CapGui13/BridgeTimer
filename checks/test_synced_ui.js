// Regression tests for the production HTML embedded in the official Windows executable.
// The historical tests are retained in the repository but refer to earlier internals.
const fs = require('node:fs');
const assert = require('node:assert/strict');
const vm = require('node:vm');
const html = fs.readFileSync('timer.html', 'utf8');
const scripts = [...html.matchAll(/<script\b[^>]*>([\s\S]*?)<\/script>/gi)];
assert.ok(scripts.length, 'The embedded UI must include JavaScript');
for (const [, src] of scripts) new vm.Script(src, {filename:'BridgeTimer:inline.js'});
const ids = [...html.matchAll(/\bid="([^"]+)"/g)].map(x=>x[1]);
const counts = new Map(); for(const id of ids) counts.set(id,(counts.get(id)||0)+1);
for(const id of ['settings','timer','clock','status','pauseOverlay','pause','round','sps','spg','miniTimer','tempMessageInput','messageBtn','quitAppBtn'])
  assert.equal(counts.get(id),1,`Missing/duplicate production UI element: ${id}`);
for(const [id,count] of counts) assert.equal(count,1,`Duplicate HTML id: ${id}`);
for(const snippet of ['function start()','function pause()','function tick()','function zadvance(','function render()','function showSettings(','function showTimer(','function q15(','function q34()','window.nativeExit','nativeConsumeCloseRequest'])
  assert.ok(html.includes(snippet),`Lost critical timer functionality: ${snippet}`);
assert.ok(html.includes('syncFaithfulMini('),'Preview must stay synchronized with live timer');
assert.ok(html.includes('backdrop-filter:blur(2px)'),'Missing pause visual effect');
assert.ok(html.includes('Appuyez sur Espace ou sur Reprendre'),'Missing pause instruction');
assert.ok(html.includes('Vous êtes censés attaquer la donne'),'Missing board attack notice');
assert.ok(html.includes('Vous êtes censés jouer la donne'),'Missing board play notice');
assert.ok(html.includes('FIN DU TOUR') && html.includes('FIN DE LA SÉANCE'),'Missing ending screens');
assert.ok(html.includes('user-select:none'),'UI text selection must be disabled outside inputs');
const script = scripts.map(s=>s[1]).join('\n');
const match=script.match(/function q15\(wallNow,remaining\)\{[^}]+\}/);
assert.ok(match,'Aligned countdown calculation was renamed or removed');
const sandbox={Math}; vm.runInNewContext(match[0],sandbox);
assert.equal(sandbox.q15(0,60),60000);
assert.equal(sandbox.q15(250,60),59750);
assert.equal(sandbox.q15(0,-20),0);
// Lock the October 23 footer/restart/overtime contracts.
const stopPos=html.indexOf('id="stopTimer"'),launchPos=html.indexOf('id="fresh"');
assert.ok(stopPos>0&&launchPos>stopPos,'Arrêter must precede Lancer/Timer in the footer');
assert.ok(html.includes('#settings #stopTimer.hidden{display:inline-flex!important;visibility:hidden!important'),'The hidden Arrêter slot must remain reserved');
assert.ok(html.includes('function q48(){')&&html.includes('st.syncDisplayCeiling=0;start();q4c(prev'),'Recommencer must restart immediately');
assert.ok(!html.includes('textContent="+"+fmt('),'End-of-round overrun must have no plus prefix');
assert.ok(html.includes('st.phase==="roundEnd"||st.phase==="ended"'),'Both modes must keep a terminal overtime display');
// Regression guarantees: Message publishes only after Valider;
// advancing from the MP4 end screen restarts immediately; overtime controls are grey.
assert.ok(!html.includes('id="sendTempBtn"'),'The obsolete instant-send M button must not return');
assert.ok(html.includes('$("messageBtn").onclick=()=>$("tempMessageOverlay").classList.contains("hidden")?q2c():q20()'),'Message toggle must remain');
assert.ok(html.includes('$("tempMessageForm").onsubmit=q1e'),'Only form submit can publish message');
assert.ok(html.includes('q20();q23();q2f()'),'Valider must publish the new message');
assert.ok(html.includes('q4a(st.pos+1,false);start();q4c(prev);return'),'MP4 next position must auto-start');
for (const selector of ['#timer.roundEndState #minus:disabled','#timer.roundEndState #plus:disabled','#timer.pairEndState #minus:disabled','#timer.pairEndState #plus:disabled'])
  assert.ok(html.includes(selector),'Overtime disabled control styling missing: '+selector);


// 2026-10-23 jump/reprise/position-specific regression checks.
for (const id of ['resumeTime','resumeBtn','resumeOverlay','resumeForm','resumeInput','resumeCancel','resumeConfirm','finishResume','prev'])
  assert.equal(counts.get(id),1,'Missing or duplicated new control '+id);
assert.ok(html.includes('function adjustmentStep(){return st.phase==="jump"?15:60}'),'Jump adjustments must be ±15 seconds');
assert.ok(html.includes('zshift(-adjustmentStep())')&&html.includes('zshift(adjustmentStep())'),'Buttons and shortcuts must use phase-adjusted increment');
assert.ok(html.includes('function previousPosition()')&&html.includes('s.mode!=="2"'),'Previous position is for pairs only');
assert.ok(html.includes('s.mode==="2"?"Pos. suiv.":"Tour suivant"'),'Round navigation labels must depend on format');
assert.ok(html.includes('s.mode==="2"?"Pos. suiv.":"Tour suivant"'),'Tour suivant MP4 label missing');
assert.ok(html.includes('REPRISE À ')&&html.includes('color:#ff202d'),'Resume announcement must be red');
assert.ok(html.includes('resumeTime:$("resumeTime").value'),'Resume time not bound to settings');
assert.ok(html.includes('function commitResumeTime(e)')&&html.includes('function openResumeEditor()'),'Live resume time editing missing');

// Restart-time announcement must be as prominent as the finish headline in both modes.
assert.ok(html.includes('#finishOverlay .finishResume{position:absolute;top:calc(58.8% + clamp(112px,calc(var(--timer-vw) * 13.8),220px))'),'Large MP4 restart announcement missing');
assert.ok(html.includes('font-size:clamp(60px,calc(var(--timer-vw) * 9),170px);line-height:1.06;font-weight:1000;color:#ff202d'),'MP4 red line must match headline scale');
assert.ok(html.includes('.finishBig.pairFinish~.finishResume{top:calc(58.8% + clamp(112px,calc(var(--timer-vw) * 13.8),220px));font-size:clamp(60px,calc(var(--timer-vw) * 9),170px)'),'Pairs restart line must match MP4 headline scale');

// Tournoi duration layout: common right-hand column and no height jump between formats.
for(const id of ['timingLayout','hours','boardMinutes','boardSeconds','minutes','seconds','sessionDurationBox','resumeTime','betweenField'])
  assert.equal(counts.get(id),1,'Lost/doubled tournament field: '+id);
assert.ok(html.includes('class="timeEntry durationSetting"')&&html.includes('class="timeEntry boardTimeSetting"'),'Duration form groups missing');
assert.ok(html.includes('<span class="mp4TimeTitle">Temps par match</span>'),'MP4 time heading must be Temps par match');
assert.ok(html.includes('<span class="tppTimeTitle">Temps par tour</span>'),'TPP time heading must remain Temps par tour');
assert.ok(html.includes('classList.toggle("pairsTiming",pairs)'),'Mode switching must synchronize duration layout');
assert.ok(html.includes('grid-template-rows:38px 38px;gap:5px 16px;min-height:81px'),'MP4 must reserve the second duration row');
assert.ok(html.includes('grid-column:2!important;grid-row:2!important'),'TPP session duration must occupy lower right row');
assert.ok(html.includes('.boardOptionsRow .resumeTimeOption{justify-self:start;display:flex'),'Reprise must remain underneath the right duration column');

// MP4 blank first row left; Temps par donne aligns vertically with TPP's second row.
assert.ok(html.includes('.tournamentCard #timingLayout .boardTimeSetting{grid-column:1;grid-row:2}'),'Temps par donne must occupy row 2');
assert.ok(!html.includes('.tournamentCard #timingLayout .boardTimeSetting{grid-column:1;grid-row:1}'),'Old MP4 board row cannot return');
assert.ok(html.includes('.tournamentCard #timingLayout .durationSetting{grid-column:2;grid-row:1}'),'MP4 match duration must stay top right');
assert.ok(html.includes('.tournamentCard #timingLayout .durationSetting{grid-column:1;grid-row:1}'),'Narrow MP4 duration must stay on first row');
assert.ok(html.includes('grid-template-rows:38px 38px;gap:5px 16px;min-height:81px'),'Reserved spacer row and common heights must remain');
// October 24: no time-picker icon in settings, and resume time must be saved immediately.
assert.ok(html.includes('#resumeTime::-webkit-calendar-picker-indicator{display:none!important'),'Reprise settings field must have no clickable clock icon');
assert.ok(html.includes('function saveResumeFromSettings(allowEmpty=false)'),'Immediate resume-time persistence missing');
assert.ok(html.includes('$("resumeTime").oninput=()=>saveResumeFromSettings(false)'),'Changing the hour must save as soon as the value is valid');
assert.ok(html.includes('$("resumeTime").onchange=()=>saveResumeFromSettings(true)'),'Clearing the hour must also persist');
assert.ok(html.includes('const written=await window.nativeStateWrite(KEY,JSON.stringify(s))'),'Windows closing must await native preferences write');
assert.ok(html.includes('id="resumeTime" type="time"'),'The HH:MM input type must stay unchanged');
assert.ok(html.includes('id="resumeInput" type="time"'),'Timer Reprise editor must stay unchanged');

// TPP duration positions and compact hour field.
assert.ok(html.includes('.tournamentCard #timingLayout.pairsTiming .betweenTimeSetting{grid-column:2;grid-row:1;display:flex}'),'TPP between-round time must be upper-right');
assert.ok(html.includes('.tournamentCard #timingLayout.pairsTiming #sessionDurationBox.sessionDurationVisible{display:flex;grid-column:2!important;grid-row:2!important'),'TPP session duration must be lower-right');
assert.ok(html.includes('.tournamentCard #timingLayout.pairsTiming .betweenTimeSetting{grid-column:1;grid-row:3}'),'Small-window TPP between-round time must be row three');
assert.ok(html.includes('.tournamentCard #timingLayout.pairsTiming #sessionDurationBox.sessionDurationVisible{grid-column:1!important;grid-row:4!important}'),'Small-window TPP session duration must be row four');
assert.ok(html.includes('#resumeTime{box-sizing:border-box;width:64px;min-width:64px;max-width:64px;flex:0 0 64px;height:33px;font-weight:700;padding-inline:4px!important}'),'Reprise should have a genuinely narrow HH:MM field');
// Both end displays use equal headline and restart font-size/placement.
assert.ok(html.includes('#finishOverlay .finishBig.pairFinish{top:58.8%;font-size:clamp(52px,calc(var(--timer-vw) * 8),154px)}'),'Pairs green headline must match MP4');
assert.ok(html.includes('.finishBig.pairFinish~.finishResume{top:calc(58.8% + clamp(112px,calc(var(--timer-vw) * 13.8),220px));font-size:clamp(60px,calc(var(--timer-vw) * 9),170px)}'),'Pairs red announcement must match MP4');
assert.ok(html.includes('#resumeTime::-webkit-datetime-edit-ampm-field{display:none!important}'),'Hide extra AM/PM field in settings');
// Resume time is for the current application launch only.
assert.ok(html.includes('function q41(key,value){const next=JSON.stringify(key===KEY?{...value,resumeTime:""}:value);'),'Saved settings must not retain restart time');
assert.ok(html.includes('movement:"mitchell"};s.resumeTime=""; /* The next tournament must request its own restart time. */'),'Opening BridgeTimer must clear the old restart time');
assert.ok(html.includes('function commitResumeTime(e)')&&html.includes('s.resumeTime=v;')&&html.includes('q41(KEY,s);closeResumeEditor();render()'),'Live edit must still update the timer and UI');
// Default toggles: unchecked for fresh/reset settings, previously saved choices still honored.
assert.ok(html.includes('boardProgressNotice:false,sound:false,warnEnabled:true'),'Son and board notice must be OFF by default');
assert.ok(!html.includes('id="sound" type="checkbox" checked'),'Sound HTML default must be unchecked');
assert.ok(!html.includes('id="boardProgressNotice" type="checkbox" checked'),'Board notice HTML default must be unchecked');
assert.ok(html.includes('if(!x||!Object.prototype.hasOwnProperty.call(x,"boardProgressNotice"))s.boardProgressNotice=false;'),'Older settings with missing board notice must default OFF');
// Reprise input: muted red when empty; browser validity automatically restores normal style when HH:MM exists.
assert.ok(html.includes('id="resumeTime" type="time" value="" required'),'The Reprise HH:MM field must signal an empty value');
assert.ok(html.includes('#resumeTime:invalid:not(:focus){background:#30202a!important;border-color:#94535d!important'),'The empty, unfocused restart input needs a muted red background and border');
assert.ok(html.includes('#resumeTime::-webkit-calendar-picker-indicator{display:none!important'),'The time picker icon must remain hidden');
// Visual regression: consistent text relief, no overlay for live temporary notices.
assert.ok(html.includes('#timer #msg.roundMessageTemporary{text-shadow:0 6px 26px #000d,0 0 1px #000;-webkit-text-stroke:1.25px'),'Temporary notice relief must not disappear');
assert.ok(html.includes('#timer #pauseOverlay .pauseBig{text-shadow:0 6px 26px #000d,0 0 1px #000;-webkit-text-stroke:1.5px'),'PAUSE headline needs finish-like text relief');
assert.ok(html.includes('#timer #pauseOverlay .pauseSmall{text-shadow:0 3px 15px #000c'),'PAUSE instruction needs a readable subtle shadow');
assert.ok(html.includes('$("msg").classList.toggle("roundMessageTemporary",!!temporary)'),'A real temporary message in a between-round break must receive relief');
assert.ok(html.includes('#resumeTime:invalid:not(:focus){background:#30202a!important'),'Reprise may turn red only if invalid AND not focused');
assert.ok(!html.includes('#resumeTime:invalid{background:#30202a!important'),'The old always-red-on-focus style must not return');

// Tournoi: delicate green border encloses the full per-board time label, inputs and trailing S.
assert.ok(html.includes('.tournamentCard #timingLayout .boardTimeSetting{position:relative;justify-self:start;width:max-content;max-width:100%}'),'Per-board timing enclosure should fit content without stretching');
assert.ok(html.includes('.boardTimeSetting::before{content:"";position:absolute;inset:-3px -7px;border:1px solid rgba(73,202,114,.52);border-radius:9px;pointer-events:none}'),'Board time outline must remain subtle and noninteractive');
assert.ok(html.includes('<div class="timeEntry boardTimeSetting"><label for="boardMinutes">Temps par donne</label>'),'Complete minutes-seconds element should remain present');
// Jump advance reminder must have the exact same relief as a temporary message, not a colored glow.
assert.ok(!html.includes('text-shadow:0 0 22px color-mix(in srgb,var(--warn) 38%,transparent)'),'Legacy green jump-message halo must be removed');
assert.ok(html.includes('#timer.roundReading #msg.roundMessageJump{color:var(--message-color);text-shadow:0 6px 26px #000d,0 0 1px #000;-webkit-text-stroke:1.25px rgba(0,0,0,.30)}'),'Jump notice must use the same shadow and stroke as a temporary notice');
assert.ok(html.includes('#timer #msg.roundMessageTemporary{text-shadow:0 6px 26px #000d,0 0 1px #000;-webkit-text-stroke:1.25px rgba(0,0,0,.30)}'),'Temporary notice relief must remain intact');
// Screen Tests gallery must resize each message in its own 778px snapshot viewport.
assert.ok(html.includes('function fitGalleryNotice(frame){'),'Gallery must recalculate message font size after cloning');
assert.ok(html.includes('e.style.fontSize="";e.style.whiteSpace="";'),'Gallery must clear stale inline font sizing from the live off-screen DOM');
assert.ok(html.includes('const viewport=frame.contentWindow?.innerWidth||778;'),'Gallery fitting uses iframe viewport rather than actual app width');
assert.ok(html.includes('frame.setAttribute("sandbox","allow-same-origin")'),'Parent needs read access to its own script-disabled static preview');
assert.ok(html.includes('frame.onload=()=>requestAnimationFrame(()=>fitGalleryNotice(frame))'),'Re-fit only after preview iframe has laid out');
assert.ok(!html.includes('frame.setAttribute("sandbox","");frame.setAttribute("aria-hidden","true")'),'Opaque preview iframe cannot be remeasured');
// EXPERIMENTAL 16:9 LAYOUT — protected by this test, main remains stable.
// This is a distinct design experiment, NOT a removal of the user's contract.
for(const required of [
 'function updateStage(){',
 'const w=1600,h=900;',
 'const k=Math.min(innerWidth/w,innerHeight/h)',
 'root.style.setProperty(\'--stage-scale\',k);',
 'transform:scale(var(--stage-scale));transform-origin:0 0',
 'const vw=1600,vh=900;',
 'function fc(){',
 'const w=$(\'timer\').clientWidth,h=$(\'timer\').clientHeight;',
 'p.textContent=\'01:00:00\';',
 'p.textContent=\'59:59\';',
 'const titleBottom=title.offsetTop+title.offsetHeight;',
 'const topLimit=Math.max(12,titleBottom+18);',
 'const bottomLimit=bar.offsetTop-18;',
 'const shortClock=/^\\d{2}:\\d{2}$/.test(c.textContent);',
 'z.fontSize=(shortClock?SF:F)+\'px\';',
 'updateStage();C=null;fc();syncFaithfulMini(true);',
 'clone.style.setProperty(\'--stage-scale\',\'1\');',
 '#timer .topBtns #fsBtn{width:246px!important;'
])assert.ok(html.includes(required),'16:9 homothety experiment regression: '+required);
// October 25 — increase MM:SS size without moving any other element.
for(const token of [
 'const shortLineHeight=.68;',
 'SF=Math.max(F,Math.min(1100,maxW*100/shortW,room/shortLineHeight));',
 'const shortHeight=SF*shortLineHeight;',
 'z.lineHeight=shortClock?\'.68\':\'.78\';',
 'z.fontSize=(shortClock?SF:F)+\'px\';',
 'z.transform=\'translateY(\'+(shortClock?shortClockOffset:10)+\'px)\';',
 'const topLimit=Math.max(12,titleBottom+18);',
 'const bottomLimit=bar.offsetTop-18;'
])assert.ok(html.includes(token),'MM:SS-only size or safety spacing changed unexpectedly: '+token);
assert.ok(.78/.68>1.14,'Subhour 0.68 line-height allows more font growth than before');
// HH:MM:SS font size and transform remain unchanged, including after returning from MM:SS.
assert.ok(html.includes("F=Math.min(620,maxW*100/wideW,(h-435)/.78);"));
assert.ok(html.includes("z.fontSize=F+'px';z.transform='translateY(10px)';"));
// October 25: requested exact native opening/minimum size from Windows screenshot.
// On the user's ~1.18x Windows DPI, the original 812x612 constants opened
// a visibly ~684x519 window. 960x720 restores about ~810x610 on screen.
// These are native logical dimensions, not physical screenshot pixels.
const nativeSource=fs.readFileSync('main.go','utf8');
assert.ok(/defaultWindowWidth\s*=\s*960/.test(nativeSource),'Opening window must be 960 logical px wide to match approved screenshot at Windows DPI');
assert.ok(/defaultWindowHeight\s*=\s*720/.test(nativeSource),'Opening window must be 720 logical px high to match approved screenshot at Windows DPI');
assert.ok(nativeSource.includes('w.SetSize(defaultWindowWidth, defaultWindowHeight, webview.HintMin)'),
  'Native minimum must equal initial window dimensions');
// MM:SS: larger and lower with a conditional progress gap; HH:MM:SS unchanged.
for(const token of [
 "bar.style.top=shortClock?'calc(65.2% + 75px)':'';",
 'const desiredTop=Math.min(topLimit+30,bottomLimit-shortHeight);',
 "z.lineHeight=shortClock?'.68':'.78';",
 "F=Math.min(620,maxW*100/wideW,(h-435)/.78);",
 'const shortClock=/^\\d{2}:\\d{2}$/.test(c.textContent);'
])assert.ok(html.includes(token),'Subhour-only alignment requirement lost: '+token);
// Explicit October 25 request: the blue progress bar is visually removed,
// but retains its geometric box so the approved large MM:SS font does NOT shrink.
assert.ok(html.includes('#timer .progress{visibility:hidden!important;pointer-events:none!important}'),
  'Progress bar must be hidden in every timer state');
assert.ok(!html.includes('#timer .progress{display:none'),
  'Do not remove bar geometry: short-clock sizing currently measures offsetTop');
assert.ok(html.includes('shortClockOffset=desiredTop-c.offsetTop+26;'),
  'MM:SS digits must be 75 reference-stage pixels lower, without resizing');
assert.ok(html.includes("F=Math.min(620,maxW*100/wideW,(h-435)/.78);"),
  'HH:MM:SS font sizing must remain untouched');
assert.ok(html.includes('const shortLineHeight=.68;'),
  'Previously approved MM:SS font size must remain intact');
assert.ok(html.includes("z.lineHeight=shortClock?'.68':'.78';"),
  'MM:SS font increase and HH:MM:SS original metrics must be retained');
assert.ok(!html.includes("z.lineHeight=shortClock?'.72':'.78';"),
  'Do not revert to the previous smaller MM:SS clock');
// Uniform scale on both axes, regardless of viewport aspect ratio.
// The window opens at approximately 960x540 client pixels.
const canvasW=1600,canvasH=900;
function stageScale(w,h){return Math.min(w/canvasW,h/canvasH)}
for (const [windowW,windowH,screenW,screenH] of [
 [960,540,1650,928],[960,538,1650,928],[1200,675,1920,1080]
]){
 const windowScale=stageScale(windowW,windowH),fullScale=stageScale(screenW,screenH);
 assert.ok(windowScale>0&&fullScale>windowScale);
 for(const referenceSize of [18,74,90,340,1100,1600]){
   const observedRatio=(referenceSize*fullScale)/(referenceSize*windowScale);
   assert.ok(Math.abs(observedRatio-fullScale/windowScale)<1e-10,
      'Every width, height and font must share a single scale ratio');
 }
}
// Preserve the main branch's essential visual constraints.
assert.ok(html.includes('.progress{position:absolute;top:65.2%;left:50%;translate:-50% 0;width:min(1100px,calc(var(--timer-vw) * 88));height:15px'),'Progress width must remain 1100px in the 1600px base stage');
assert.ok(!html.includes('function syncWindowedStage(){'),'Rejected prior aspect-dependent implementation must not return');
const contract=fs.readFileSync('UI_LAYOUT_CONTRACT.md','utf8');
assert.ok(contract.includes('Plein écran strictement homothétique'));
assert.ok(contract.includes('Le chrono HH:MM:SS doit remplir la largeur utile'));

// Locked-duration clock: new composition only for a round started at >=1h.
// Do not silently regress into time-remaining-based format changes.
for(const required of [
 'longClockAtStart:false',
 'st.longClockAtStart=_crd()>=3600;',
 'longClockAtStart:st.longClockAtStart',
 'longClockAtStart:x.longClockAtStart??(x.roundDuration>=3600)',
 'const longStarted=st.phase==="round"&&(st.started?(st.longClockAtStart??(_crd()>=3600)):(q4e()>=3600));',
 'cel.classList.toggle("longStartClock",longStarted);',
 'if(longStarted){',
 'cel.innerHTML=\'<span class="clockPrimary">\'+hr+\':\'+String(mi).padStart(2,"0")+\'</span><span class="clockSeconds">\'+String(sec).padStart(2,"0")+\'</span>\';',
 '}else cel.textContent=ctx;',
 '#timer #clock.longStartClock{display:inline-flex;align-items:baseline;justify-content:center;gap:22px}',
 '#timer #clock.longStartClock .clockSeconds{font-size:.56em;',
 'let longClockKey="",longClockFont=0,longClockOffset=0;',
 "if(c.classList.contains('longStartClock')){",
 "const target=Math.max(normalF,shortSF*.931);",
 'return;'
])assert.ok(html.includes(required),'Start-duration-locked long-clock layout is missing: '+required);
// Only the short-round MM:SS clock is further reduced by exactly 2%.
// Multiplying the previous .95 scaling by .98 gives .931.
// The long-start HH:MM+SS rendering must remain untouched.
assert.ok(html.includes('SF=Math.max(F,SF*.931);'),
  'Requested further 2 percent reduction of MM:SS was removed');
assert.ok(Math.abs((400*.95)*.98-400*.931)<1e-8,
  'MM:SS font must be 2% smaller than previous .95 version before minimum F clamp');
// All other short-clock geometry and long-start styling remain unchanged.
for(const token of [
 'const shortLineHeight=.68;',
 "z.lineHeight=shortClock?'.68':'.78';",
 "shortClockOffset=desiredTop-c.offsetTop+26;",
 "F=Math.min(620,maxW*100/wideW,(h-435)/.78);",
 'const shortClock=/^\\d{2}:\\d{2}$/.test(c.textContent);'
])assert.ok(html.includes(token),'Approved short-clock rendering changed: '+token);
assert.ok(html.includes('#timer .progress{visibility:hidden!important;pointer-events:none!important}'),
 'Removed progress bar must stay removed');
for(const [original,expected] of [[7198,'1:59 / 58'],[3600,'1:00 / 00'],[3599,'0:59 / 59'],[58,'0:00 / 58']]){
 const hr=Math.floor(original/3600),mi=Math.floor((original%3600)/60),sec=original%60;
 assert.equal(hr+':'+String(mi).padStart(2,'0')+' / '+String(sec).padStart(2,'0'),expected);
}

/* User contract: under-one-hour START, not current remaining time.
   Pressing +1 minute or F8 cannot display 1:00:00. Run actual zshift()
   extracted from production JS, for running/paused/long and jump cases. */
const zshiftSource = scripts.map(x=>x[1]).join('\n');
const matchZshift = zshiftSource.match(/function zshift\(x\)\{([\s\S]*?)\}\s*function q48\(\)/);
assert.ok(matchZshift,'Cannot find production time-adjustment function');
function applyActualShift({startLong=false,phase='round',running=false,remaining=3590,amount=60,duration=startLong?5400:3000}={}){
 const now=100000;
 const state={phase,started:true,longClockAtStart:startLong,roundDuration:duration,
   running,remaining,endAt:running?now+remaining*1000:null,
   syncHoldUntil:1,syncDisplayCeiling:5};
 let renders=0;
 const context={st:state,_mon:()=>now,_crd:()=>state.roundDuration,render:()=>{renders++},Math};
 const shift=vm.runInNewContext('(function zshift(x){'+matchZshift[1]+'})',context);
 shift(amount);
 assert.equal(renders,1,'Time adjustment must trigger exactly one render');
 assert.equal(state.syncHoldUntil,0);
 const display=Math.ceil(state.remaining);
 return {remaining:state.remaining,display,remainingStartMode:state.longClockAtStart,endAt:state.endAt};
}
for(const running of [false,true]){
 assert.equal(applyActualShift({running}).display,3599,
  'Short-start +1 min must stop at 59:59, not 1:00:00');
 assert.equal(applyActualShift({running,remaining:3599,amount:60}).display,3599,
  'Further +1 min must not exceed the 59:59 cap');
 assert.equal(applyActualShift({running,remaining:3598,amount:60}).display,3599,
  'Boundary add must cap to 59:59');
 assert.equal(applyActualShift({running,remaining:3590,amount:-60}).display,3530,
  'Minus one minute still works on short starts');
 assert.equal(applyActualShift({running,startLong:true}).display,3650,
  'Long-start rounds must remain unrestricted, even below one hour');
 assert.equal(applyActualShift({running,startLong:true,remaining:600,amount:3600}).display,4200,
  'Long-start rounds must not switch to short cap after passing 59:59');
 assert.equal(applyActualShift({running,phase:'break',remaining:3590,amount:60}).display,3650,
  'Break-state adjustments must not gain a short-round restriction');
}
assert.ok(zshiftSource.includes('shortClockOffset=desiredTop-c.offsetTop+26;'),
 'Short MM:SS glyphs must be raised 16 reference px; long digits untouched');
assert.ok(zshiftSource.includes('SF=Math.max(F,SF*.931);'),
 'The approved MM:SS font-size must not change');

/* 26 Oct 2026: opening Message must not reflow the 16:9 header or club.
   These assertions protect the composer's absolute positioning and prevent
   the old .messageEditing layout switch from returning. */
for(const required of [
 '#timer .top{position:relative}',
 '#timer .top.messageComposeOpen .topBtns{visibility:hidden;pointer-events:none}',
 '#timer .top #tempMessageOverlay:not(.hidden){position:absolute;left:545px;right:22px;top:7px;bottom:7px;',
 '#timer #tempMessageOverlay #tempMessageHeading{display:none}',
 '#timer #tempMessageOverlay .tempMessageActions{flex-direction:column;',
 'id="tempMessageInput" aria-label="Message temporaire"',
 'top.classList.add("messageComposeOpen");$("tempMessageOverlay").classList.remove("hidden")',
 'top.classList.remove("messageComposeOpen");$("messageBtn").focus()'
]) assert.ok(html.includes(required),'Temporary-message header layout regression: '+required);
const allJs = scripts.map(x=>x[1]).join('\n');
const openEditor = allJs.match(/function q2c\(\)\{([\s\S]*?)\}\s*function q20\(\)/);
const closeEditor = allJs.match(/function q20\(\)\{([\s\S]*?)\}\s*function resumeEditorOpen\(\)/);
assert.ok(openEditor&&closeEditor,'Message editor handlers must exist');
assert.ok(!openEditor[1].includes('style.height')&&!closeEditor[1].includes('style.height'),
  'Temporary message must NEVER resize the title/header on open or close');
assert.ok(!openEditor[1].includes('messageEditing')&&!closeEditor[1].includes('messageEditing'),
  'Temporary message must not activate the old grid-reflow class');
assert.ok(html.includes("const top=$('timer').querySelector('.top');top.style.height=top.getBoundingClientRect().height+'px';top.classList.add('messageEditing');$('resumeOverlay')"),
  'Resume-time editor must remain unchanged');

/* Screenshot positioning only: compare unchanged typography, body and footer,
   while moving the event and MM:SS upward by the requested distances.
   A 1920x1080 screen scales the reference 1600x900 canvas by exactly 1.2. */
assert.ok(html.includes('#timer.roundReading #status{transform:translateY(-19px)}'),
 'Event text must be visually moved 11 virtual px upward without relayout');
assert.equal(19-16,3,'Event additional upward shift in virtual canvas pixels');
assert.equal(31-26,5,'MM:SS additional upward shift in virtual canvas pixels');
assert.ok(html.includes('shortClockOffset=desiredTop-c.offsetTop+26;'),
 'Short MM:SS must be 20 base pixels higher without a font-size change');
assert.ok(html.includes('SF=Math.max(F,SF*.931);'),
 'Keep accepted short-clock font size');
assert.ok(html.includes("F=Math.min(620,maxW*100/wideW,(h-435)/.78);"),
 'HH:MM:SS sizing unchanged');
assert.ok(html.includes('left:545px;right:22px;top:7px;bottom:7px;'),
 'Message input must start further left while preserving footer/header geometry');

// Mandatory font-size parity: the LONG primary HH:MM digits are no
// longer 20-25% smaller than the SHORT MM:SS glyphs. Both use the same
// short-round .931 reference and matching visual ink Y position.
// Compact seconds stay at exactly 56%; all other UI remains unchanged.
for(const token of [
 'const available=$(\'timer\').clientWidth-24;',
 'const normalF=Math.min(620,available*100/wideW,(h-435)/.78);',
 'const shortTop=Math.max(12,titleBottom+18);',
 'const shortBottom=main.clientHeight*.652+75-18;',
 'const shortSF=Math.max(normalF,Math.min(1100,available*100/shortW,shortRoom/.68));',
 'const target=Math.max(normalF,shortSF*.931);',
 'const font=Math.min(target,available*100/needed);',
 'const desiredTop=Math.min(shortTop+30,shortBottom-height);',
 'longClockFont=font;longClockOffset=desiredTop-c.offsetTop-53;',
 '#timer #clock.longStartClock .clockSeconds{font-size:.56em;',
 'shortClockOffset=desiredTop-c.offsetTop+26;',
 'SF=Math.max(F,SF*.931);',
 '#timer.roundReading #status{transform:translateY(-19px)}'
])assert.ok(html.includes(token),'Clock glyph-size parity or typography changed: '+token);
assert.ok(!html.includes('const font=Math.min(520,available*100/needed,verticalRoom/.68);'),
 'Old long-only 520px / hidden progress-bar size limitation must not return');
assert.ok(!html.includes('longClockFont=font;longClockOffset=desiredTop-c.offsetTop+26;'),
 'Long clock must use its visual baseline compensation, not the old lower one');
{
 // Numeric reference at 1920×1080: a 1600×900 homothetic canvas scales ×1.2.
 // Chromium visual capture with the current frontend measured:
 // short visible glyph ink y=295..720, long ink y=297..721 (±2px).
 const shortInk={top:295,bottom:720},longInk={top:297,bottom:721};
 assert.ok(Math.abs(longInk.top-shortInk.top)<=2 && Math.abs(longInk.bottom-shortInk.bottom)<=2,
   'Long and short primary glyphs should occupy the same visual band');
}
// The user approved long-format glyph SIZE. Adjust VERTICAL position only.
assert.ok(html.includes('longClockFont=font;longClockOffset=desiredTop-c.offsetTop-53;'),
 'Long digits must sit 4 reference pixels higher, with the same font');
assert.ok(!html.includes('longClockFont=font;longClockOffset=desiredTop-c.offsetTop-49;'),
 'Old slightly-too-low long clock offset must not return');
assert.ok(html.includes('shortClockOffset=desiredTop-c.offsetTop+26;'),
 'Short format position must remain untouched');
assert.ok(html.includes('#timer #clock.longStartClock .clockSeconds{font-size:.56em;'),
 'Keep smaller seconds of long format');
console.log(`Production UI regression OK: ${ids.length} unique elements, JS, countdown, pause, notices, previews and native bindings`);
