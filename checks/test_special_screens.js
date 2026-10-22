// Regression: special screens have a single readable headline and no misleading 00:00.
const fs=require('node:fs'),assert=require('node:assert/strict');
const html=fs.readFileSync('timer.html','utf8');
function contains(s){assert.ok(html.includes(s),'Missing special-screen rule: '+s)}
contains('#timer.roundEndState #clock,#timer.endState #clock');
contains('#timer.roundEndState #status,#timer.endState #status');
contains('#timer.roundEndState #submsg,#timer.endState #submsg');
contains('#timer.breakState #msg{top:71.5%');
contains('#timer.breakState #submsg{top:87%');
contains('#jumpSplash.on{display:grid');
contains('grid-template-rows:auto minmax(0,1fr) auto auto');
contains('function fitSplashText()');
contains('fc();fitRoundNotice();fitSplashText()');
contains('#pauseOverlay .pauseSmall{font-size:clamp(25px');
contains('if((_sps?screenPreviewKind==="temporary":tempMessageActive())&&st.phase!=="ended"&&st.phase!=="round"&&st.phase!=="break"&&st.phase!=="roundEnd")');
contains('temporary||"CHANGEZ DE TABLE"');
contains('st.pos<s.positions?"Le tour suivant sera relancé par l’arbitre":"Dernier tour terminé"');
assert.ok(!html.includes('$("#never")'));
assert.ok(!html.includes('$("msg").textContent="Fin du tour"'));
assert.ok(!html.includes('$("msg").textContent="Fin de la séance"'));
assert.ok(!html.includes('else if(isRoundEnd){heading="FIN DU TOUR";main="Fin du tour"'));
console.log('Special screen hierarchy regression OK');
