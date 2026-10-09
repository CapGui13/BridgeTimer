from pathlib import Path
import subprocess
import os
import stat

cache = Path(subprocess.check_output(['go','env','GOMODCACHE'], text=True).strip())
roots = list((cache / 'github.com' / 'jchv').glob('go-webview2@*'))
if not roots:
    raise SystemExit('go-webview2 module not found')
p = roots[0] / 'webview.go'
os.chmod(p, stat.S_IWRITE)
src = p.read_text(encoding='utf-8')

options_marker = '''type WindowOptions struct {
	Title  string
	Width  uint
	Height uint
	IconId uint
	Center bool
}'''
create_marker = 'func (w *webview) CreateWithOptions(opts WindowOptions) bool {'
show_marker = '_, _, _ = w32.User32ShowWindow.Call(w.hwnd, w32.SWShow)'
if create_marker not in src or show_marker not in src:
    raise SystemExit('go-webview2 markers not found')

if 'UsePosition bool' not in src:
    if options_marker not in src:
        raise SystemExit('go-webview2 WindowOptions marker not found')
    src = src.replace(options_marker, '''type WindowOptions struct {
	Title       string
	Width       uint
	Height      uint
	IconId      uint
	Center      bool
	X           int
	Y           int
	UsePosition bool
}''', 1)

old_position = '''	var posX, posY uint
	if opts.Center {
		// get screen size
		screenWidth, _, _ := w32.User32GetSystemMetrics.Call(w32.SM_CXSCREEN)
		screenHeight, _, _ := w32.User32GetSystemMetrics.Call(w32.SM_CYSCREEN)
		// calculate window position
		posX = (uint(screenWidth) - windowWidth) / 2
		posY = (uint(screenHeight) - windowHeight) / 2
	} else {
		// use default position
		posX = w32.CW_USEDEFAULT
		posY = w32.CW_USEDEFAULT
	}'''
new_position = '''	var posX, posY uint
	if opts.UsePosition {
		posX = uint(opts.X)
		posY = uint(opts.Y)
	} else if opts.Center {
		// get screen size
		screenWidth, _, _ := w32.User32GetSystemMetrics.Call(w32.SM_CXSCREEN)
		screenHeight, _, _ := w32.User32GetSystemMetrics.Call(w32.SM_CYSCREEN)
		// calculate window position
		posX = (uint(screenWidth) - windowWidth) / 2
		posY = (uint(screenHeight) - windowHeight) / 2
	} else {
		// use default position
		posX = w32.CW_USEDEFAULT
		posY = w32.CW_USEDEFAULT
	}'''
if 'if opts.UsePosition {' not in src:
    if old_position not in src:
        raise SystemExit('go-webview2 position marker not found')
    src = src.replace(old_position, new_position, 1)

dark_helper = r'''func applyBridgeTimerDarkBeforeShow(hwnd uintptr) {
    dll := windows.NewLazySystemDLL("dwmapi.dll")
    proc := dll.NewProc("DwmSetWindowAttribute")
    enabled := int32(1)
    _, _, _ = proc.Call(hwnd, 20, uintptr(unsafe.Pointer(&enabled)), unsafe.Sizeof(enabled))
    caption := uint32(0x0025140D)
    text := uint32(0x00FCFAF8)
    border := uint32(0x00554433)
    _, _, _ = proc.Call(hwnd, 35, uintptr(unsafe.Pointer(&caption)), unsafe.Sizeof(caption))
    _, _, _ = proc.Call(hwnd, 36, uintptr(unsafe.Pointer(&text)), unsafe.Sizeof(text))
    _, _, _ = proc.Call(hwnd, 34, uintptr(unsafe.Pointer(&border)), unsafe.Sizeof(border))
}

'''

brush_helper = r'''func bridgeTimerDarkBrush() windows.Handle {
    dll := windows.NewLazySystemDLL("gdi32.dll")
    proc := dll.NewProc("CreateSolidBrush")
    brush, _, _ := proc.Call(0x002A170F)
    return windows.Handle(brush)
}

'''

if 'func applyBridgeTimerDarkBeforeShow' not in src:
    src = src.replace(create_marker, dark_helper + create_marker, 1)
if 'func bridgeTimerDarkBrush' not in src:
    src = src.replace(create_marker, brush_helper + create_marker, 1)

# Disable WebView2's own browser accelerator handling so application
# shortcuts such as F1 are consistently delivered to the page even when
# the window is not in native fullscreen.
accelerator_marker = '''	err = settings.PutAreDevToolsEnabled(options.Debug)
	if err != nil {
		log.Fatal(err)
	}
'''
accelerator_patch = accelerator_marker + '''	err = settings.PutAreBrowserAcceleratorKeysEnabled(false)
	if err != nil {
		log.Printf("disable browser accelerators: %v", err)
	}
'''
if 'PutAreBrowserAcceleratorKeysEnabled(false)' not in src:
    if accelerator_marker not in src:
        raise SystemExit('go-webview2 accelerator settings marker not found')
    src = src.replace(accelerator_marker, accelerator_patch, 1)


# Handle F1 at the WebView2 controller level. This is more reliable than a
# DOM keydown listener when the native window is maximized by Windows.
chromium_marker = '''	chromium := edge.NewChromium()
	chromium.MessageCallback = w.msgcb
'''
chromium_patch = '''	chromium := edge.NewChromium()
	chromium.MessageCallback = w.msgcb
	chromium.AcceleratorKeyCallback = func(key uint) bool {
		if key != 0x70 { // VK_F1
			return false
		}
		chromium.Eval(`(function(){var t=document.getElementById("timer"),h=document.getElementById("hint");if(t&&h&&!t.classList.contains("hidden"))h.classList.toggle("hintVisible");})()`)
		return true
	}
'''
if 'chromium.AcceleratorKeyCallback = func(key uint) bool' not in src:
    if chromium_marker not in src:
        raise SystemExit('go-webview2 Chromium creation marker not found')
    src = src.replace(chromium_marker, chromium_patch, 1)


wc_marker = '''		HIconSm:       windows.Handle(icon),
		LpfnWndProc:   windows.NewCallback(wndproc),'''
if 'HbrBackground: bridgeTimerDarkBrush()' not in src:
    if wc_marker not in src:
        raise SystemExit('go-webview2 background marker not found')
    src = src.replace(wc_marker, '''		HIconSm:       windows.Handle(icon),
		HbrBackground: bridgeTimerDarkBrush(),
		LpfnWndProc:   windows.NewCallback(wndproc),''', 1)

show_with_dark = 'applyBridgeTimerDarkBeforeShow(w.hwnd)\n\t' + show_marker
if show_with_dark not in src:
    src = src.replace(show_marker, show_with_dark, 1)
p.write_text(src, encoding='utf-8')
print('Patched:', p)
