package main

import "testing"

func TestDefaultWindowSameRatioOnBothScreens(t *testing.T) {
 if defaultWindowWidth!=960 || defaultWindowHeight!=570 {
  t.Fatalf("Settings and Timer must share one 16:9 native default: got %dx%d",defaultWindowWidth,defaultWindowHeight)
 }
}

func TestTimerWindowOuterHeight(t *testing.T) {
	tests := []struct {
		name string
		outerH int32
		clientW int32
		clientH int32
		want int32
	}{
		{"settings 960x720, 30px frame",720,960,690,570},
		{"user screenshot 812x612, 26px frame",612,812,586,483},
		{"already 16x9 client",570,960,540,570},
		{"large native window",1000,1600,970,930},
		{"invalid",720,0,690,720},
	}
	for _,tc:=range tests {
		t.Run(tc.name,func(t *testing.T) {
			got:=timerWindowOuterHeight(tc.outerH,tc.clientW,tc.clientH)
			if got!=tc.want {t.Fatalf("got %d, want %d",got,tc.want)}
			clientAfter:=got-(tc.outerH-tc.clientH)
			if tc.clientW>0 && tc.clientH>0 && clientAfter<=0 {
				t.Fatalf("invalid resulting client height %d",clientAfter)
			}
		})
	}
}
