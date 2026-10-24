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
assert.ok(html.includes('#finishOverlay .finishResume{position:absolute;top:calc(58.8% + clamp(112px,13.8vw,220px))'),'Large MP4 restart announcement missing');
assert.ok(html.includes('font-size:clamp(60px,9vw,170px);line-height:1.06;font-weight:1000;color:#ff202d'),'MP4 red line must match headline scale');
assert.ok(html.includes('.finishBig.pairFinish~.finishResume{top:calc(58.8% + clamp(112px,13.8vw,220px));font-size:clamp(60px,9vw,170px)'),'Pairs restart line must match MP4 headline scale');

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
assert.ok(html.includes('#finishOverlay .finishBig.pairFinish{top:58.8%;font-size:clamp(52px,8vw,154px)}'),'Pairs green headline must match MP4');
assert.ok(html.includes('.finishBig.pairFinish~.finishResume{top:calc(58.8% + clamp(112px,13.8vw,220px));font-size:clamp(60px,9vw,170px)}'),'Pairs red announcement must match MP4');
assert.ok(html.includes('#resumeTime::-webkit-datetime-edit-ampm-field{display:none!important}'),'Hide extra AM/PM field in settings');
console.log(`Production UI regression OK: ${ids.length} unique elements, JS, countdown, pause, notices, previews and native bindings`);
