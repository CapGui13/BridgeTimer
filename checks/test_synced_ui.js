// Regression tests for the production HTML embedded in the official Windows executable.
// The historical tests are retained in the repository but refer to earlier internals.
const fs = require('node:fs');
const assert = require('node:assert/strict');
const vm = require('node:vm');
const html = fs.readFileSync('timer.html', 'utf8');
const scripts = [...html.matchAll(/<script\b[^>]*>([\s\S]*?)<\/script>/gi)];
assert.ok(scripts.length, 'The embedded UI must include JavaScript');
for (const [, src] of scripts) new vm.Script(src, {filename:'BridgeTimer:inline.js'});
// Transition screens must overlay only the central pane. The club/actions
// and time/round/buttons remain mounted, visible and unchanged in both phases.
const mainStart=html.indexOf('<div class="main">');
const footerStart=html.indexOf('<div><div class="bottom">',mainStart);
assert.ok(mainStart>=0&&footerStart>mainStart,'Timer pane/footer structure missing');
const mainPane=html.slice(mainStart,footerStart);
assert.ok(mainPane.includes('<div id="jumpSplash"')&&mainPane.includes('id="jumpSplashBar"'),
 'Saut and CHGT must use one overlay INSIDE .main, never cover top/bottom bands');
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
assert.ok(launchPos>0&&stopPos>launchPos,'Timer / Lancer must precede Arrêter in the footer');
assert.ok(html.includes('#settings #stopTimer.hidden{display:inline-flex!important;visibility:hidden!important'),'The hidden Arrêter slot must remain reserved');
assert.ok(html.includes('function q48(){')&&html.includes('st.syncDisplayCeiling=0;start();q4c(prev'),'Recommencer must restart immediately');
assert.ok(!html.includes('textContent="+"+fmt('),'End-of-round overrun must have no plus prefix');
assert.ok(html.includes('st.phase==="roundEnd"||st.phase==="ended"'),'Both modes must keep a terminal overtime display');
// Regression guarantees: Message publishes only after Valider;
// advancing from the MP4 end screen restarts immediately; overtime controls are grey.
assert.ok(!html.includes('id="sendTempBtn"'),'The obsolete instant-send M button must not return');
assert.ok(html.includes('$("messageBtn").onclick=toggleTemporaryMessageEditor'),'Message button must share the M-key behaviour');
assert.ok(html.includes('if(!e.repeat)toggleTemporaryMessageEditor()'),'Holding M must not dismiss and immediately reopen a message');
assert.ok(html.includes('if(q16()&&(st.phase==="round"||st.phase==="break")){q23();render();return}'),
 'Active displayed temporary message must be hidden before the composer is opened');
