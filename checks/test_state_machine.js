// State-machine unit tests against CURRENT BridgeTimer functions.
// Replaces the 2025-era test that extracted functions that no longer exist.
const fs=require("node:fs"),vm=require("node:vm"),assert=require("node:assert/strict");
const html=fs.readFileSync("timer.html","utf8");
function extract(name){
 const start=html.indexOf("function "+name+"(");
 assert.ok(start>=0,"Missing live function: "+name);
 let open=html.indexOf("{",start),depth=0,quote=null,escape=false;
 for(let i=open;i<html.length;i++){
  const c=html[i];
  if(escape){escape=false;continue}
  if(quote){if(c==="\\")escape=true;else if(c===quote)quote=null;continue}
  if(c==="'"||c==='"'||c==="`"){quote=c;continue}
  if(c==="{")depth++;
  if(c==="}"&&!--depth)return html.slice(start,i+1);
 }
 throw Error("Unbalanced function "+name);
}
const names=["q4e","_bds","qa","_crd","_crb","q4a","qe","zadvance","q15","fmt","zboard","pause"];
let released=0,renders=0,beeps=0;
const context={
 s:null,st:null,clearInterval:()=>{},_mon:()=>10000,
 q32:()=>{released++},q1a:()=>{beeps++},render:()=>{renders++},
 clamp:(x,a,b)=>Math.max(a,Math.min(b,x)),
 $:()=>({textContent:"",disabled:false}),console
};
vm.createContext(context);
vm.runInContext(names.map(extract).join("\n"),context);
function reset(props={},state={}){
 context.s={mode:"2",positions:6,startPosition:1,boards:4,
  hours:0,minutes:30,seconds:0,boardMinutes:7,boardSeconds:30,
  between:15,jumpRound:0,jumpDisplaySecs:15,...props};
 context.st={pos:1,phase:"round",remaining:1800,running:true,
  started:true,endAt:1900000,interval:null,syncHoldUntil:0,
  syncDisplayCeiling:0,roundDuration:1800,roundBetween:15,
  roundBoardDuration:450,roundBoards:4,breakDuration:0,
  jumpReminderRound:0,longClockAtStart:false,...state};
}
reset({mode:"4"},{pos:2});
assert.equal(context.qe(),false);
assert.equal(context.st.phase,"roundEnd");
assert.equal(context.st.running,false);
assert.equal(context.st.remaining,0);
assert.ok(released>0);
reset({mode:"2",positions:6,between:15},{pos:3});
assert.equal(context.qe(),true);
assert.equal(context.st.phase,"break");
assert.equal(context.st.pos,3);
assert.equal(context.st.remaining,15);
context.zadvance(0);
assert.equal(context.st.phase,"round");
assert.equal(context.st.pos,4);
reset({mode:"2",positions:6,between:10,jumpRound:2},{pos:2});
assert.equal(context.qe(),true);
assert.equal(context.st.phase,"jump");
context.zadvance(0);
assert.equal(context.st.phase,"break");
context.zadvance(0);
assert.equal(context.st.pos,3);
reset({mode:"2",positions:6},{pos:6});
assert.equal(context.qe(),false);
assert.equal(context.st.phase,"ended");
assert.equal(context.st.running,false);
reset({mode:"2",minutes:30,between:0,boards:4},{pos:3});
context.q4a(3,false);
assert.equal(context._crd(),1800);
context.s.minutes=40;context.s.between=20;
assert.equal(context._crd(),1800,"Editing the form must not change active round");
assert.equal(context._crb(),0,"Break time is snapped for current round");
context.q4a(4,false);
assert.equal(context._crd(),2400);
assert.equal(context._crb(),20);
reset({mode:"4",hours:4,minutes:0,seconds:0},{pos:1});
context.q4a(1,false);
assert.equal(context._crd(),14400);
assert.equal(context.st.longClockAtStart,true);
assert.equal(context.fmt(14400),"04:00:00");
assert.equal(context.q15(100250,60),59750);
assert.equal(context.q15(100750,60),60250);
reset({mode:"4"},{pos:1,remaining:100,running:true,endAt:110000,
 syncHoldUntil:0,syncDisplayCeiling:0});
context.pause();
assert.equal(context.st.running,false);
assert.equal(context.st.started,true,"Pause must keep tournament active");
assert.equal(context.st.endAt,null);
assert.equal(context.st.remaining,100);
assert.ok(renders>0);
console.log("CURRENT state-machine tests OK: MP4 / Paires, jump, break, snapshots, 4h clock, pause and wall alignment");
