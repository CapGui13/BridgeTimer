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
  "transitionAfterRound",
];

let s = {};
let st = {};
function releaseWakeLock() {}
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

// Zero-second Mitchell jump starts next round immediately and preserves a reminder.
reset({mode:"2",positions:13,between:0,jumpRound:6,minutes:15,boards:2},{pos:6});
snapshotRoundSettings();
assert(transitionAfterRound() === true, "Zero-second jump should continue immediately");
assert(st.phase === "round" && st.pos === 7, "Zero-second jump must enter round 7");
assert(st.jumpReminderRound === 7, "Zero-second jump reminder must target the new round");
assert(st.remaining === 900, "New round must start with its full snapshotted duration");

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

console.log("BridgeTimer state-machine behavior OK");
