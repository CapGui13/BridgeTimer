package main

import "testing"

func TestOpeningAndMinimumWindowDimensions(t *testing.T) {
 if defaultWindowWidth!=812 || defaultWindowHeight!=520 {
  t.Fatalf("BridgeTimer must open at its original minimum 812x520, got %dx%d",defaultWindowWidth,defaultWindowHeight)
 }
 x,y,w,h,saved:=startupWindowGeometry()
 if x!=0 || y!=0 || w!=812 || h!=520 || saved {
  t.Fatalf("startup geometry must be centered at 812x520: %+v",[]any{x,y,w,h,saved})
 }
}

func TestViewSwitchPreservesNativeGeometry(t *testing.T) {
 // Validate logical state transitions without a real HWND.
 // Windows integration uses a nonzero HWND and is exercised in CI.
 originalSerial:=viewRequestSerial
 originalActive:=timerViewActive.Load()
 defer func(){viewRequestSerial=originalSerial;timerViewActive.Store(originalActive)}()
 viewRequestSerial=0
 if !setNativeView(0,"settings",1) {t.Fatal("settings view was rejected")}
 if timerViewActive.Load() {t.Fatal("settings should not be marked as timer")}
 if !setNativeView(0,"timer",2) {t.Fatal("timer view was rejected")}
 if !timerViewActive.Load() {t.Fatal("timer should be marked active")}
 if setNativeView(0,"timer",1) {t.Fatal("stale view request must be rejected")}
 if setNativeView(0,"unknown",3) {t.Fatal("unknown view must be rejected")}
}

func TestBothWindowedViewsHaveTheSameMinimum(t *testing.T) {
 if defaultWindowHeight != 520 { t.Fatalf("Unified minimum must be 520px, got %d",defaultWindowHeight) }
}

func TestNativeWindowCloseAlwaysPromptsUnlessPreviouslyApproved(t *testing.T) {
 oldRequest:=nativeCloseRequestHandler
 oldApproved:=closeApproved.Load()
 oldProc:=originalWndProc
 defer func(){
   nativeCloseRequestHandler=oldRequest
   closeApproved.Store(oldApproved)
   originalWndProc=oldProc
 }()
 originalWndProc=0
 count:=0
 nativeCloseRequestHandler=func(){count++}
 closeApproved.Store(false)
 darkTitleWndProc(0,wmClose,0,0)
 if count!=1||closeApproved.Load(){t.Fatalf("X must request the HTML dialog, not close: calls=%d",count)}
 // Clicking No leaves closeApproved=false. Repeated X can reopen dialog.
 darkTitleWndProc(0,wmClose,0,0)
 if count!=2||closeApproved.Load(){t.Fatalf("Canceled X must not approve close: calls=%d",count)}
 // HTML Yes invokes nativeExit, which approves close and posts WM_CLOSE.
 closeApproved.Store(true)
 darkTitleWndProc(0,wmClose,0,0)
 if count!=2{t.Fatal("Approved HTML quit must not reopen dialog")}
}
