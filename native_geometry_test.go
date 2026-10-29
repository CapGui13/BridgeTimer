package main

import "testing"

// A single Win32 frame is used in both windowed screens. Geometry changes
// are reserved for an actual user resize or the native fullscreen toggle.
func TestSharedWindowedOpeningDimensions(t *testing.T) {
	x,y,width,height,hasSaved:=startupWindowGeometry()
	if x!=0 || y!=0 || width!=812 || height!=520 || hasSaved {
		t.Fatalf("expected centered 812x520 startup; got (%d,%d), %dx%d, saved=%v",x,y,width,height,hasSaved)
	}
}

func TestSwitchingWindowedScreensOnlyChangesActiveView(t *testing.T) {
	oldSerial,oldView:=viewRequestSerial,timerViewActive.Load()
	defer func(){viewRequestSerial=oldSerial;timerViewActive.Store(oldView)}()
	viewRequestSerial=0
	if !setNativeView(0,"settings",1) || timerViewActive.Load() {
		t.Fatal("settings mode failed")
	}
	if !setNativeView(0,"timer",2) || !timerViewActive.Load() {
		t.Fatal("timer mode failed")
	}
	if !setNativeView(0,"settings",3) || timerViewActive.Load() {
		t.Fatal("return to settings failed")
	}
	if setNativeView(0,"timer",2) {t.Fatal("stale view request accepted")}
	if setNativeView(0,"invalid",4) {t.Fatal("invalid mode accepted")}
}

func TestSharedWindowedMinimum(t *testing.T) {
	if defaultWindowWidth!=812 || defaultWindowHeight!=520 {
		t.Fatalf("minimum must match common frame, got %dx%d",defaultWindowWidth,defaultWindowHeight)
	}
}
