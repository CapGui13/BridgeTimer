//go:build windows

package main

import (
 "runtime"
 "syscall"
 "testing"
 "unsafe"
)

func TestWindowedSettingsTimerSameNativeRect(t *testing.T) {
 runtime.LockOSThread()
 defer runtime.UnlockOSThread()
 create:=user32.NewProc("CreateWindowExW")
 destroy:=user32.NewProc("DestroyWindow")
 className:=syscall.StringToUTF16Ptr("STATIC")
 title:=syscall.StringToUTF16Ptr("Bridge Timer stable-window regression")
 const overlappedWindow=0x00CF0000
 hwnd,_,err:=create.Call(0,uintptr(unsafe.Pointer(className)),
   uintptr(unsafe.Pointer(title)),overlappedWindow,45,55,812,520,0,0,0,0)
 runtime.KeepAlive(className);runtime.KeepAlive(title)
 if hwnd==0 {t.Fatalf("unable to create test HWND: %v",err)}
 defer destroy.Call(hwnd)
 oldSerial,oldFullscreen,oldActive:=viewRequestSerial,fullscreen,timerViewActive.Load()
 defer func(){viewRequestSerial=oldSerial;fullscreen=oldFullscreen;timerViewActive.Store(oldActive)}()
 viewRequestSerial=0
 fullscreen=false
 timerViewActive.Store(false)

 rectOf:=func()rect{
   var r rect
   if ok,_,_:=getWindowRect.Call(hwnd,uintptr(unsafe.Pointer(&r)));ok==0{
      t.Fatal("GetWindowRect failed")
   }
   return r
 }
 checkSwitches:=func(label string, serial int64) int64{
   before:=rectOf()
   for _,mode:=range []string{"settings","timer","settings","timer","settings"}{
      serial++
      if !setNativeView(hwnd,mode,serial) {t.Fatalf("%s: rejected %s",label,mode)}
      after:=rectOf()
      if after!=before {t.Fatalf("%s: %s changed native rectangle: before %+v / after %+v",label,mode,before,after)}
   }
   return serial
 }
 serial:=checkSwitches("default 812x520",0)

 for _,size:=range [][4]int32{
   {120,90,960,640},
   {250,130,1100,700},
   {35,45,812,520},
 }{
   ok,_,_:=setWindowPos.Call(hwnd,0,uintptr(size[0]),uintptr(size[1]),
     uintptr(size[2]),uintptr(size[3]),swpNoZOrder|swpNoOwnerZOrder)
   if ok==0 {t.Fatalf("manual test resize to %+v failed",size)}
   serial=checkSwitches("user-sized native window",serial)
 }
 // The state request itself must never resize the window even with native
 // fullscreen flagged; the actual fullscreen toggle has its own Win32 path.
 fullscreen=true
 serial=checkSwitches("in fullscreen",serial)
 fullscreen=false
 serial=checkSwitches("after fullscreen",serial)
 _=serial
}
