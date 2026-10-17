const fs = require("fs");

const html = fs.readFileSync("timer.html", "utf8");

function extractFunction(name) {
  const marker = "function " + name + "(";
  const start = html.indexOf(marker);
  if (start < 0) throw new Error("Missing function in timer.html: " + name);
  const brace = html.indexOf("{", start);
  let depth = 0;
  let quote = null;
  let escape = false;
  let templateDepth = 0;
  for (let i = brace; i < html.length; i++) {
    const ch = html[i];
    if (escape) { escape = false; continue; }
    if (quote) {
      if (ch === "\\") { escape = true; continue; }
      if (quote === "`" && ch === "$" && html[i + 1] === "{") {
        templateDepth++;
        i++;
        continue;
      }
      if (templateDepth > 0) {
        if (ch === "{") templateDepth++;
        else if (ch === "}") templateDepth--;
        continue;
      }
      if (ch === quote) quote = null;
      continue;
    }
    if (ch === "'" || ch === '"' || ch === "`") { quote = ch; continue; }
    if (ch === "{") depth++;
    else if (ch === "}") {
      depth--;
      if (depth === 0) return html.slice(start, i + 1);
    }
  }
  throw new Error("Unclosed function in timer.html: " + name);
}

const functionNames = [
  "duration",
  "boardDurationSeconds",
  "snapshotRoundSettings",
  "currentRoundDuration",
  "currentRoundBetween",
  "currentRoundBoardTimingMatches",
  "beginRound",
  "applyDebugSettingsToCurrentTimer",
  "transitionAfterRound",
  "alignedWallDelayMs",
  "restoreUndoState",
  "warnThreshold",
  "dangerThreshold",
  "buildScreenPreview",
];

let s = {};
let st = {};
const def={jumpMessage:"Au prochain tour, les EO sautent une table"};
const clamp = (n,a,b) => Math.max(a, Math.min(b, n));
function releaseWakeLock() {}
function debugActive() { return true; }
function syncEndAtToWallSecond() { st.endAt = 999; }
const source = functionNames.map(extractFunction).join("\n");
eval(source);

function assert(condition, message) {
  if (!condition) throw new Error(message);
}
function reset(settings, state) {
  s = Object.assign({
    hours: 0, minutes: 30, seconds: 0,
    boardMinutes: 7, boardSeconds: 30, boards: 4,
    between: 0, mode: "4", positions: 6, jumpRound: 0,
  }, settings || {});
  st = Object.assign({
    pos: 1, phase: "round", remaining: 0, running: true,
    endAt: 1, interval: null, started: true,
    roundDuration: 0, roundBetween: 0, roundBoardDuration: 0,
    roundBoards: 0, breakDuration: 0, jumpReminderRound: 0,
  }, state || {});
}

// Match/4 always stops at the end of a round.
reset({mode:"4",positions:6},{pos:2});
snapshotRoundSettings();
assert(transitionAfterRound() === false, "Match/4 transition must stop");
assert(st.phase === "roundEnd", "Match/4 must enter roundEnd");
assert(st.running === false && st.remaining === 0, "Match/4 roundEnd must be stopped at 00:00");

// Pairs final round ends the session.
reset({mode:"2",positions:13},{pos:13});
snapshotRoundSettings();
assert(transitionAfterRound() === false, "Pairs final transition must stop");
assert(st.phase === "ended", "Pairs final round must end the session");

// Pairs with a break keeps the current tour number until the break finishes.
reset({mode:"2",positions:13,between:15},{pos:5});
snapshotRoundSettings();
assert(transitionAfterRound() === true, "Pairs break transition should continue");
assert(st.phase === "break" && st.pos === 5 && st.remaining === 15, "Pairs break state is wrong");

// Jump announcement is a separate countdown before the next round begins.
reset({mode:"2",positions:13,between:0,jumpRound:6,jumpDisplaySecs:15,minutes:15,boards:2},{pos:6});
snapshotRoundSettings();
assert(transitionAfterRound() === true, "Jump announcement must start");
assert(st.phase === "jump" && st.pos === 6, "Jump must hold the previous round number");
assert(st.remaining === 15, "Jump countdown must use configured duration");
beginRound(7,false);
assert(st.phase === "round" && st.pos === 7 && st.remaining === 900, "Next round must start with its full duration");

// Timing edits during a live round do not rewrite the active round; they apply next round.
reset({mode:"2",positions:13,minutes:30,between:0,boards:4,boardMinutes:7,boardSeconds:30},{pos:3});
snapshotRoundSettings();
assert(currentRoundDuration() === 1800, "Initial round duration snapshot is wrong");
s.minutes = 40;
s.between = 20;
s.boards = 8;
s.boardMinutes = 5;
s.boardSeconds = 0;
assert(currentRoundDuration() === 1800, "Live duration edit leaked into current round");
assert(currentRoundBetween() === 0, "Live between-round edit leaked into current round");
beginRound(4, false);
assert(currentRoundDuration() === 2400, "Next round did not receive new duration");
assert(currentRoundBetween() === 20, "Next round did not receive new between-round time");
assert(currentRoundBoardTimingMatches() === true, "Next round board timing snapshot is inconsistent");