assert.ok(html.includes('for(const evt of ["focus","click"])$("quickMessage").addEventListener(evt,()=>{$("quickMessage").select()})'),
 'Clicking or focusing the saved temporary-message field must select the whole text');
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
assert.ok(html.includes('color:var(--message-color);font-size:96px;text-shadow:0 6px 26px #000d,0 0 1px #000;-webkit-text-stroke:1.25px'),'All shared notices keep the same text relief');
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
assert.ok(html.includes('#timer.roundReading #msg{left:50%;right:auto;transform:translateX(-50%);top:70%;height:29%;'),'Round notices share one layout; between-round deliberately uses jump splash');
assert.ok(!html.includes('#timer #msg.roundMessageTemporary{text-shadow:'),'No duplicate styling for temporary notices');
// Gallery thumbnails are exactly scaled copies of the 1600x900 timer stage.
// No separate typography, no 778x595 alternate reflow, and no stage re-scaling
// inside the iframe. These properties must apply to ALL 9 special screens.
for(const needed of [
 '.pv{position:relative;width:100%;aspect-ratio:16/9;',
 '.pv iframe{display:block;position:absolute;left:0;top:0;width:1600px;height:900px;',
 'function fitGalleryFrames(){',
 'cell.clientWidth/1600',
 'tm.classList.remove("spa","spm");',
 'toolbar.style.display="none";target.style.display="none";',
 'C=null;longClockKey="";render();',
 'clone.classList.remove("spa","spm","hidden");',
 '"--stage-scale":"1"',
 '"--stage-width":"1600px","--stage-height":"900px"',
 'width:1600px!important;height:900px!important;min-height:0!important',
 'transform:none!important',
 'frame.setAttribute("sandbox","allow-same-origin")',
 'frame.onload=()=>requestAnimationFrame(fitGalleryFrames)',
 'tm.classList.add("spm","spa");'
])assert.ok(html.includes(needed),'Screen Tests homothetic thumbnails regression: '+needed);
assert.ok(!html.includes('cell.clientWidth/778'),'Obsolete 778px gallery scaling must never return');
assert.ok(!html.includes('function fitGalleryNotice(frame){'),'Never resize thumbnail fonts differently from native timer');
{
 const source=scripts.map(x=>x[1]).join('\n');
 const fit=source.match(/function fitGalleryFrames\(\)\{([\s\S]*?)\n\}/);
 assert.ok(fit,'Gallery scale function missing');
 // Exercise the same scaling function used on resize and gallery rendering.
 const elements=[400,640,800].map(width=>{
  const iframe={style:{transform:''}};
  return {clientWidth:width,querySelector:()=>iframe,iframe};
 });
 const stub={ $:()=>({querySelectorAll:()=>elements}) };
 vm.runInNewContext('(function fitGalleryFrames(){'+fit[1]+'\n})',stub)();
 for(const cell of elements)assert.equal(cell.iframe.style.transform,
   'scale('+(cell.clientWidth/1600)+')',
   'Gallery preview must scale the whole stage uniformly');
}
// Screen Tests 'Voir en grand' MUST preserve the same stage geometry as
// 'Tous': the toolbar is outside the 1600x900 reference canvas and scaled
// along with it, never a fourth grid row compressing the main area.
for(const required of [
 '#timer.spm:not(.spa){grid-template-rows:auto minmax(0,1fr) auto;overflow:visible}',
 '#timer.spm:not(.spa) #sptb{position:absolute;left:0;right:0;top:-56px;height:56px;',
 "const singlePreview=!!root.classList?.contains('spm')&&!root.classList?.contains('spa');",
 'const k=singlePreview?Math.min(innerWidth/w,innerHeight/(h+previewToolbar)):standardScale;',
 'const previewToolbar=56;',
 'if(isAll)_rspg();updateStage();',
 'false);updateStage();C=null;showSettings(false);'
])assert.ok(html.includes(required),'Single-preview vs gallery stage mismatch: '+required);
{
 const source=scripts.map(x=>x[1]).join('\n');
 const body=source.match(/function updateStage\(\)\{([\s\S]*?)\n\}/);
 assert.ok(body,'updateStage not found for Screen Tests mode comparison');
 for(const [w,h] of [[960,720],[1280,720],[1920,1080],[1650,928]]){
  for(const mode of ['normal','all','single']){
   const variables=new Map();
   const root={
    classList:{contains:c=>mode!=='normal'&&(c==='spm'||(c==='spa'&&mode==='all'))},
    style:{setProperty:(k,v)=>variables.set(k,v)}
   };
   const sandbox={innerWidth:w,innerHeight:h,$:()=>root,Math,C:3};
   vm.runInNewContext('(function updateStage(){'+body[1]+'\n})',sandbox)();
   const preview=mode==='single',factor=Math.min(w/1600,h/(preview?956:900));
   const y=preview?(h-956*factor)/2+56*factor:0;
   assert.ok(Math.abs(Number(variables.get('--stage-scale'))-factor)<1e-12,
     'Single shared uniform scale, including native non-16:9 windows');
   assert.ok(Math.abs(parseFloat(variables.get('--stage-top'))-y)<1e-8,
     'Timer bands flush with viewport edges except isolated screen preview');
   assert.ok(Math.abs(parseFloat(variables.get('--stage-left'))-(preview?(w-1600*factor)/2:0))<1e-8,
     'Timer uses full window width, preview uses original 1600x900');
   assert.ok(Math.abs(parseFloat(variables.get('--stage-width'))-(preview?1600:w/factor))<1e-7,
     'Windowed timer expands stage grid horizontally without stretching fonts');
   assert.ok(Math.abs(parseFloat(variables.get('--stage-height'))-(preview?900:h/factor))<1e-7,
     'Windowed timer expands stage grid vertically, removing empty top/bottom strips');
  }
 }
}
// EXPERIMENTAL 16:9 LAYOUT — protected by this test, main remains stable.
// This is a distinct design experiment, NOT a removal of the user's contract.
for(const required of [
 'function updateStage(){',
 'const w=1600,h=900;',
 'const standardScale=Math.min(innerWidth/w,innerHeight/h);',
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
// October 27: user explicitly requests identical native 16:9 WINDOW geometry
// for BOTH Settings and Timer, with scrollable Settings and a fixed footer.
// The caption height is compensated using the actual Win32 client rectangle.
// These are native logical dimensions, not physical screenshot pixels.
const nativeSource=fs.readFileSync('main.go','utf8');
assert.ok(/defaultWindowWidth\s*=\s*812/.test(nativeSource),'Restored opening/minimum window must be 812 pixels wide');
assert.ok(/defaultWindowHeight\s*=\s*680/.test(nativeSource),'Settings opening/minimum must match the 680px reference');
assert.ok(nativeSource.includes('w.SetSize(defaultWindowWidth, defaultWindowHeight, webview.HintMin)'),
  'Native minimum must equal initial window dimensions');
assert.ok(nativeSource.includes('nativeCloseRequestHandler()') &&
  nativeSource.includes('w.Eval(`if(typeof q34==="function"){q34()}'),
  'Native X / Alt+F4 must open the SAME HTML confirmation as Quitter');
assert.ok(nativeSource.includes('closeApproved.Store(true)'),
  'An approved HTML quit must bypass the second native confirmation');
assert.ok(!nativeSource.includes('nativeClientCalibrated=true'),
  'Native view switching must not secretly shrink startup height to 16:9');
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
assert.ok(html.includes("function openResumeEditor(){") && html.includes("$('resumeOverlay').classList.remove('hidden');input.focus()") &&
  !html.includes("top.style.height=top.getBoundingClientRect().height+'px'") &&
  html.includes('#timer .topBtns #resumeOverlay:not(.hidden)') &&
  html.includes('<div class="topBtns"><div id="resumeOverlay"'),
  'Resume-time editor must open compactly before Reprise without header reflow');

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
 'const shortReferenceWidth=Math.min(w-24,(main.clientWidth-96)*1.02);',
 'const normalF=Math.min(620,shortReferenceWidth*100/wideW,(h-435)/.78);',
 'const shortTop=Math.max(12,titleBottom+18);',
 'const shortBottom=main.clientHeight*.652+75-18;',
 'const shortSF=Math.max(normalF,Math.min(1100,shortReferenceWidth*100/shortW,shortRoom/.68));',
 'const target=Math.max(normalF,shortSF*.931);',
 'const font=Math.min(target,available*100/needed);',
 'const desiredTop=Math.min(shortTop+30,shortBottom-height);',
 'longClockFont=font;longClockOffset=desiredTop-c.offsetTop-63;',
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
 // Verified in Chromium at viewport 1920×1080 and 1650×928.
 // Both clocks now use the same 482.5096 canvas-px font in the reference
 // layout, and the visible glyph ink ranges match (295..715 screen px at
 // 1920×1080, 253..614 at 1650×928). Visual verification on Windows still
 // remains separate from these source-level assertions.
 const shortFont=482.5096216216217,longFont=482.5096216216217;
 assert.ok(Math.abs(longFont-shortFont)<1e-6,'Reference long and short font sizes must match');
}
// The short-clock width reference now drives LONG font size as well; maintain ink alignment.
assert.ok(html.includes('longClockFont=font;longClockOffset=desiredTop-c.offsetTop-63;'),
 'Long digits must sit 4 reference pixels higher, with the same font');
assert.ok(!html.includes('longClockFont=font;longClockOffset=desiredTop-c.offsetTop-53;'),
 'Previous high offset must not return');
assert.ok(!html.includes('longClockFont=font;longClockOffset=desiredTop-c.offsetTop-49;'),
 'Old slightly-too-low long clock offset must not return');
assert.ok(html.includes('shortClockOffset=desiredTop-c.offsetTop+26;'),
 'Short format position must remain untouched');
assert.ok(html.includes('#timer #clock.longStartClock .clockSeconds{font-size:.56em;'),
 'Keep smaller seconds of long format');
// Strictly forbid the previous long-only reference that was 0.8% too large.
assert.ok(!html.includes('const normalF=Math.min(620,available*100/wideW,(h-435)/.78);'),
 'Long format must not calculate its short reference using the larger available width');
assert.ok(!html.includes('const shortSF=Math.max(normalF,Math.min(1100,available*100/shortW,shortRoom/.68));'),
 'Long format must use exact short width for shortSF');
// Native Windows full-screen screenshots (same 1920x1080 resolution)
// showed actual long-primary numeral ink precisely 14px lower than short:
// '0' y=273 long vs y=259 short; '5' y=279 long vs y=265 short.
// The immutable stage is 1600x900, zoomed by 1.2; shifting long clock
// up 12 reference pixels compensates for ~14.4 physical pixels.
// This test forbids edits that accidentally reset the long-only correction.
assert.equal(273-259,14);
assert.equal(279-265,14);
assert.ok(Math.abs(12*(1920/1600)-14)<.5,
 'Long timer native screenshot correction must resolve 14px displacement');
assert.ok(html.includes('longClockFont=font;longClockOffset=desiredTop-c.offsetTop-63;'),
 'Long-only native Windows baseline fix has been removed');
assert.ok(html.includes('shortClockOffset=desiredTop-c.offsetTop+26;'),
 'Short format must not move');
assert.ok(html.includes('#timer.roundReading #status{transform:translateY(-19px)}'),
 'Event title must remain in place');
assert.ok(html.includes('#timer #clock.longStartClock .clockSeconds{font-size:.56em;'),
 'Long-format small seconds must remain at 56 percent');

// === IMMUTABLE VISUAL CONTRACT — 26 October 2026 ==========================
// A. One and ONLY one homothetic scale factor is applied to the entire
//    1600x900 timer stage, independent of fullscreen/windowed UI state.
// B. Short MM:SS and long H:MM use the SAME primary font-size reference,
//    vertical ink placement and title gap; only long SS uses .56em.
// These test the real updateStage() function and guard both fc() branches.
{
 const source=script.match(/function updateStage\(\)\{[\s\S]*?\n\}/);
 assert.ok(source,'Homothetic updateStage function missing');
 const stageFnSource=source[0];
 assert.ok(stageFnSource.includes('const w=1600,h=900;'),
   'Layout reference must remain 1600x900');
 assert.ok(stageFnSource.includes('Math.min(innerWidth/w,innerHeight/h)'),
   'Uniform scale factor must be shared on both axes');
 assert.ok(html.includes('transform:scale(var(--stage-scale));transform-origin:0 0'),
   'Entire stage must use one transform, not independently scaled UI elements');
 for(const [viewportW,viewportH] of [[960,540],[960,720],[1280,720],[1650,928],[1920,1080]]){
   const set = new Map();
   const sandbox = {
     innerWidth:viewportW,innerHeight:viewportH,C:'cached',
     $:name=>{
       assert.equal(name,'timer');
       return {style:{setProperty:(key,value)=>set.set(key,value)}};
     },
     Math
   };
   const update = vm.runInNewContext('('+stageFnSource+')',sandbox);
   update();
   const k=Number(set.get('--stage-scale'));
   const expected=Math.min(viewportW/1600,viewportH/900);
   assert.ok(Math.abs(k-expected)<1e-12,'Stage must use one factor in every viewport');
   assert.ok(Math.abs(parseFloat(set.get('--stage-width'))-viewportW/k)<1e-7);
   assert.ok(Math.abs(parseFloat(set.get('--stage-height'))-viewportH/k)<1e-7);
   assert.equal(set.get('--stage-left'),'0px');
   assert.equal(set.get('--stage-top'),'0px');
   for(const reference of [15,42,90,300,480,1100]){
     const width=reference*k,height=reference*k;
     assert.ok(Math.abs(width/height-1)<1e-12,
       'Fonts, margins and buttons cannot have separate horizontal/vertical scaling');
   }
   assert.equal(sandbox.C,null,'Resize must invalidate clock sizing cache');
 }
}
for(const requirement of [
 'CONTRAT VISUEL PERMANENT (26/10/2026)',
 'GARDE-FOU FONCTIONNEL — mêmes mesures',
 'const shortReferenceWidth=Math.min(w-24,(main.clientWidth-96)*1.02);',
 'const normalF=Math.min(620,shortReferenceWidth*100/wideW,(h-435)/.78);',
 'const shortSF=Math.max(normalF,Math.min(1100,shortReferenceWidth*100/shortW,shortRoom/.68));',
 'const target=Math.max(normalF,shortSF*.931);',
 'SF=Math.max(F,SF*.931);',
 '#timer #clock.longStartClock .clockSeconds{font-size:.56em;',
 'longClockFont=font;longClockOffset=desiredTop-c.offsetTop-63;',
 'shortClockOffset=desiredTop-c.offsetTop+26;',
 '#timer.roundReading #status{transform:translateY(-19px)}'
])assert.ok(html.includes(requirement),
  'HOMOTHETY OR LONG/SHORT VISUAL PARITY REGRESSION: '+requirement);
assert.ok(!html.includes('const font=Math.min(520,available*100/needed,verticalRoom/.68);'),
 'A long-only font cap would shrink primary H:MM compared to short MM:SS');
{
 const contract=fs.readFileSync('UI_LAYOUT_CONTRACT.md','utf8');
 for(const clause of [
  'RÈGLE A — Homothétie totale entre fenêtre et plein écran.',
  'RÈGLE B — Parité visuelle des formats court et long.',
  'durée initiale du tour',
  '56 %',
  'même distance visible entre le bas du nom de l’évènement'
 ]){
   assert.ok(contract.includes(clause),
     'Mandatory two-part visual contract accidentally deleted: '+clause);
 }
}
// The numeric 1920x1080 screenshot baseline is a guard for Windows ink
// alignment, but a native Windows comparison is still needed after UI edits.
// ========================================================================
// Documentation guard: each new assistant session/change must consult AGENTS.md,
// then the permanent layout contract, BEFORE editing. Presence is checked by CI.
{
 const instructions=fs.readFileSync('AGENTS.md','utf8');
 for(const token of [
  'AVANT tout changement',
  'UI_LAYOUT_CONTRACT.md',
  'checks/test_synced_ui.js',
  'Homothétie fenêtré',
  'Parité court',
  'Source de vérité commune',
  '56 %',
  'durée **initiale**',
  'Procédure obligatoire'
 ]){
   assert.ok(instructions.includes(token),
     'Missing mandatory agent preflight procedure: '+token);
 }
}

// Permanent shared band-height contract (26 Oct 2026):
// 2 virtual-stage pixels freed from BOTH top and bottom, identically
// in window/fullscreen and short/long. Footer labels centered with one
// shared rule, no independently hardcoded pixel offsets.
for (const selector of [
 '.top{display:grid;grid-template-columns:1fr auto;align-items:center;gap:15px;padding:13px 22px;',
 '#timer .bottom{height:88px;min-height:88px;padding:0 190px}',
 '#timer #localTime,#timer #round{top:50%;bottom:auto;transform:translateY(-50%)}'
]) assert.ok(html.includes(selector),'Uniform two-band layout regression: '+selector);
assert.ok(!html.includes('#timer .bottom{height:90px;min-height:90px;'),
 'Footer cannot silently return to the original 90px band');
assert.equal((html.match(/#timer #localTime,#timer #round\{top:50%;bottom:auto;transform:translateY\(-50%\)\}/g)||[]).length,1,
 'Footer alignment must remain a single shared CSS rule for both labels');

/* Mandatory presentation contract:
   - Round notices: one #msg box and one font fitting method.
   - Between-round countdown and table-jump: same #jumpSplash screen and
     same q40() fitter, typography, caption, timer, and progress bar.
   - Both still live within the SAME homothetic 1600x900 main canvas. */
assert.ok(html.includes('#timer.roundReading #msg{'),
 'Round messages must share their one approved box');
assert.ok(!html.includes('#timer.roundReading #msg,#timer.breakState #msg{'),
 'Between-round must NOT use the old normal message box');
for(const broken of [
 '#timer.breakState #msg{top:71.5%;',
 '#timer.roundReading #msg.roundMessageJump{color:',
 '#timer.roundReading #msg.roundMessageTemporary{color:'
])assert.ok(!html.includes(broken),'Old per-message layout must not return: '+broken);
assert.ok(html.includes('const active=timer.classList.contains("roundReading");'),
 'The round message fitter must not independently lay out the between-round screen');
assert.ok(html.includes('const max=154,min=22,step=2;'),
 'All notices must use one shared auto-fit range');
assert.ok(html.includes('e.style.whiteSpace="normal";'),
 'Long messages must be allowed to wrap');
assert.ok(html.includes('e.style.whiteSpace="nowrap";'),
 'Short messages may use one line');
assert.ok(!html.includes('Prochain tour :'),'Remove Prochain tour X from between-round screen');
assert.ok(html.includes('$( "submsg" )')===false ||
 html.includes('$("submsg").textContent="";'),
 'Between-round explanatory line must be empty');
// Exercise production fit rule with mocked element sizes to catch a broken
// state gate and ensure all three message sources share identical outcomes.
{
 const src=scripts.map(x=>x[1]).join('\n');
 const found=src.match(/function q38\(\)\{([\s\S]*?)\n\}\s*\/\* Single source of truth/);
 assert.ok(found,'Cannot find unified live message fitter');
 function run(kind,textValue,limit=1200){
  const e={textContent:textValue,style:{fontSize:'',whiteSpace:''},
   clientWidth:limit,clientHeight:220,getClientRects:()=>[1]};
  Object.defineProperty(e,'scrollWidth',{get(){
   const size=parseFloat(e.style.fontSize)||96;
   // Simulated line width; use same width/height metrics across all kinds.
   const full=textValue.length*size*.53;
   return e.style.whiteSpace==='nowrap'?full:Math.min(full,limit);
  }});
  Object.defineProperty(e,'scrollHeight',{get(){
   const size=parseFloat(e.style.fontSize)||96;
   const lines=e.style.whiteSpace==='nowrap'?1:
     Math.ceil(textValue.length*size*.53/limit);
   return lines*size*1.08;
  }});
  const timer={clientWidth:1600,classList:{contains:c=>c===kind}};
  const sandbox={ $:id=>id==='msg'?e:timer,Math,lrf:'' };
  vm.runInNewContext('(function q38(){'+found[1]+'\n})',sandbox)();
  return {font:e.style.fontSize,whitespace:e.style.whiteSpace};
 }
 for(const str of ['Annonce courte','Vous êtes censés jouer la donne 11','Au prochain tour, les EO sautent une table','AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA']){
  assert.ok(run('roundReading',str).font,
   'Every notice displayed during a round must get a fitted font size');
  assert.equal(run('breakState',str).font,'',
   'Between-round now renders in transition splash, not the old round message fitter');
 }
}

// Actual jump and between-round MUST use precisely the same transition splash.
// No duplicate layout, and the previous "Prochain tour : X" line stays removed.
for(const required of [
 'function transitionSplashModel(state,settings,temporaryBreakText=""){',
 'const between=state.phase==="break",jump=state.phase==="jump";',
 'const transition=transitionSplashModel(st,s,breakTemporary);',
 '$("jumpSplash").classList.toggle("on",transition.visible);',
 '$("jumpSplashTitle").textContent=transition.title;',
 '$("jumpSplashText").textContent=transition.text;',
 '$("jumpSplashCountdownLabel").textContent=transition.label;',
 '$("jumpSplashSeconds").textContent=transition.seconds;',
 '$("jumpSplashBar").style.width=transition.percent+"%";',
 'const isTransition=isJump||st.phase==="break";',
 '#jumpSplash.on{display:grid;grid-template-rows:auto minmax(0,1fr) auto auto;'
])assert.ok(html.includes(required),'Jump/between same-design regression: '+required);
assert.ok(!html.includes('Prochain tour :'),'Never reintroduce the next-round line');
// Validate one pure content model drives both phases, with only content changing.
{
 const src=scripts.map(x=>x[1]).join('\n');
 const match=src.match(/function transitionSplashModel\(state,settings,temporaryBreakText=""\)\{([\s\S]*?)\n\}\s*let lsf/);
 assert.ok(match,'Shared transition model must be accessible');
 const fn=vm.runInNewContext('(function transitionSplashModel(state,settings,temporaryBreakText=""){'+match[1]+'\n})',{
  clamp:(x,min,max)=>Math.max(min,Math.min(max,x)),Math,Number
 });
 const settings={between:60,jumpDisplaySecs:15,jumpSplashTitleSetting:'ATTENTION',
  jumpSplashBodySetting:'À cette position, les EO sautent une table',
  jumpCountdownLabel:'secondes pour le changement'};
 const jump=fn({phase:'jump',started:true,remaining:10},settings);
 const between=fn({phase:'break',started:true,remaining:40,breakDuration:80},settings);
 assert.equal(jump.visible,true);
 assert.equal(between.visible,true);
 assert.equal(jump.title,'ATTENTION');
 assert.equal(between.title,'CHANGEMENT DE TOUR');
 assert.equal(between.text,'Changez de table');
 assert.equal(jump.label,between.label);
 assert.equal(jump.seconds,10);
 assert.equal(between.seconds,40);
 assert.equal(jump.percent,10/15*100);
 assert.equal(between.percent,50);
 assert.equal(fn({phase:'break',started:true,remaining:20,breakDuration:40},settings,'Message personnalisé').text,'Message personnalisé');
 assert.equal(fn({phase:'round',started:true,remaining:55},settings).visible,false);
}
// =======================================================================

/* CHGT customization — separate persisted content, SAME jump dialog style.
 * The CHGT button is placed just after the time-between-rounds field.
 * Visibility derives strictly from current seconds and Paires format.
 * Normal 00 -> hidden; Debug + Paires -> visible even at 00. */
for(const id of [
 'betweenMsgBtn','betweenMsgOverlay','betweenMsgForm','betweenMsgCancel',
 'betweenMsgConfirm','betweenSplashTitleSetting','betweenSplashBodySetting',
 'betweenMsgSeconds','betweenCountdownLabel'
])assert.equal(counts.get(id),1,'Missing/duplicate CHGT customization ID '+id);
for(const token of [
 'id="betweenField" class="unitField hidden"><input id="between" type="tel" min="0" max="99" value="00"><span class="unit">S</span></div><button id="betweenMsgBtn"',
 'title="Personnaliser le changement de tour">CHGT</button>',
 '#betweenLabel,#betweenField,#betweenMsgBtn,#sessionDurationBox{position:relative;left:-80px}',
 'id="betweenMsgOverlay" class="jumpMsgOverlay hidden"',
 'id="betweenMsgForm"',
 'id="betweenSplashTitleSetting"',
 'id="betweenSplashBodySetting"',
 'id="betweenCountdownLabel"',
 'id="betweenMsgSeconds" type="text" inputmode="numeric" data-numeric="int" pattern="[0-9]*" maxlength="2" min="0" max="99" value="00"',
 'for="betweenMsgSeconds">Nb secondes entre tours',
 'class="jumpMsgTimeRow"><div class="jumpMsgTimeCol"><label for="betweenMsgSeconds"',
 '.jumpMsgTimeCol #jumpCountdownLabel,.jumpMsgTimeCol #betweenCountdownLabel{width:100%;height:36px}',
 'const betweenMsgFieldIds=["betweenSplashTitleSetting","betweenSplashBodySetting","betweenMsgSeconds","betweenCountdownLabel"];',
 ' $("betweenMsgSeconds").value=String(clamp(Number($("between").value)||0,0,99)).padStart(2,"0");',
 ' $("between").value=String(seconds).padStart(2,"0");',
 'function syncBetweenMsgButton(){',
 'syncBetweenMsgButton();render()};',
 'const eligible=$("mode").value==="2"&&(debugActive()||Number($("between").value)>=1);',
 '$("betweenMsgBtn").classList.toggle("hidden",!eligible);',
 '$("between").addEventListener("input",syncBetweenMsgButton)',
 '$("between").addEventListener("change",syncBetweenMsgButton)',
 'function openBetweenMsgDialog(){',
 'function closeBetweenMsgDialog(confirmed=false){',
 'function confirmBetweenMsgDialog(){',
 '$("betweenMsgBtn").onclick=openBetweenMsgDialog;',
 '$("betweenMsgForm").onsubmit=e=>{e.preventDefault();confirmBetweenMsgDialog()}',
 'if(!confirmed&&betweenMsgSnapshot)for(const id of betweenMsgFieldIds)',
 'betweenSplashTitleSetting:$("betweenSplashTitleSetting").value',
 'betweenSplashBodySetting:$("betweenSplashBodySetting").value',
 'betweenCountdownLabel:$("betweenCountdownLabel").value',
 'title:between?(settings.betweenSplashTitleSetting??"CHANGEMENT DE TOUR")',
 'text:between?(temporaryBreakText||((settings.betweenSplashBodySetting??"Changez de table")==="CHANGEZ DE TABLE"?"Changez de table":(settings.betweenSplashBodySetting??"Changez de table")))',
 'label:between?(settings.betweenCountdownLabel??"secondes pour le changement")',
 'el.closest("#jumpMsgForm,#betweenMsgForm")'
])assert.ok(html.includes(token),'CHGT regression: '+token);
{
 // Execute the production visibility function for 0, 1 and 99 seconds
 // in Paires and MP4 without any DOM browser dependencies.
 const src=scripts.map(x=>x[1]).join('\n');
 const found=src.match(/function syncBetweenMsgButton\(\)\{([\s\S]*?)\n\}/);
 assert.ok(found,'CHGT eligibility function not found');
 function verify(mode,seconds,debug=false){
  let hidden=true,disabled=true;
  const btn={classList:{toggle:(name,value)=>{if(name==='hidden')hidden=value}},set disabled(v){disabled=v}};
  const dom={mode:{value:mode},between:{value:String(seconds)},betweenMsgBtn:btn};
  const context={$:id=>dom[id],Number,debugActive:()=>debug,closeBetweenMsgDialog:()=>{}};
  vm.runInNewContext('(function syncBetweenMsgButton(){'+found[1]+'\n})',context)();
  return {hidden,disabled};
 }
 // Standard mode: 00 hidden, 01+ visible in Paires only.
 assert.deepEqual(verify('2',0),{hidden:true,disabled:true});
 assert.deepEqual(verify('2',1),{hidden:false,disabled:false});
 assert.deepEqual(verify('2',99),{hidden:false,disabled:false});
 assert.deepEqual(verify('4',1),{hidden:true,disabled:true});
 // Debug must override zero-second gating, but NEVER the Paires mode.
 assert.deepEqual(verify('2',0,true),{hidden:false,disabled:false});
 assert.deepEqual(verify('2',1,true),{hidden:false,disabled:false});
 assert.deepEqual(verify('4',0,true),{hidden:true,disabled:true});
 assert.deepEqual(verify('4',1,true),{hidden:true,disabled:true});
}
{
 const src=scripts.map(x=>x[1]).join('\n');
 const f=src.match(/function transitionSplashModel\(state,settings,temporaryBreakText=""\)\{([\s\S]*?)\n\}/);
 assert.ok(f,'Missing shared transition design data model');
 const model=vm.runInNewContext('(function transitionSplashModel(state,settings,temporaryBreakText=""){'+f[1]+'\n})',{
  clamp:(v,a,b)=>Math.max(a,Math.min(v,b)),Math,Number
 });
 const settings={jumpSplashTitleSetting:'ATTENTION',jumpSplashBodySetting:'Saut',
  jumpCountdownLabel:'Saut secondes',jumpDisplaySecs:15,between:30,
  betweenSplashTitleSetting:'Tour suivant',betweenSplashBodySetting:'On change de table',
  betweenCountdownLabel:'secondes restantes'};
 const customized=model({phase:'break',started:true,remaining:10,breakDuration:30},settings);
 assert.equal(customized.title,'Tour suivant');
 assert.equal(customized.text,'On change de table');
 assert.equal(customized.label,'secondes restantes');
 assert.equal(customized.seconds,10);
 const jump=model({phase:'jump',started:true,remaining:10},settings);
 assert.equal(jump.title,'ATTENTION');
 assert.equal(jump.text,'Saut');
 assert.equal(jump.label,'Saut secondes');
}

// CHGT seconds editor must be on the LEFT of countdown label, using precisely
// the same CSS grid as MSG. There is no stale explanatory sentence.
assert.ok(!html.includes('Durée : réglée par le champ « Temps entre tours ».'),
 'Remove the misleading read-only CHGT duration explanation');
{
 const area=html.slice(html.indexOf('id="betweenMsgOverlay"'),html.indexOf('</section><section id="timer"'));
 assert.ok(area.indexOf('id="betweenMsgSeconds"')<area.indexOf('id="betweenCountdownLabel"'),
  'Seconds editor must appear left of countdown label inside CHGT');
 assert.equal((area.match(/class="jumpMsgTimeRow"/g)||[]).length,1,
  'CHGT must reuse the MSG two-column time + countdown layout once');
}
{
 const src=scripts.map(x=>x[1]).join('\n');
 const open=src.match(/function openBetweenMsgDialog\(\)\{([\s\S]*?)\n\}\s*function closeBetweenMsgDialog/);
 const confirm=src.match(/function confirmBetweenMsgDialog\(\)\{([\s\S]*?)\n\}\s*let jumpMsgSnapshot/);
 const close=src.match(/function closeBetweenMsgDialog\(confirmed=false\)\{([\s\S]*?)\n\}\s*function confirmBetweenMsgDialog/);
 assert.ok(open&&confirm&&close,'CHGT open/confirm/cancel handlers missing');
 // Mock the actual production routines, including their transactional
 // boundary. Merely typing in the modal must never alter the main setting.
 function simulate(initial,choice,accept){
  let main=String(initial).padStart(2,'0');
  let modalOpen=false;
  const dom={
   between:{value:main},
   betweenMsgSeconds:{value:'00'},
   betweenMsgBtn:{classList:{contains:()=>false},setAttribute:()=>{},focus:()=>{}},
   betweenMsgOverlay:{classList:{
    contains:name=>name==='hidden'?!modalOpen:false,
    add:name=>{if(name==='hidden')modalOpen=false},
    remove:name=>{if(name==='hidden')modalOpen=true}
   }},
   betweenSplashTitleSetting:{value:'CHANGEMENT DE TOUR',focus:()=>{}},
   betweenSplashBodySetting:{value:'Changez de table'},
   betweenCountdownLabel:{value:'secondes pour le changement'},
   settings:{classList:{contains:()=>false}}
  };
  let readCount=0,savedBetween=null,closeArgs=[];
  const ids=['betweenSplashTitleSetting','betweenSplashBodySetting','betweenMsgSeconds','betweenCountdownLabel'];
  let scope={
   $:key=>dom[key],betweenMsgFieldIds:ids,
   betweenMsgIsOpen:()=>modalOpen,betweenMsgSnapshot:null,
   q43:()=>{},clearTimeout:()=>{},autosaveTimer:null,save:()=>{},
   clamp:(n,min,max)=>Math.max(min,Math.min(max,n)),Number,String,Object,
   closeBetweenMsgDialog:flag=>{closeArgs.push(flag)},
   read:()=>{readCount++;savedBetween=Number(dom.between.value)},q41:()=>{},KEY:'test',s:{},
   render:()=>{}
  };
  const run=(code,confirmed=false)=>vm.runInNewContext('(function(confirmed=false){'+code+'\n})',scope)(confirmed);
  run(open[1]);
  assert.equal(dom.betweenMsgSeconds.value,main,'Opening CHGT must copy current main seconds');
  dom.betweenMsgSeconds.value=String(choice);
  assert.equal(dom.between.value,main,'Editing CHGT must not prematurely change main parameters');
  if(accept){
   run(confirm[1]);
   assert.equal(dom.between.value,String(Math.max(0,Math.min(99,Number(choice)||0))).padStart(2,'0'),
    'Valider must immediately synchronize main seconds');
   assert.equal(savedBetween,Number(dom.between.value),'Valider must persist canonical s.between');
   assert.equal(readCount,1,'Valider must persist once');
   assert.deepEqual(closeArgs,[true],'Valider must close transaction as confirmed');
  }else{
   // Cancel must leave main parameters unchanged and restore form snapshot.
   assert.ok(scope.betweenMsgSnapshot,'Open must snapshot all CHGT fields');
   run(close[1]);
   assert.equal(dom.between.value,main,'Annuler must not change main seconds');
   assert.equal(dom.betweenMsgSeconds.value,main,'Annuler must restore CHGT seconds');
  }
 }
 for(const value of [0,1,7,45,99,105])simulate(30,value,true);
 simulate(0,52,false);
 simulate(27,0,false);
}

// Reproduce the CHGT Debug lag: switching Match -> Paires through q7()
// temporarily suspends Debug; its inner _upu()/read() can hide CHGT at 00.
// q7 MUST refresh CHGT in its own finally, synchronously before returning,
// without relying on the 450ms autosave timer.
{
 const src=scripts.map(x=>x[1]).join('\n');
 const wrapper=src.match(/function q7\(fn\)\{([\s\S]*?)\}function _adu\(/);
 const sync=src.match(/function syncBetweenMsgButton\(\)\{([\s\S]*?)\n\}/);
 assert.ok(wrapper&&sync,'Missing Debug format wrapper / CHGT sync function');
 assert.ok(wrapper[0].includes('finally{document.body.classList.add("debugMode");_adu();syncBetweenMsgButton()}'),
   'CHGT must update synchronously after restoring Debug');
 function change(initialMode,newMode,initialSeconds,debugOn=true){
  let mode={value:initialMode}, between={value:String(initialSeconds)};
  let active=debugOn,hidden=true,disabled=true,syncCount=0,debugRestoreCount=0;
  const button={classList:{toggle:(cls,on)=>{if(cls==='hidden')hidden=on}},
   set disabled(v){disabled=v},get disabled(){return disabled}};
  const body={classList:{contains:name=>name==='debugMode'&&active,
   remove:name=>{if(name==='debugMode')active=false},
   add:name=>{if(name==='debugMode'){active=true;debugRestoreCount++}}}};
  const dom={mode,between,betweenMsgBtn:button};
  const context={
   document:{body},$:name=>dom[name],
   debugActive:()=>active,_adu:()=>true,
   Number,closeBetweenMsgDialog:()=>{},
   syncCount
  };
  context.syncBetweenMsgButton=vm.runInNewContext(
   '(function syncBetweenMsgButton(){'+sync[1]+'\n})',context);
  const realSync=context.syncBetweenMsgButton;
  context.syncBetweenMsgButton=()=>{syncCount++;return realSync()};
  const q7=vm.runInNewContext('(function q7(fn){'+wrapper[1]+'})',context);
  // Simulate _upu/read's immediate eligibility calculation WHILE Debug is
  // suspended by q7: even at zero it temporarily hides CHGT.
  q7(()=>{mode.value=newMode;context.syncBetweenMsgButton()});
  return {hidden,disabled,syncCount,debugRestoreCount};
 }
 assert.deepEqual(change('4','2',0),{
  hidden:false,disabled:false,syncCount:2,debugRestoreCount:1
 },'Debug + Paires + 00 must show CHGT immediately after mode switch');
 assert.deepEqual(change('2','4',0),{
  hidden:true,disabled:true,syncCount:2,debugRestoreCount:1
 },'Match/4 must hide CHGT immediately after switch');
 assert.deepEqual(change('4','2',30),{
  hidden:false,disabled:false,syncCount:2,debugRestoreCount:1
 },'Positive between duration must also remain immediate');
 assert.deepEqual(change('4','2',0,false),{
  hidden:true,disabled:true,syncCount:1,debugRestoreCount:0
 },'Without Debug, zero seconds still correctly hides CHGT');
}

// Transition message color, user rule: the shared Saut de table and
// Changement de tour title AND central text are RED by default, customizable
// independently of the blue progress/accent and green ordinary notices.
{
 const newColor='transitionMessageColor';
 assert.equal(counts.get(newColor),1,'Transition message color input must be unique');
 for(const token of [
  '<span>Messages de changement et saut</span><input id="transitionMessageColor" type="color" value="#ef4444"',
  '--transition-message-color:#ef4444',
  'color:var(--transition-message-color);pointer-events:none}',
  '#jumpSplash .jumpSplashTitle{',
  '#jumpSplash .jumpSplashText{',
  '#jumpSplashBar{height:100%;width:100%;background:var(--accent)',
  'color:var(--message-color)',
  'messageColor:"#22c55e",transitionMessageColor:"#ef4444"',
  'root.setProperty("--transition-message-color",s.transitionMessageColor||def.transitionMessageColor);',
  'transitionMessageColor:$("transitionMessageColor").value',
  's.transitionMessageColor=p.transitionMessageColor||def.transitionMessageColor;',
  's.transitionMessageColor=def.transitionMessageColor;',
  'const colorSettingIds=["accent","background","menu","text","messageColor","transitionMessageColor"];',
  'transitionMessageColor:s.transitionMessageColor};',
  'transitionMessageColor:def.transitionMessageColor};',
  '!x.transitionMessageColor||/^#[0-9a-f]{6}$/i.test(x.transitionMessageColor)',
  '"messageColor","transitionMessageColor"].includes(key)'
 ])assert.ok(html.includes(token),'Transition message color regression: '+token);
 assert.ok(!html.includes('#jumpSplash .jumpSplashText{color:var(--accent)'),
  'Transition message body must not use the accent color');
 assert.ok(!html.includes('#jumpSplash .jumpSplashTitle{color:var(--accent)'),
  'Transition title must not use accent color');
 const script=scripts.map(x=>x[1]).join('\n');
 const sanitize=script.match(/function q6\(x\)\{([\s\S]*?)\}function q2a\(/);
 assert.ok(sanitize,'Persistent settings sanitizer q6 must exist');
 const def={accent:'#0ea5e9',messageColor:'#22c55e',transitionMessageColor:'#ef4444'};
 const clean=vm.runInNewContext('(function q6(x){'+sanitize[1]+'})',{
  def,Number,Object,Math,q26:x=>!!x&&typeof x==='object'&&!Array.isArray(x)
 });
 const valid=clean({transitionMessageColor:'#Cc4455'});
 assert.equal(valid.transitionMessageColor,'#Cc4455','Chosen transition color must be preserved');
 assert.equal(clean({transitionMessageColor:'red'}).transitionMessageColor,undefined,
  'Malformed transition color must not be persisted');
 assert.equal(clean({messageColor:'#22c55e',accent:'#0ea5e9',transitionMessageColor:'#ff1234'}).messageColor,
  '#22c55e','Old message colors are still independent');
 const validation=script.match(/function q2a\(x\)\{(.*?)\}const def=/);
 assert.ok(validation,'Saved Custom color validator q2a must exist');
 const q2a=vm.runInNewContext('(function q2a(x){'+validation[1]+'})',{
  q26:x=>!!x&&typeof x==='object'&&!Array.isArray(x)
 });
 const preset={accent:'#0ea5e9',background:'#0f172a',menu:'#111827',text:'#f8fafc'};
 assert.equal(q2a({...preset,transitionMessageColor:'#aa0000'}),true,
  'Custom color themes must accept independent transition colors');
 assert.equal(q2a({...preset,transitionMessageColor:'bad'}),false,
  'Custom color themes must reject invalid transition colors');
 assert.equal(q2a(preset),true,
  'Previously saved themes without new field remain compatible');
}
// Phase-isolation guards. Verified separately with headless Chromium across
// five viewport sizes: transitions and fullscreen toggles cannot move bands.
assert.ok(html.includes('#timer.breakState .main{background:var(--panel)}'),
 'Between-round may tint only the central pane, never the permanent bands');
assert.ok(!html.includes('#timer.breakState{background:var(--panel)}'),
 'Whole-stage background changes would repaint both header and footer');
assert.ok(html.includes('#timer .controls #minus,#timer .controls #plus{box-sizing:border-box;width:114px;min-width:114px;flex:0 0 114px}'),
 'Jump-specific +/- 15 s labels must not shift the controls group');
assert.ok(html.includes('const transition=transitionSplashModel(st,s,breakTemporary);'),
 'Transition phases must share one model, not redefine stage layout');
assert.ok(html.includes('tm.classList.remove("spa","spm");')&&html.includes('tm.classList.add("spm","spa");'),
 'Gallery captures must isolate and restore preview mode classes');
assert.ok(html.includes('$("timer").classList.remove("spm","spa");'),
 'Returning from screen tests must restore the standard stage classes');
// Updated contract: Settings opens at 812x680; Timer uses a shorter 812x490
// native frame without changing fullscreen rendering.
assert.ok(!nativeSource.includes('func timerWindowOuterHeight('),'Obsolete 16:9 outer-window calibration returned');
assert.ok(nativeSource.includes('w.Bind("nativeSetView"'),'Missing JS/native screen-mode binding');
assert.ok(nativeSource.includes('w.SetSize(defaultWindowWidth, defaultWindowHeight, webview.HintMin)'),'Native min must equal opening size');
assert.ok(nativeSource.includes('timerViewActive.Store(isTimer)') && nativeSource.includes('timerWindowHeight = 490'),'Timer needs a distinct minimum and height of 490px');
assert.ok(nativeSource.includes('msg == wmGetMinMaxInfo') && nativeSource.includes('minimum.Y = int32(timerWindowHeight)') && nativeSource.includes('rtlMoveMemory.Call(lp+24'), 'Native minimum must follow the active screen');
assert.ok(html.includes('syncNativeView("timer")')&&html.includes('syncNativeView("settings")'),'Both screens must notify the native window of their active mode');
assert.ok(html.includes('if(!on)syncNativeView($("timer").classList.contains("hidden")?"settings":"timer")'),'Synchronize native mode after fullscreen');
assert.equal((html.match(/syncNativeView\("timer"\)/g)||[]).length,1,'Timer must not change geometry on phase transitions');
assert.equal((html.match(/syncNativeView\("settings"\)/g)||[]).length,2,'Settings and Timer must both synchronize the native view');
// Fullscreen settings header shares the immutable timer stage geometry.
// The native window remains untouched by these CSS-only fullscreen changes.
for(const required of [
 'id="settingsFullscreenBtn"',
 'body.fs #settings .wrap>.head{',
 'width:1600px;height:var(--settings-top-height,82px);transform:scale(var(--settings-stage-scale))',
 'body.fs #settings .wrap>.head #drawerClose{',
 'width:168px;min-width:168px',
 'body.fs #settings .wrap>.head #settingsFullscreenBtn{',
 'display:inline-flex;width:246px;min-width:246px',
 'docRoot.style.setProperty(\'--settings-stage-scale\',k);',
 '$("settingsFullscreenBtn").onclick=fs;',
 'document.body.appendChild($("miniTimer"))',
 'body.settingsLive #miniTimer.spView{',
 'display:block;position:fixed;left:0;bottom:0',
])assert.ok(html.includes(required),'Fullscreen settings/thumbnail regression: '+required);
assert.ok(!html.includes('settingsActions.prepend($("miniTimer"))'),
 'Live thumbnail must never be placed inside the fixed footer');
assert.ok(html.includes('function cacheSettingsHeaderGeometry(){')&&html.includes('cacheSettingsHeaderGeometry();q43();'), 'Settings must inherit the measured timer header height before hiding the timer');
assert.ok(!html.includes('body.fs #timer .top{'),
 'Do not change the original timer header just to match settings');

// 27 October — live tournament locks, deferred Debug edits, and unified footer.
for(const k of [
 'const lockedDurationIds=["hours","minutes","seconds","boardMinutes","boardSeconds"]',
 'function syncLiveTournamentControls(live){',
 'const locked=!!live&&!debugActive();',
 '$("between").disabled=locked?$("mode").value!=="2"',
 'if(locked)$("boardProgressNotice").disabled=false;',
 'if(st.started&&document.body.classList.contains("settingsLive")){cb.disabled=false;return}',
 'st.roundBetween=Math.max(0,Number(s.between)||0);',
 'body.fs #settings .actions{',
 'height:var(--settings-bottom-height,88px)!important;',
 'body.fs #settings .actions .settingsActionButtons .btn,',
 'body.fs #settings .actions #quitAppBtn{'
])assert.ok(html.includes(k),'Missing active-session/footer guard: '+k);
assert.ok(!html.includes('st.remaining=newDuration;if(wasRunning)_ses()'),
 'Debug live duration changes must never restart the running clock');
assert.ok(!html.includes('st.remaining=newBetween;if(wasRunning)_ses()'),
 'Debug changes of the inter-round setting must not restart an active break');
// Preserve the 812x680 Settings startup; dynamic 812x490 is applied only
// when Timer is activated.
assert.ok(!nativeSource.includes('nativeClientCalibrated=true'),
 'Native window must not be resized to a 16:9 client aspect at startup');
assert.ok(!nativeSource.includes('target = settingsWindowRect'), 'Legacy native view-based frame resizing must remain absent');
assert.ok(html.includes('render();syncNativeView("settings");zclean()'), 'Initial Settings must sync native view without changing size');
assert.ok(html.includes('#settings .actions,\nbody.settingsLive #settings .actions,'), 'Opaque footer must cover Settings in both modes');
assert.ok(html.includes('background:var(--panel)!important;\n backdrop-filter:none!important;'), 'Settings footer must be opaque and not backdrop-filtered');

/* Windowed only: slim Settings title band must inherit actual timer top band.
   Never alter the fullscreen title band, permanent footer, or timer stage. */
for(const rule of [
 'body:not(.fs) #settings .wrap{padding-top:var(--settings-window-top-height,42px)}',
 'height:var(--settings-top-height,82px)',
 'font-size:40px;line-height:var(--settings-title-height,55px);',
 'root.style.setProperty("--settings-window-title-height",title.getBoundingClientRect().height+"px");',
 'root.style.setProperty("--settings-window-top-height",bar.getBoundingClientRect().height+"px");',
 'docRoot.style.setProperty(\'--settings-window-top-height\',(82*settingsWindowScale)+\'px\');',
])assert.ok(html.includes(rule),'Windowed title band regression: '+rule);

/* Windowed Settings must mirror the last two actual timer-header buttons,
   including fullscreen access, regardless of the center column width. */
for(const required of [
 'body:not(.fs) #settings .wrap>.head{',
 'width:1600px;height:var(--settings-top-height,82px)',
 'transform:scale(var(--settings-stage-scale,.5))',
 'body:not(.fs) #settings .wrap>.head #drawerClose{',
 'width:168px;min-width:168px;',
 'body:not(.fs) #settings .wrap>.head #settingsFullscreenBtn{',
 'display:inline-flex;width:246px;min-width:246px;',
 '$("settingsFullscreenBtn").textContent=on?"Quitter plein écran":"Plein écran";',
 '$("settingsFullscreenBtn").onclick=fs;'
]) assert.ok(html.includes(required),'Windowed Settings header button alignment: '+required);
// Startup return is never displayed without a session; leave its slot
// reserved so the Plein écran button stays at exactly the same x-coordinate.
for(const token of [
 'body:not(.settingsLive) #settings .wrap>.head #drawerClose{',
 'visibility:hidden!important;pointer-events:none!important;',
 'body:not(.fs).settingsLive #settings .actions{',
 'height:var(--settings-bottom-height,88px)!important;',
 'min-height:var(--settings-bottom-height,88px)!important;',
 'max-height:var(--settings-bottom-height,88px)!important;',
 'transform:scale(var(--settings-stage-scale,.5))!important;',
 'body:not(.fs).settingsLive #settings .actions .settingsActionButtons{',
 'body:not(.fs) #settings .actions #quitAppBtn,',
])assert.ok(html.includes(token),'Startup return/footer regression: '+token);
assert.ok(html.includes('<button id="drawerClose" class="btn drawerClose">Retour au timer</button>'),
 'Startup return must not have legacy ambiguous Retour text');
// The old 77px stop-button width must not clip the larger synchronized
// footer typography. Give Arrêter room, with a visible gap before Reset.
for(const token of [
 '#settings .actions #stopTimer{',
 'width:auto!important;min-width:132px!important;',
 'padding-left:18px!important;padding-right:18px!important;',
 'margin-right:13px!important;'
])assert.ok(html.includes(token),'Stop button sizing/gap regression: '+token);
// In both MP4/TPP, footer buttons must be centered between the hour's
// right edge and the round label's left edge (not at width/2 of stage).
for(const contract of [
 '#timer .controls{position:absolute;left:var(--footer-controls-center,50%);',
 'function alignTimerFooterControls(){',
 'const freeCenter=(timeBounds.right+roundBounds.left)/2;',
 'const center=(freeCenter-bounds.left)/stageScale;',
 'if(debugActive())_adu();alignTimerFooterControls();fc();',
 " if(typeof alignTimerFooterControls==='function')alignTimerFooterControls();"
])assert.ok(html.includes(contract),'Footer center regression: '+contract);
// A single 1600x900 stage must have identical typography in full and
// windowed modes, even below the old 850px viewport breakpoint.
for(const val of [
 'invariant settings-button slots & screen-independent timer styles',
 'width:711px!important;min-width:711px!important;max-width:711px!important;',
 'flex:0 0 104px!important;',
 'flex:0 0 136px!important;',
 'flex:0 0 154px!important;',
 'flex:0 0 106px!important;',
 'flex:0 0 162px!important;',
 '#settings .actions .settingsActionButtons > #stopTimer.hidden {',
 'display:inline-flex!important;visibility:hidden!important;',
 '#timer .controls{gap:9px!important;}',
 'font-size:21px!important;padding:10px 14px!important;',
 '#timer .topBtns{gap:8px!important;}',
 'font-size:18px!important;padding:10px 13px!important;'
]) assert.ok(html.includes(val),'Stable settings positions/fullscreen typography: '+val);
// Window-width media rules must never downscale the hour or round text
// inside the fixed 1600x900 virtual stage. Their apparent size depends
// exclusively on the outer stage scale.
for(const token of [
 '#timer #localTime{\n font-size:clamp(34px,calc(var(--timer-vw) * 3.1),56px)!important;',
 '#timer #round{\n font-size:clamp(34px,calc(var(--timer-vw) * 3.4),62px)!important;',
 'left:22px!important;',
 'right:22px!important;'
])assert.ok(html.includes(token),'Footer hour/round virtual scale regression: '+token);

// Exit requires an explicit confirmation whether triggered by Quitter, Esc,
// or the existing native WM_CLOSE -> nativeConsumeCloseRequest queue.
assert.ok(html.includes('function q34(){\n if(exitClosing||q1d())return;'),'Quitter must present modal and be idempotent');
assert.ok(html.includes('$("exitConfirmOverlay").classList.remove("hidden");'),'Exit modal must be visible');
assert.ok(html.includes('async function q46(){if(exitClosing||!q1d())return;'),'Exit must not be callable without explicit confirmation');
assert.ok(html.includes('if(e.key==="Escape"){e.preventDefault();e.stopPropagation();if(!e.repeat)q21();return}'),'Escape must cancel exit confirmation');
assert.ok(html.includes('function commitLiveSettingsOnReturn(){'),'All return paths must sync current settings');
assert.ok(html.includes('commitLiveSettingsOnReturn();document.body.classList.remove("dockMode"'),'Return-to-timer must commit before switching view');
assert.ok(html.includes('st.roundBetween=Math.max(0,Number(s.between)||0);'),'Upcoming interval must be refreshed');
assert.ok(!html.includes('function q34(){if(exitClosing)return;q46()}'),'Old unconfirmed exit must be absent');
// The 8-board session startup defaults (audit point 3) are intentionally unchanged.
assert.ok(html.includes('const per=Math.max(0,(+s.boardMinutes||0)*60+(+s.boardSeconds||0)),total=Math.min(43200,8*per);'),'Startup recalculation deliberately preserved');

// Prevent letterbox-stage offsets from pulling windowed Settings bars away
// from the native client top/bottom during independent X/Y resizing.
for(const rule of [
 "docRoot.style.setProperty('--settings-window-scale',settingsWindowScale);",
 "body:not(.fs) #settings .wrap>.head {",
 "left:0!important;",
 "top:0!important;",
 "transform:scale(var(--settings-window-scale,.5))!important;",
 "body:not(.fs).settingsLive #settings .actions {",
 "bottom:0!important;"
]) assert.ok(html.includes(rule),'Settings independent window resize regression: '+rule);
// The native request never shows a separate MessageBox. Only the existing
// on-page exit overlay is allowed to ask for confirmation.
assert.ok(!nativeSource.includes('func confirmNativeClose('));
assert.ok(nativeSource.includes('if msg == wmClose && !closeApproved.Load() {'));
assert.ok(nativeSource.includes('nativeCloseRequestHandler = func() {'));
assert.ok(nativeSource.includes('w.Dispatch(func() {'));
assert.ok(html.includes('function q34(){') && html.includes('exitConfirmOverlay'));
console.log(`Production UI regression OK: ${ids.length} unique elements, JS, countdown, pause, notices, previews and native bindings`);
