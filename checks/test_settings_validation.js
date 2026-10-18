// Test independently validating persisted preference data without running the UI.
const fs=require("node:fs"),vm=require("node:vm"),assert=require("node:assert/strict");
const html=fs.readFileSync("timer.html","utf8");
const start=html.indexOf("const def="),end=html.indexOf(";let s=",start);
const begin=html.indexOf("function sanitizeStoredSettings("),finish=html.indexOf("function validColorPreset(",begin);
assert.ok(start>0&&end>start&&begin>0&&finish>begin);
const context={};
vm.runInNewContext("function validPlainObject(x){return !!x&&typeof x==='object'&&!Array.isArray(x)}\n"+
 html.slice(start,end+1)+"\n"+html.slice(begin,finish),context);
const clean=context.sanitizeStoredSettings;
const good=clean({accent:"#00AbCd",background:"#000011",menu:"#444444",text:"#ffffff",
 clubName:"Test club",eventName:"Festival",sound:false,boardProgressNotice:false,quickMessageSecs:12});
assert.equal(good.accent,"#00AbCd");assert.equal(good.clubName,"Test club");
assert.equal(good.boardProgressNotice,false);assert.equal(good.sound,false);
const bad=clean({accent:876,menu:{foo:"bar"},background:"#222222",text:"#fffffg",
 clubName:3,eventName:"Valid event",sound:"false",boardMinutes:[],boardSeconds:Infinity,
 warnMinutes:-10,dangerSeconds:1000,jumpMessage:null,logoData:{bytes:[0]}});
assert.equal(bad.background,"#222222");assert.equal(bad.eventName,"Valid event");
for(const key of ["accent","menu","text","clubName","sound","boardMinutes","boardSeconds","jumpMessage","logoData"])
 assert.ok(!(key in bad),"Wrong type must fall back to defaults: "+key);
assert.equal(bad.warnMinutes,0);assert.equal(bad.dangerSeconds,59);
assert.equal(Object.keys(clean(null)).length,0);assert.equal(Object.keys(clean([])).length,0);
const upper=clean({accent:"#CFA5A5",movement:"howell",mode:"2",logoData:""});
assert.equal(upper.accent,"#CFA5A5");assert.equal(upper.mode,"2");
assert.equal(upper.movement,"howell");
assert.equal(Object.keys(clean({accent:"#xyzxyz",mode:"bad",movement:"bogus"})).length,0);
function luminance(hex){const v=[1,3,5].map(i=>parseInt(hex.slice(i,i+2),16)/255);
 const c=v.map(n=>n<=.04045?n/12.92:((n+.055)/1.055)**2.4);
 return .2126*c[0]+.7152*c[1]+.0722*c[2];}
assert.ok(1.05/(luminance("#e60033")+.05)>=4.5,"Quitter text contrast must meet WCAG AA");
console.log("Persisted settings sanitation and Quitter contrast OK");
