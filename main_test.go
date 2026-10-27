package main

import "testing"

func TestOpeningAndMinimumWindowDimensions(t *testing.T) {
 if defaultWindowWidth!=812 || defaultWindowHeight!=612 {
  t.Fatalf("BridgeTimer must open at its original minimum 812x612, got %dx%d",defaultWindowWidth,defaultWindowHeight)
 }
 x,y,w,h,saved:=startupWindowGeometry()
 if x!=0 || y!=0 || w!=812 || h!=612 || saved {
  t.Fatalf("startup geometry must be centered at 812x612: %+v",[]any{x,y,w,h,saved})
 }
}

func TestViewSwitchPreservesNativeGeometry(t *testing.T) {
 // No native Win32 resize should be attempted when switching views.
 // A zero HWND is intentionally passed: it is safe only while the
 // view-switch implementation never calls SetWindowPos/GetWindowRect.
 originalSerial:=viewRequestSerial
 originalActive:=timerViewActive.Load()
 defer func(){viewRequestSerial=originalSerial;timerViewActive.Store(originalActive)}()
 viewRequestSerial=0
 if !setNativeView(0,"settings",1) {t.Fatal("settings view was rejected")}
 if !setNativeView(0,"timer",2) {t.Fatal("timer view was rejected")}
 if setNativeView(0,"timer",1) {t.Fatal("stale view request must be rejected")}
 if setNativeView(0,"unknown",3) {t.Fatal("unknown view must be rejected")}
}

func TestNativeWindowCloseAlwaysPromptsUnlessPreviouslyApproved(t *testing.T) {
 oldConfirm:=nativeCloseConfirmation
 oldApproved:=closeApproved.Load()
 oldProc:=originalWndProc
 defer func(){
   nativeCloseConfirmation=oldConfirm
   closeApproved.Store(oldApproved)
   originalWndProc=oldProc
 }()
 originalWndProc=0
 count:=0
 nativeCloseConfirmation=func(hwnd uintptr) bool { count++;return false }
 closeApproved.Store(false)
 darkTitleWndProc(0,wmClose,0,0)
 if count!=1||closeApproved.Load(){t.Fatalf("Cancel X must preserve window and prompt once: calls=%d",count)}
 nativeCloseConfirmation=func(hwnd uintptr) bool { count++;return true }
 darkTitleWndProc(0,wmClose,0,0)
 if count!=2||!closeApproved.Load(){t.Fatalf("Yes X must approve closing: calls=%d",count)}
 darkTitleWndProc(0,wmClose,0,0)
 if count!=2{t.Fatal("Already confirmed app quit must not prompt twice")}
}
