//go:build windows

package main

import (
 "runtime"
 "syscall"
 "testing"
 "unsafe"
)

// Test the real Windows full-screen round trip on a disposable native HWND.
// This is deliberately test-only: the validated application is untouched.
func TestFullscreenNativeRoundTripPreservesGeometry(t *testing.T) {
 runtime.LockOSThread()
 defer runtime.UnlockOSThread()
 create:=user32.NewProc("CreateWindowExW")
 destroy:=user32.NewProc("DestroyWindow")
 className:=syscall.StringToUTF16Ptr("STATIC")
 title:=syscall.StringToUTF16Ptr("BridgeTimer fullscreen audit")
 const overlappedWindow=0x00CF0000
 hwnd,_,err:=create.Call(0,uintptr(unsafe.Pointer(className)),uintptr(unsafe.Pointer(title)),
    overlappedWindow,34,42,812,680,0,0,0,0)
 runtime.KeepAlive(className);runtime.KeepAlive(title)
 if hwnd==0 {t.Fatalf("unable to create Win32 audit window: %v",err)}
 defer destroy.Call(hwnd)
 var original rect
 if ok,_,_:=getWindowRect.Call(hwnd,uintptr(unsafe.Pointer(&original)));ok==0 {
  t.Fatal("could not read initial test rectangle")
 }
 oldFullscreen,oldSerial,oldTimer:=fullscreen,viewRequestSerial,timerViewActive.Load()
 oldSavedPlace,oldSavedStyle:=savedPlace,savedStyle
 defer func(){fullscreen=oldFullscreen;viewRequestSerial=oldSerial;timerViewActive.Store(oldTimer);savedPlace=oldSavedPlace;savedStyle=oldSavedStyle}()
 fullscreen=false;viewRequestSerial=0;timerViewActive.Store(false)
 if !setNativeView(hwnd,"settings",1){t.Fatal("settings mode rejected")}
 if !toggleNativeFullscreen(hwnd){t.Fatal("failed to enter native fullscreen")}
 var fsRect rect
 getWindowRect.Call(hwnd,uintptr(unsafe.Pointer(&fsRect)))
 mon,ok:=monitorWorkArea(hwnd)
 if !ok {t.Fatal("no monitor detected while fullscreen")}
 if fsRect.Right-fsRect.Left<defaultWindowWidth || fsRect.Bottom-fsRect.Top<timerWindowHeight {
  t.Fatalf("fullscreen frame collapsed: %+v, monitor work area %+v",fsRect,mon)
 }
 // Switching the visible application screen inside fullscreen must not resize it.
 if !setNativeView(hwnd,"timer",2){t.Fatal("timer screen rejected in fullscreen")}
 var afterTimer rect
 getWindowRect.Call(hwnd,uintptr(unsafe.Pointer(&afterTimer)))
 if afterTimer!=fsRect {t.Fatalf("view change resized the fullscreen frame: before %+v after %+v",fsRect,afterTimer)}
 if toggleNativeFullscreen(hwnd){t.Fatal("fullscreen must be off after exit")}
 // Return to the selected timer layout.
 if !setNativeView(hwnd,"timer",3){t.Fatal("timer resize after fullscreen exit failed")}
 var after rect
 getWindowRect.Call(hwnd,uintptr(unsafe.Pointer(&after)))
 if after.Right-after.Left!=812 || after.Bottom-after.Top!=490 {
  t.Fatalf("timer geometry not restored after fullscreen: %+v",after)
 }
 if !setNativeView(hwnd,"settings",4){t.Fatal("settings after fullscreen failed")}
 getWindowRect.Call(hwnd,uintptr(unsafe.Pointer(&after)))
 if after.Right-after.Left!=812 || after.Bottom-after.Top!=680 {
  t.Fatalf("settings geometry not restored after fullscreen: %+v",after)
 }
}
