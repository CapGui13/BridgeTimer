// Explicit behavior for running-timer notices. Other screens remain unchanged.
const fs=require("node:fs"),vm=require("node:vm"),assert=require("node:assert/strict");
const html=fs.readFileSync("timer.html","utf8");
const a=html.indexOf("function chooseRoundNotice("),b=html.indexOf("\nlet lastRoundNoticeFit=",a);
assert.ok(a>0&&b>a,"Running notice selector missing");
const ctx={};vm.runInNewContext(html.slice(a,b),ctx);const choose=ctx.chooseRoundNotice;
function check(args,text,kind){const result=choose(...args);assert.equal(result.text,text);assert.equal(result.kind,kind)}
check(["","",""],"","board");
check(["Vous êtes censés jouer la donne 4","",""],"Vous êtes censés jouer la donne 4","board");
check(["Donne 4","Saut de table",""],"Saut de table","jump");
check(["Donne 4","Saut de table","Les scores !"],"Les scores !","temporary");
check(["","Saut de table",""],"Saut de table","jump");
check(["","","Message urgent"],"Message urgent","temporary");
assert.ok(html.includes('$( "status").textContent=s.eventName')||html.includes('$("status").textContent=(s.eventName||"").trim()'));
assert.ok(html.includes('$("msg").textContent=notice.text'));
assert.ok(html.includes('$("msg").classList.toggle("roundMessageJump"'));
assert.ok(html.includes('$("msg").classList.toggle("roundMessageTemporary"'));
assert.ok(html.includes('if((_sps?screenPreviewKind==="temporary":tempMessageActive())&&st.phase!=="ended"&&st.phase!=="round")'));
assert.ok(html.includes('function fitRoundNotice()'));
assert.ok(html.includes('fitRoundNotice()\n}'));
assert.ok(html.includes('t.classList.toggle("roundReading",st.phase==="round")'));
assert.ok(!html.includes('id="mainMessage"'));
assert.ok(!html.includes('s.mainMessage'));
assert.ok(!html.includes('cfg.mainMessage'));
assert.ok(html.includes('else if(st.phase==="break")'));
assert.ok(html.includes('else if(st.phase==="roundEnd")'));
assert.ok(html.includes('$("jumpSplash").classList.toggle("on",jumpSplashOn)'));
console.log("Running timer text hierarchy and notice precedence OK");
