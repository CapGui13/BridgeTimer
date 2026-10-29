package main

import "testing"

// Rectangles use native outer-window pixel dimensions, matching SetWindowPos.
func TestTimerOuterHeightScalesWithUserWidth(t *testing.T) {
	cases := []struct{width, height int32}{
		{812,490}, {960,573}, {1100,652}, {1280,753},
	}
	for _, c := range cases {
		if got:=timerOuterHeight(c.width); got!=c.height {
			t.Errorf("timer width %d: height %d, want %d",c.width,got,c.height)
		}
	}
}

func TestNativeViewPreservesChosenWidthAndSettingsHeight(t *testing.T) {
	work:=rect{Left:0,Top:0,Right:1920,Bottom:1040}
	settings:=rect{Left:140,Top:90,Right:1240,Bottom:890}
	timer:=planNativeViewRect(settings,work,"timer",800)
	if timer.Right-timer.Left!=1100 || timer.Bottom-timer.Top!=652 {
		t.Fatalf("1100px width not preserved on Timer: %+v",timer)
	}
	if timer.Left!=settings.Left || timer.Top!=settings.Top {
		t.Fatalf("unnecessary origin change: %+v",timer)
	}
	back:=planNativeViewRect(timer,work,"settings",800)
	if back.Right-back.Left!=1100 || back.Bottom-back.Top!=800 {
		t.Fatalf("settings height/width not restored: %+v",back)
	}
}

func TestNativeViewRecomputesTimerAtDifferentWidths(t *testing.T) {
	work:=rect{Left:0,Top:0,Right:2400,Bottom:1400}
	sizes:=[]int32{812,960,1100,1440}
	for _,width:=range sizes {
		in:=rect{Left:20,Top:40,Right:20+width,Bottom:720}
		result:=planNativeViewRect(in,work,"timer",680)
		if result.Right-result.Left!=width { t.Fatalf("%dpx width changed to %+v",width,result) }
		if result.Bottom-result.Top!=timerOuterHeight(width) { t.Fatalf("%dpx timer height invalid: %+v",width,result) }
	}
}

func TestNativeViewClampsToVisibleMonitorWorkArea(t *testing.T) {
	work:=rect{Left:0,Top:0,Right:1366,Bottom:728}
	in:=rect{Left:1050,Top:570,Right:2150,Bottom:1250}
	timer:=planNativeViewRect(in,work,"timer",680)
	if timer.Left<work.Left || timer.Right>work.Right || timer.Top<work.Top || timer.Bottom>work.Bottom {
		t.Fatalf("timer went offscreen: %+v",timer)
	}
	if timer.Right-timer.Left != 1100 {t.Fatalf("width changed despite room to reposition: %+v",timer)}
	settings:=planNativeViewRect(timer,work,"settings",680)
	if settings.Left<work.Left || settings.Right>work.Right || settings.Top<work.Top || settings.Bottom>work.Bottom {
		t.Fatalf("settings went offscreen: %+v",settings)
	}
	if settings.Right-settings.Left!=1100 || settings.Bottom-settings.Top!=680 {
		t.Fatalf("settings dimensions changed: %+v",settings)
	}
}

func TestNativeViewClampsWidthOnlyWhenMonitorCannotFitIt(t *testing.T) {
	work:=rect{Left:0,Top:0,Right:1024,Bottom:768}
	in:=rect{Left:0,Top:0,Right:1500,Bottom:680}
	timer:=planNativeViewRect(in,work,"timer",680)
	if timer.Right-timer.Left!=1024 { t.Fatalf("expected work-area width cap: %+v",timer) }
	if timer.Bottom-timer.Top!=timerOuterHeight(1024) {
		t.Fatalf("timer must recalculate height after width cap: %+v",timer)
	}
}

func TestNativeViewHandlesSecondaryMonitorWithNegativeOrigin(t *testing.T) {
	work:=rect{Left:-1920,Top:-200,Right:0,Bottom:880}
	in:=rect{Left:-1150,Top:610,Right:-150,Bottom:1390}
	out:=planNativeViewRect(in,work,"settings",680)
	if out.Left < work.Left || out.Right > work.Right || out.Top < work.Top || out.Bottom > work.Bottom {
		t.Fatalf("secondary display bounds not respected: %+v",out)
	}
	if out.Right-out.Left != 1000 { t.Fatalf("user's 1000px width lost: %+v",out) }
}

func TestNativeViewMinimaAreEnforcedInPlanning(t *testing.T) {
	work:=rect{Left:0,Top:0,Right:1600,Bottom:1000}
	in:=rect{Left:0,Top:0,Right:600,Bottom:450}
	for _,mode:=range []string{"timer","settings"} {
		result:=planNativeViewRect(in,work,mode,500)
		if result.Right-result.Left<812 {t.Fatalf("%s width below minimum: %+v",mode,result)}
		minimum:=int32(680)
		if mode=="timer" {minimum=490}
		if result.Bottom-result.Top < minimum {t.Fatalf("%s height below minimum: %+v",mode,result)}
	}
}
