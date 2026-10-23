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

console.log(`Production UI regression OK: ${ids.length} unique elements, JS, countdown, pause, notices, previews and native bindings`);