// Debug may deliberately rewrite the active round snapshot.
reset({mode:"2",positions:13,minutes:30,between:0,boards:4,boardMinutes:7,boardSeconds:30},{pos:3,running:false,remaining:1200});
snapshotRoundSettings();
s.minutes = 10;
s.between = 25;
s.boards = 9;
s.boardMinutes = 3;
s.boardSeconds = 0;
applyDebugSettingsToCurrentTimer();
assert(st.roundDuration === 600 && st.remaining === 600, "Debug duration change did not apply to the current round");
assert(st.roundBetween === 25, "Debug between-round change did not apply to the current snapshot");
assert(st.roundBoards === 9 && st.roundBoardDuration === 180, "Debug board settings did not apply to the current snapshot");

// A Debug edit that does not alter the round duration must not reset the remaining time.
reset({mode:"2",positions:13,minutes:30,between:0,boards:4,boardMinutes:7,boardSeconds:30},{pos:3,running:false,remaining:777});
snapshotRoundSettings();
st.remaining = 777;
s.between = 12;
applyDebugSettingsToCurrentTimer();
assert(st.remaining === 777, "Debug non-duration edit must not reset the countdown");
assert(st.roundBetween === 12, "Debug non-duration edit must still update the active snapshot");

// Undo must restore the complete timing snapshot of the previous round.
reset({mode:"2",positions:13,minutes:40,between:20,boards:8,boardMinutes:5,boardSeconds:0},{pos:4});
restoreUndoState({
  pos:3, phase:"round", remaining:1234, running:false, started:true,
  roundDuration:1800, roundBetween:0, roundBoardDuration:450,
  roundBoards:4, breakDuration:0, jumpReminderRound:0,
});
assert(st.pos === 3 && st.remaining === 1234, "Undo did not restore the previous tour/time");
assert(currentRoundDuration() === 1800, "Undo did not restore previous round duration");
assert(currentRoundBetween() === 0, "Undo did not restore previous between-round duration");
assert(currentRoundBoardTimingMatches() === true, "Undo did not restore previous board timing");


// Wall-clock alignment rounds the target end time to the nearest real second,
// so the total correction is never more than half a second.
assert(alignedWallDelayMs(100250, 60) === 59750, "Quarter-second start should align backward to the nearest second");
assert(alignedWallDelayMs(100750, 60) === 60250, "Three-quarter-second start should align forward to the nearest second");
assert(Math.abs(alignedWallDelayMs(100499, 60) - 60000) <= 500, "Wall-clock correction exceeded half a second");
assert(Math.abs(alignedWallDelayMs(100501, 60) - 60000) <= 500, "Wall-clock correction exceeded half a second");

// Warnings use fixed remaining-time thresholds. The pre-jump message uses
// the same warning trigger independently of any end-of-round message.
reset({warnMinutes:2,warnSeconds:0,dangerMinutes:1,dangerSeconds:0});
assert(warnThreshold() === 120, "Orange must start with 2 minutes left");
assert(dangerThreshold() === 60, "Red must start with 1 minute left");
s.warnMinutes=0; s.warnSeconds=45;
assert(warnThreshold() === 45, "Fixed warning must support seconds");
s.dangerMinutes=0; s.dangerSeconds=20;
assert(dangerThreshold() === 20, "Fixed red warning must support seconds");

// Temporary screen-preview values must be independent of the real tournament clock.
reset({mode:"4",positions:6,between:0,minutes:30,jumpRound:0,jumpDisplaySecs:15,quickMessage:""},{pos:3,phase:"round",remaining:483,running:true});
const realSettingsJSON=JSON.stringify(s),realStateJSON=JSON.stringify(st);
for(const kind of ["prejump","jump","between","orange","red","pause","roundend","ended","temporary"]){
  const {cfg,v}=buildScreenPreview(kind);
  assert(v.started===true&&v.endAt===null,"Preview "+kind+" must not create any running timer");
  assert(JSON.stringify(s)===realSettingsJSON&&JSON.stringify(st)===realStateJSON,
    "Preview "+kind+" modified the real settings or timer state");
  if(kind==="prejump")assert(cfg.jumpRound>0&&v.phase==="round"&&cfg.jumpAdvanceNotice,"Missing pre-jump notice");
  if(kind==="jump")assert(v.phase==="jump"&&v.remaining>0,"Missing jump countdown");
  if(kind==="between")assert(v.phase==="break"&&v.breakDuration>0,"Missing between-rounds screen");
  if(kind==="orange")assert(v.phase==="round"&&v.remaining===90,"Missing orange warning sample");
  if(kind==="red")assert(v.phase==="round"&&v.remaining===30,"Missing red warning sample");
  if(kind==="pause")assert(v.running===false&&v.phase==="round","Missing paused sample");
  if(kind==="roundend")assert(v.phase==="roundEnd"&&cfg.mode==="4","Missing MP4 ending");
  if(kind==="ended")assert(v.phase==="ended"&&cfg.mode==="2","Missing pairs ending");
  if(kind==="temporary")assert(cfg.quickMessage.length>0,"Missing temporary message");
}

console.log("BridgeTimer state-machine behavior OK");
