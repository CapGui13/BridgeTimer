//go:build windows

package main

import (
	"runtime"
	"syscall"
	"testing"
	"unsafe"
)

// Use an actual Win32 HWND: this tests the style/geometry transition, not
// just an HTML mock. It does not measure DWM's perceived animation on screen.
func TestNativeFullscreenEntryFrameAndReturn(t *testing.T) {
	runtime.LockOSThread()
	defer runtime.UnlockOSThread()
	create := user32.NewProc("CreateWindowExW")
	destroy := user32.NewProc("DestroyWindow")
	cls := syscall.StringToUTF16Ptr("STATIC")
	name := syscall.StringToUTF16Ptr("BridgeTimer DWM entry integration")
	const overlappedWindow = 0x00CF0000
	hwnd, _, err := create.Call(0, uintptr(unsafe.Pointer(cls)),
		uintptr(unsafe.Pointer(name)), overlappedWindow,
		85, 90, 812, 520, 0, 0, 0, 0)
	runtime.KeepAlive(cls)
	runtime.KeepAlive(name)
	if hwnd == 0 { t.Fatalf("could not create HWND: %v", err) }
	defer destroy.Call(hwnd)

	oldFs, oldStyle, oldPlace := fullscreen, savedStyle, savedPlace
	defer func(){ fullscreen = oldFs; savedStyle = oldStyle; savedPlace = oldPlace }()
	fullscreen = false
	originalStyle, _, _ := getWindowLongPtrW.Call(hwnd, ^uintptr(15))
	var original rect
	if ok, _, _ := getWindowRect.Call(hwnd, uintptr(unsafe.Pointer(&original))); ok == 0 {
		t.Fatal("GetWindowRect failed")
	}
	monitor, _, _ := monitorFromWindow.Call(hwnd, monitorDefaultToNearest)
	if monitor == 0 { t.Fatal("no monitor") }
	mi := monitorInfo{CbSize:uint32(unsafe.Sizeof(monitorInfo{}))}
	if ok, _, _ := getMonitorInfoW.Call(monitor,uintptr(unsafe.Pointer(&mi))); ok == 0 {
		t.Fatal("GetMonitorInfoW failed")
	}

	for pass := 0; pass < 2; pass++ {
		if !toggleNativeFullscreen(hwnd) || !fullscreen {
			t.Fatalf("native entry %d failed",pass)
		}
		var full rect
		if ok,_,_ := getWindowRect.Call(hwnd,uintptr(unsafe.Pointer(&full)));ok==0{
			t.Fatal("fullscreen GetWindowRect failed")
		}
		if full!=mi.RcMonitor {
			t.Fatalf("full window geometry %+v should cover monitor %+v",full,mi.RcMonitor)
		}
		fullStyle,_,_ := getWindowLongPtrW.Call(hwnd,^uintptr(15))
		if fullStyle & uintptr(wsCaption|wsThickFrame|wsSysMenu) != 0 {
			t.Fatalf("native frame still visible in fullscreen: %#x",fullStyle)
		}

		if toggleNativeFullscreen(hwnd) || fullscreen {
			t.Fatalf("native exit %d failed",pass)
		}
		restoredStyle,_,_:=getWindowLongPtrW.Call(hwnd,^uintptr(15))
		// SetWindowPlacement can add WS_VISIBLE to a test window that was
		// deliberately created hidden. The actual app is always visible.
		// Compare frame/decorations, not the test HWND visibility bit.
		const wsVisible = uintptr(0x10000000)
		if (restoredStyle^originalStyle)&^wsVisible != 0 {
			t.Fatalf("exit changed original frame style: before %#x, after %#x",originalStyle,restoredStyle)
		}
		var after rect
		getWindowRect.Call(hwnd,uintptr(unsafe.Pointer(&after)))
		if after!=original {
			t.Fatalf("exit did not restore native rectangle: before %+v, after %+v",original,after)
		}
	}
}

// DWM may refuse optional settings on some Windows configurations; the
// application must still work in that case. When DWM supports the attribute,
// its value must be correctly switched off again, without a global OS change.
func TestDwmTransitionSettingIsWindowScoped(t *testing.T) {
	runtime.LockOSThread()
	defer runtime.UnlockOSThread()
	create := user32.NewProc("CreateWindowExW")
	destroy := user32.NewProc("DestroyWindow")
	cls := syscall.StringToUTF16Ptr("STATIC")
	title := syscall.StringToUTF16Ptr("BridgeTimer attribute integration")
	hwnd,_,_:=create.Call(0,uintptr(unsafe.Pointer(cls)),uintptr(unsafe.Pointer(title)),
		0x00CF0000,80,80,812,520,0,0,0,0)
	runtime.KeepAlive(cls);runtime.KeepAlive(title)
	if hwnd==0 {t.Fatal("could not make test HWND")}
	defer destroy.Call(hwnd)
	if setDwmTransitionsDisabled(hwnd,true) {
		read := dwmapi.NewProc("DwmGetWindowAttribute")
		var disabled int32
		hr,_,_:=read.Call(hwnd,dwmTransitionsForcedDisabled,
			uintptr(unsafe.Pointer(&disabled)),unsafe.Sizeof(disabled))
		if int32(hr)==0 && disabled!=1 {t.Fatalf("DWM transition disable not applied: %d",disabled)}
		if !setDwmTransitionsDisabled(hwnd,false) {t.Fatal("DWM attribute failed to restore")}
		disabled=1
		hr,_,_=read.Call(hwnd,dwmTransitionsForcedDisabled,
			uintptr(unsafe.Pointer(&disabled)),unsafe.Sizeof(disabled))
		if int32(hr)==0 && disabled!=0 {t.Fatalf("DWM transition still disabled: %d",disabled)}
	}
}
