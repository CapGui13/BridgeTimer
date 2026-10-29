//go:build windows

package main

import (
 "runtime"
 "syscall"
 "testing"
 "unsafe"
)

// Native integration test: exercise SetWindowPos/GetWindowRect on an actual
// hidden test HWND. This catches mistakes that pure geometry tests cannot.
func TestNativeViewSwitchOnRealHiddenWindow(t *testing.T) {
 runtime.LockOSThread()
 defer runtime.UnlockOSThread()
 className:=syscall.StringToUTF16Ptr("STATIC")
 windowTitle:=syscall.StringToUTF16Ptr("Bridge Timer geometry test")
 create:=user32.NewProc("CreateWindowExW")
 destroy:=user32.NewProc("DestroyWindow")
 const overlappedWindow=0x00CF0000
 hwnd,_,err:=create.Call(0,uintptr(unsafe.Pointer(className)),uintptr(unsafe.Pointer(windowTitle)),
  overlappedWindow,20,20,920,680,0,0,0,0)
 runtime.KeepAlive(className)
 runtime.KeepAlive(windowTitle)
 if hwnd==0 { t.Skipf("test HWND unavailable on this Windows runner: %v",err) }
 defer destroy.Call(hwnd)
 work,ok:=monitorWorkArea(hwnd)
 if !ok { t.Fatal("a real test window has no monitor work area") }
 if work.Right-work.Left<920 || work.Bottom-work.Top<680 {
  t.Skipf("test monitor too small: %+v",work)
 }
 oldSerial,oldHeight,oldFullscreen:=viewRequestSerial,settingsWindowHeight,fullscreen
 oldTimer:=timerViewActive.Load()
 defer func(){
  viewRequestSerial=oldSerial
  settingsWindowHeight=oldHeight
  fullscreen=oldFullscreen
  timerViewActive.Store(oldTimer)
 }()
 fullscreen=false
 viewRequestSerial=0
 timerViewActive.Store(false)
 settingsWindowHeight=680
 if !setNativeView(hwnd,"settings",1) {t.Fatal("initial settings transition failed")}
 if !setNativeView(hwnd,"timer",2) {t.Fatal("timer transition failed")}
 var timerRect rect
 getWindowRect.Call(hwnd,uintptr(unsafe.Pointer(&timerRect)))
 timerWidth:=timerRect.Right-timerRect.Left
 if timerWidth!=920 || timerRect.Bottom-timerRect.Top!=timerOuterHeight(920) {
  t.Fatalf("native timer width/height wrong: %+v",timerRect)
 }
 if !setNativeView(hwnd,"settings",3) {t.Fatal("return to settings failed")}
 var settingsRect rect
 getWindowRect.Call(hwnd,uintptr(unsafe.Pointer(&settingsRect)))
 if settingsRect.Right-settingsRect.Left!=920 || settingsRect.Bottom-settingsRect.Top!=680 {
  t.Fatalf("native settings dimensions not restored: %+v",settingsRect)
 }
 // The user can resize the Settings window; that width must survive both routes.
 moved,_,_:=setWindowPos.Call(hwnd,0,uintptr(30),uintptr(30),uintptr(960),uintptr(680),
    swpNoZOrder|swpNoOwnerZOrder)
 if moved==0 {t.Fatal("manual test resize failed")}
 if !setNativeView(hwnd,"timer",4) || !setNativeView(hwnd,"settings",5) {
  t.Fatal("user-resized window transitions failed")
 }
 getWindowRect.Call(hwnd,uintptr(unsafe.Pointer(&settingsRect)))
 if settingsRect.Right-settingsRect.Left!=960 {
  t.Fatalf("native view switch destroyed user-chosen width: %+v",settingsRect)
 }
}
