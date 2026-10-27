package main

import (
	"context"
	_ "embed"
	"encoding/json"
	"errors"
	"fmt"
	"log"
	"net"
	"net/http"
	"os"
	"path/filepath"
	"runtime"
	"strings"
	"sync"
	"sync/atomic"
	"syscall"
	"time"
	"unicode/utf16"
	"unsafe"

	webview "github.com/jchv/go-webview2"
)

//go:embed timer.html
var timerHTML []byte

const (
	appTitle = "Bridge Timer"
	appVersion = "1.7.8"
	host = "127.0.0.1"
	port = 43831
	defaultWindowWidth = 960
	defaultWindowHeight = 570

	wsCaption = 0x00C00000
	wsThickFrame = 0x00040000
	wsMinimizeBox = 0x00020000
	wsMaximizeBox = 0x00010000
	wsSysMenu = 0x00080000

	monitorDefaultToNearest = 2
	swpNoSize = 0x0001
	swpNoMove = 0x0002
	swpNoZOrder = 0x0004
	swpFrameChanged = 0x0020
	swpNoOwnerZOrder = 0x0200

	gwlpWndProc = ^uintptr(3) // -4
	wmActivate = 0x0006
	wmShowWindow = 0x0018
	wmClose = 0x0010
	wmThemeChanged = 0x031A
	wmGetMinMaxInfo = 0x0024
	wmAppDarkTitle = 0x8061
	waInactive = 0
)

type point struct{ X, Y int32 }
type rect struct{ Left, Top, Right, Bottom int32 }
type minMaxInfo struct { PtReserved, PtMaxSize, PtMaxPosition, PtMinTrackSize, PtMaxTrackSize point }
type windowPlacement struct {
	Length uint32
	Flags uint32
	ShowCmd uint32
	PtMinPosition point
	PtMaxPosition point
	RcNormalPosition rect
}
type monitorInfo struct {
	CbSize uint32
	RcMonitor rect
	RcWork rect
	DwFlags uint32
}

type openFileNameW struct {
	LStructSize       uint32
	HwndOwner         uintptr
	HInstance         uintptr
	LpstrFilter       *uint16
	LpstrCustomFilter *uint16
	NMaxCustFilter    uint32
	NFilterIndex      uint32
	LpstrFile         *uint16
	NMaxFile          uint32
	LpstrFileTitle    *uint16
	NMaxFileTitle     uint32
	LpstrInitialDir   *uint16
	LpstrTitle        *uint16
	Flags             uint32
	NFileOffset       uint16
	NFileExtension    uint16
	LpstrDefExt       *uint16
	LCustData         uintptr
	LpfnHook          uintptr
	LpTemplateName    *uint16
	PvReserved        uintptr
	DwReserved        uint32
	FlagsEx           uint32
}


var (
	kernel32 = syscall.NewLazyDLL("kernel32.dll")
	user32 = syscall.NewLazyDLL("user32.dll")
	dwmapi = syscall.NewLazyDLL("dwmapi.dll")
	comdlg32 = syscall.NewLazyDLL("comdlg32.dll")
	getWindowLongPtrW = user32.NewProc("GetWindowLongPtrW")
	setWindowLongPtrW = user32.NewProc("SetWindowLongPtrW")
	getWindowPlacement = user32.NewProc("GetWindowPlacement")
	setWindowPlacement = user32.NewProc("SetWindowPlacement")
	monitorFromWindow = user32.NewProc("MonitorFromWindow")
	getMonitorInfoW = user32.NewProc("GetMonitorInfoW")
	setWindowPos = user32.NewProc("SetWindowPos")
	callWindowProcW = user32.NewProc("CallWindowProcW")
	postMessageW = user32.NewProc("PostMessageW")
	findWindowW = user32.NewProc("FindWindowW")
	showWindow = user32.NewProc("ShowWindow")
	setForegroundWindow = user32.NewProc("SetForegroundWindow")
	messageBoxW = user32.NewProc("MessageBoxW")
	setProcessDpiAwarenessContext = user32.NewProc("SetProcessDpiAwarenessContext")
	setProcessDPIAware = user32.NewProc("SetProcessDPIAware")
	moveMemory = kernel32.NewProc("RtlMoveMemory")
	getWindowRect = user32.NewProc("GetWindowRect")
	getClientRect = user32.NewProc("GetClientRect")
	isZoomed = user32.NewProc("IsZoomed")
	createMutexW = kernel32.NewProc("CreateMutexW")
	closeHandle = kernel32.NewProc("CloseHandle")
	setThreadExecutionState = kernel32.NewProc("SetThreadExecutionState")
	dwmSetWindowAttribute = dwmapi.NewProc("DwmSetWindowAttribute")
	getSaveFileNameW = comdlg32.NewProc("GetSaveFileNameW")

	fullscreenMu sync.Mutex
	fullscreen bool
	// Settings keeps its original native height. Timer needs a 16:9 CLIENT
	// area; resizing the native window is the only way to avoid letterboxing
	// without distorting the same 1600x900 timer layout.
	timerViewActive atomic.Bool
	viewRequestSerial int64
	nativeClientCalibrated bool
	settingsWindowRect rect
	settingsWindowRectValid bool
	savedStyle uintptr
	savedPlace windowPlacement

	originalWndProc uintptr
	darkWndProcCallback uintptr

	instanceMutex uintptr

	awakeMu sync.Mutex
	nativeAwake bool
	logFile *os.File
	stateFileMu sync.Mutex
	// Close-request handshake: Windows asks, JS confirms, then nativeExit posts WM_CLOSE.
	closePromptPending atomic.Bool
	closeRequestAt atomic.Int64
	closeApproved atomic.Bool
)

func showStartupError(message string) {
	title, _ := syscall.UTF16PtrFromString(appTitle)
	body, _ := syscall.UTF16PtrFromString(message)
	messageBoxW.Call(
		0,
		uintptr(unsafe.Pointer(body)),
		uintptr(unsafe.Pointer(title)),
		0x00000010, // MB_ICONERROR
	)
}

func configureWebView2Rendering() {
	const flag = "--disable-lcd-text"
	_ = os.Setenv("WEBVIEW2_DEFAULT_BACKGROUND_COLOR", "FF0F172A")
	current := strings.TrimSpace(os.Getenv("WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS"))
	if current == "" {
		_ = os.Setenv("WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS", flag)
		return
	}
	if !strings.Contains(current, flag) {
		_ = os.Setenv("WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS", current+" "+flag)
	}
}

func enableNativeDPIAwareness() {
	// WebView2 must be created by a DPI-aware process. Otherwise Windows can
	// bitmap-scale the whole composition surface, which visibly stair-steps
	// the huge timer digits on 125%/150% displays.
	const perMonitorAwareV2 = ^uintptr(3) // DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2 (-4)
	if err := setProcessDpiAwarenessContext.Find(); err == nil {
		if ok, _, _ := setProcessDpiAwarenessContext.Call(perMonitorAwareV2); ok != 0 {
			return
		}
	}
	// Fallback for older Windows.
	if err := setProcessDPIAware.Find(); err == nil {
		setProcessDPIAware.Call()
	}
}

func setNativeAwake(on bool) bool {
	const (
		esSystemRequired  = uintptr(0x00000001)
		esDisplayRequired = uintptr(0x00000002)
		esContinuous      = uintptr(0x80000000)
	)
	flags := esContinuous
	if on {
		flags |= esSystemRequired | esDisplayRequired
	}
	r, _, _ := setThreadExecutionState.Call(flags)
	if r == 0 {
		return false
	}
	awakeMu.Lock()
	nativeAwake = on
	awakeMu.Unlock()
	log.Printf("anti-sleep: %t", on)
	return true
}

func isNativeAwake() bool {
	awakeMu.Lock()
	defer awakeMu.Unlock()
	return nativeAwake
}

func logPath() string {
	return filepath.Join(appDataPath(), "BridgeTimer.log")
}

func initLogging() func() {
	path := logPath()
	if fi, err := os.Stat(path); err == nil && fi.Size() > 1024*1024 {
		bak := path + ".bak"
		_ = os.Remove(bak)
		_ = os.Rename(path, bak)
	}
	f, err := os.OpenFile(path, os.O_CREATE|os.O_WRONLY|os.O_APPEND, 0600)
	if err != nil {
		return func() {}
	}
	logFile = f
	log.SetOutput(f)
	log.SetFlags(log.Ldate | log.Ltime | log.Lmicroseconds)
	log.Printf("Bridge Timer %s starting", appVersion)
	return func() {
		log.Printf("Bridge Timer %s stopping", appVersion)
		_ = f.Sync()
		_ = f.Close()
		logFile = nil
	}
}

func tailLogLines(maxLines int) string {
	b, err := os.ReadFile(logPath())
	if err != nil {
		return ""
	}
	lines := strings.Split(strings.ReplaceAll(string(b), "\r\n", "\n"), "\n")
	if len(lines) > maxLines {
		lines = lines[len(lines)-maxLines:]
	}
	return strings.TrimSpace(strings.Join(lines, "\n"))
}

func appDataPath() string {
	base := os.Getenv("LOCALAPPDATA")
	if base == "" {
		base = os.TempDir()
	}
	p := filepath.Join(base, "BridgeTimerWebView2")
	_ = os.MkdirAll(p, 0700)
	return p
}

func acquireSingleInstance() bool {
	name, _ := syscall.UTF16FromString("Local\\BridgeTimerWebView2")
	h, _, err := createMutexW.Call(0, 0, uintptr(unsafe.Pointer(&name[0])))
	if h == 0 {
		return true
	}
	if err == syscall.Errno(183) {
		title, _ := syscall.UTF16FromString(appTitle)
		wnd, _, _ := findWindowW.Call(0, uintptr(unsafe.Pointer(&title[0])))
		if wnd != 0 {
			showWindow.Call(wnd, 9) // SW_RESTORE
			setForegroundWindow.Call(wnd)
		}
		closeHandle.Call(h)
		return false
	}
	instanceMutex = h
	return true
}

func releaseSingleInstance() {
	if instanceMutex != 0 {
		closeHandle.Call(instanceMutex)
		instanceMutex = 0
	}
}

func startupWindowGeometry() (int32, int32, uint, uint, bool) {
	// Always open Bridge Timer centered, regardless of where the previous
	// session's window was moved. Settings and timer now share one native
	// 16:9 CLIENT area, including the Windows caption in outer dimensions.
	// Settings remain scrollable and their fixed footer stays on top.
	// Native DPI scales the starting logical dimensions.
	return 0, 0, defaultWindowWidth, defaultWindowHeight, false
}

func applyDarkTitleBar(hwnd uintptr) {
	enabled := int32(1)
	for _, attr := range []uintptr{20, 19} {
		r, _, _ := dwmSetWindowAttribute.Call(hwnd, attr, uintptr(unsafe.Pointer(&enabled)), unsafe.Sizeof(enabled))
		if r == 0 {
			break
		}
	}
	caption := uint32(0x0025140D)
	text := uint32(0x00FCFAF8)
	border := uint32(0x00554433)
	dwmSetWindowAttribute.Call(hwnd, 35, uintptr(unsafe.Pointer(&caption)), unsafe.Sizeof(caption))
	dwmSetWindowAttribute.Call(hwnd, 36, uintptr(unsafe.Pointer(&text)), unsafe.Sizeof(text))
	dwmSetWindowAttribute.Call(hwnd, 34, uintptr(unsafe.Pointer(&border)), unsafe.Sizeof(border))
	setWindowPos.Call(hwnd, 0, 0, 0, 0, 0, swpNoMove|swpNoSize|swpNoZOrder|swpNoOwnerZOrder|swpFrameChanged)
}

// A second Windows close request after 12 seconds without a WebView
// acknowledgement provides a last-resort escape when the UI is frozen.
// Normal closes still always use the user's custom HTML confirmation.
func confirmUnresponsiveExit(hwnd uintptr) bool {
	text, _ := syscall.UTF16PtrFromString("BridgeTimer ne répond pas à la demande de fermeture.\n\nForcer la fermeture ? Le tournoi en cours sera interrompu.")
	title, _ := syscall.UTF16PtrFromString("BridgeTimer - Fermeture de secours")
	response, _, _ := messageBoxW.Call(hwnd, uintptr(unsafe.Pointer(text)), uintptr(unsafe.Pointer(title)), 0x00000024) // MB_YESNO | MB_ICONQUESTION
	return response == 6 // IDYES
}


/*
 * Stable single-view native window geometry.
 * Timer AND Settings share exactly one 16:9 CLIENT rectangle, so switching
 * screens must NEVER change native window dimensions or position.
 * The starter's 960x570 outer dimensions only approximate Windows decorations;
 * first loaded Settings view aligns the real client ratio once, via Win32.
 * Fullscreen is handled independently by toggleNativeFullscreen.
 * Serial guards drop stale asynchronous view requests.
 */
func timerWindowOuterHeight(outerHeight, clientWidth, clientHeight int32) int32 {
	if outerHeight <= 0 || clientWidth <= 0 || clientHeight <= 0 {
		return outerHeight
	}
	targetClientHeight := (clientWidth*9 + 8)/16
	return targetClientHeight + outerHeight - clientHeight
}

func setNativeView(hwnd uintptr, requested string, serial int64) bool {
	if requested != "timer" && requested != "settings" { return false }
	fullscreenMu.Lock()
	defer fullscreenMu.Unlock()
	if serial <= viewRequestSerial { return false }
	viewRequestSerial = serial
	// Preserve existing WM_GETMINMAXINFO support in both views.
	timerViewActive.Store(true)
	if fullscreen { return true }
	if nativeClientCalibrated { return true } // no native resize on screen transitions
	zoomed, _, _ := isZoomed.Call(hwnd)
	if zoomed != 0 { return true }
	var wr, cr rect
	okW, _, _ := getWindowRect.Call(hwnd, uintptr(unsafe.Pointer(&wr)))
	okC, _, _ := getClientRect.Call(hwnd, uintptr(unsafe.Pointer(&cr)))
	if okW == 0 || okC == 0 { return false }
	oldWidth := wr.Right - wr.Left
	oldHeight := wr.Bottom - wr.Top
	desiredHeight := timerWindowOuterHeight(oldHeight, cr.Right-cr.Left, cr.Bottom-cr.Top)
	// Only the initial native-client calibration may change its geometry.
	// Thereafter, both views compute the same target and do nothing.
	if desiredHeight < 200 || desiredHeight > 10000 { return false }
	if diff := desiredHeight-oldHeight; diff >= -1 && diff <= 1 { nativeClientCalibrated=true; return true }
	y := wr.Top + (oldHeight-desiredHeight)/2
	ok, _, _ := setWindowPos.Call(hwnd, 0,
		uintptr(wr.Left), uintptr(y), uintptr(oldWidth), uintptr(desiredHeight),
		swpNoZOrder|swpNoOwnerZOrder|swpFrameChanged)
	if ok != 0 {
		nativeClientCalibrated=true
		log.Printf("one-time 16:9 client calibration (%s): %dx%d -> %dx%d",requested,oldWidth,oldHeight,oldWidth,desiredHeight)
	}
	return ok != 0
}

func darkTitleWndProc(hwnd, msg, wp, lp uintptr) uintptr {
	// The native X / Alt+F4 must not destroy the WebView before the HTML
	// confirmation. Never invoke COM/WebView code from this Windows callback.
	if msg == wmClose && !closeApproved.Load() {
		now := time.Now().UnixMilli()
		if closePromptPending.CompareAndSwap(false, true) {
			closeRequestAt.Store(now)
			return 0
		}
		first := closeRequestAt.Load()
		if first == 0 || now-first < 12000 {
			return 0
		}
		// WebView did not consume a close request for 12 seconds.
		closePromptPending.Store(false)
		closeRequestAt.Store(0)
		if !confirmUnresponsiveExit(hwnd) {
			return 0
		}
		closeApproved.Store(true)
	}
	if msg == wmGetMinMaxInfo {
		// Both settings and timer use the same 16:9 client-area minimum.
		// Adjust Win32's min-track height to the actual decorated frame.
		var result uintptr
		if originalWndProc != 0 {
			result, _, _ = callWindowProcW.Call(originalWndProc, hwnd, msg, wp, lp)
		}
		if timerViewActive.Load() && lp != 0 {
			mm := minMaxInfo{}
			// WM_GETMINMAXINFO gives us a native pointer (LPARAM).
			// Copy through Kernel32 rather than casting uintptr to
			// unsafe.Pointer: the latter is correctly rejected by go vet.
			moveMemory.Call(uintptr(unsafe.Pointer(&mm)),lp,unsafe.Sizeof(mm))
			var wr, cr rect
			ow, _, _ := getWindowRect.Call(hwnd,uintptr(unsafe.Pointer(&wr)))
			oc, _, _ := getClientRect.Call(hwnd,uintptr(unsafe.Pointer(&cr)))
			if ow != 0 && oc != 0 {
				frameW := (wr.Right-wr.Left)-(cr.Right-cr.Left)
				frameH := (wr.Bottom-wr.Top)-(cr.Bottom-cr.Top)
				minClientW := mm.PtMinTrackSize.X-frameW
				if minClientW > 0 {
					mm.PtMinTrackSize.Y = (minClientW*9+8)/16+frameH
				}
				moveMemory.Call(lp,uintptr(unsafe.Pointer(&mm)),unsafe.Sizeof(mm))
			}
		}
		return result
	}
	switch msg {
	case wmActivate:
		if wp&0xFFFF != waInactive {
			postMessageW.Call(hwnd, wmAppDarkTitle, 0, 0)
		}
	case wmShowWindow, wmThemeChanged:
		postMessageW.Call(hwnd, wmAppDarkTitle, 0, 0)
	case wmAppDarkTitle:
		applyDarkTitleBar(hwnd)
	}
	if originalWndProc != 0 {
		r, _, _ := callWindowProcW.Call(originalWndProc, hwnd, msg, wp, lp)
		return r
	}
	return 0
}

func installDarkTitleHook(hwnd uintptr) {
	if darkWndProcCallback == 0 {
		darkWndProcCallback = syscall.NewCallback(darkTitleWndProc)
	}
	if originalWndProc == 0 {
		prev, _, _ := setWindowLongPtrW.Call(hwnd, gwlpWndProc, darkWndProcCallback)
		originalWndProc = prev
	}
	// Queue one repaint after the subclass is installed. From then on,
	// WM_ACTIVATE/WM_SHOWWINDOW keep the non-client frame correct.
	postMessageW.Call(hwnd, wmAppDarkTitle, 0, 0)
}
type nativeDiagInfo struct {
	Version     string `json:"version"`
	AppData     string `json:"appData"`
	LogPath     string `json:"logPath"`
	RecentLog   string `json:"recentLog"`
	WindowLeft  int32  `json:"windowLeft"`
	WindowTop   int32  `json:"windowTop"`
	WindowRight int32  `json:"windowRight"`
	WindowBottom int32 `json:"windowBottom"`
	Fullscreen  bool   `json:"fullscreen"`
	NativeAwake bool   `json:"nativeAwake"`
}

func toggleNativeFullscreen(hwnd uintptr) bool {
	fullscreenMu.Lock()
	defer fullscreenMu.Unlock()

	styleIndex := int32(-16)

	if !fullscreen {
		style, _, _ := getWindowLongPtrW.Call(hwnd, uintptr(styleIndex))
		savedStyle = style

		savedPlace = windowPlacement{Length: uint32(unsafe.Sizeof(windowPlacement{}))}
		getWindowPlacement.Call(hwnd, uintptr(unsafe.Pointer(&savedPlace)))

		newStyle := style &^ uintptr(wsCaption|wsThickFrame|wsMinimizeBox|wsMaximizeBox|wsSysMenu)
		setWindowLongPtrW.Call(hwnd, uintptr(styleIndex), newStyle)

		mon, _, _ := monitorFromWindow.Call(hwnd, monitorDefaultToNearest)
		mi := monitorInfo{CbSize: uint32(unsafe.Sizeof(monitorInfo{}))}
		if mon == 0 {
			return false
		}
		ok, _, _ := getMonitorInfoW.Call(mon, uintptr(unsafe.Pointer(&mi)))
		if ok == 0 {
			return false
		}
		setWindowPos.Call(
			hwnd, 0,
			uintptr(mi.RcMonitor.Left), uintptr(mi.RcMonitor.Top),
			uintptr(mi.RcMonitor.Right-mi.RcMonitor.Left),
			uintptr(mi.RcMonitor.Bottom-mi.RcMonitor.Top),
			swpNoZOrder|swpNoOwnerZOrder|swpFrameChanged,
		)
		fullscreen = true
		log.Printf("fullscreen: on")
		return true
	}

	setWindowLongPtrW.Call(hwnd, uintptr(styleIndex), savedStyle)
	if savedPlace.Length != 0 {
		setWindowPlacement.Call(hwnd, uintptr(unsafe.Pointer(&savedPlace)))
	}
	setWindowPos.Call(
		hwnd, 0, 0, 0, 0, 0,
		swpNoMove|swpNoSize|swpNoZOrder|swpNoOwnerZOrder|swpFrameChanged,
	)
	fullscreen = false
	log.Printf("fullscreen: off")
	applyDarkTitleBar(hwnd)
	return false
}


func getNativeDiagnostics(hwnd uintptr) nativeDiagInfo {
	var r rect
	getWindowRect.Call(hwnd, uintptr(unsafe.Pointer(&r)))

	fullscreenMu.Lock()
	fs := fullscreen
	fullscreenMu.Unlock()

	return nativeDiagInfo{
		Version:      appVersion,
		AppData:      appDataPath(),
		LogPath:      logPath(),
		RecentLog:    tailLogLines(20),
		WindowLeft:   r.Left,
		WindowTop:    r.Top,
		WindowRight:  r.Right,
		WindowBottom: r.Bottom,
		Fullscreen:   fs,
		NativeAwake:  isNativeAwake(),
	}
}

func diagnosticsDialogFilter() []uint16 {
	return utf16Multi("Fichier texte (*.txt)\x00*.txt\x00Tous les fichiers (*.*)\x00*.*\x00")
}

func exportDiagnosticsFile(hwnd uintptr, payload string) bool {
	buf := make([]uint16, 1024)
	defaultName, _ := syscall.UTF16FromString("BridgeTimer-diagnostic.txt")
	copy(buf, defaultName)
	filter := diagnosticsDialogFilter()
	title, _ := syscall.UTF16FromString("Exporter le diagnostic Bridge Timer")
	defExt, _ := syscall.UTF16FromString("txt")

	ofn := openFileNameW{
		LStructSize:  uint32(unsafe.Sizeof(openFileNameW{})),
		HwndOwner:    hwnd,
		LpstrFilter:  &filter[0],
		NFilterIndex: 1,
		LpstrFile:    &buf[0],
		NMaxFile:     uint32(len(buf)),
		LpstrTitle:   &title[0],
		LpstrDefExt:  &defExt[0],
		Flags:        0x00000002 | 0x00000008 | 0x00000800 | 0x00080000,
	}
	ok, _, _ := getSaveFileNameW.Call(uintptr(unsafe.Pointer(&ofn)))
	if ok == 0 {
		return false
	}
	path := syscall.UTF16ToString(buf)
	if filepath.Ext(path) == "" {
		path += ".txt"
	}
	if err := os.WriteFile(path, []byte(payload), 0600); err != nil {
		log.Printf("export diagnostic: %v", err)
		return false
	}
	return true
}

func utf16Multi(s string) []uint16 {
	out := utf16.Encode([]rune(s))
	return append(out, 0)
}


func nativeStateFileName(key string) string {
	// Accept only BridgeTimer's own keys: never trust arbitrary paths from the web view.
	switch key {
	case "bridgeTimerV2.settings":
		return "native-settings.json"
	case "bridgeTimerWebView2.savedColors":
		return "native-colors.json"
	case "bridgeTimerV2.activeSession":
		return "native-session.json"
	default:
		return ""
	}
}

func nativeStateReadAll() map[string]string {
	stateFileMu.Lock()
	defer stateFileMu.Unlock()
	out := make(map[string]string)
	for _, key := range []string{"bridgeTimerV2.settings", "bridgeTimerWebView2.savedColors", "bridgeTimerV2.activeSession"} {
		b, err := os.ReadFile(filepath.Join(appDataPath(), nativeStateFileName(key)))
		if err == nil && len(b) <= 100000 && json.Valid(b) {
			out[key] = string(b)
		}
	}
	return out
}

func nativeStateWrite(key, value string) bool {
	name := nativeStateFileName(key)
	if name == "" || len(value) > 100000 || !json.Valid([]byte(value)) {
		return false
	}
	stateFileMu.Lock()
	defer stateFileMu.Unlock()
	path := filepath.Join(appDataPath(), name)
	if err := os.WriteFile(path, []byte(value), 0600); err != nil {
		log.Printf("native state write %s: %v", name, err)
		return false
	}
	return true
}

func nativeStateDelete(key string) bool {
	name := nativeStateFileName(key)
	if name == "" {
		return false
	}
	stateFileMu.Lock()
	defer stateFileMu.Unlock()
	err := os.Remove(filepath.Join(appDataPath(), name))
	return err == nil || os.IsNotExist(err)
}

func startLocalServer() (*http.Server, string, error) {
	addr := fmt.Sprintf("%s:%d", host, port)
	ln, err := net.Listen("tcp", addr)
	if errors.Is(err, syscall.EADDRINUSE) {
		// A different local program already owns our stable port.
		// Keep BridgeTimer usable; native state files preserve preferences
		// despite the temporary WebView2 origin change.
		log.Printf("port %d occupied; using a free localhost port", port)
		ln, err = net.Listen("tcp", net.JoinHostPort(host, "0"))
	}
	if err != nil {
		return nil, "", err
	}
	mux := http.NewServeMux()
	mux.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "text/html; charset=utf-8")
		w.Header().Set("Cache-Control", "no-store")
		w.Header().Set("X-Content-Type-Options", "nosniff")
		_, _ = w.Write(timerHTML)
	})
	mux.HandleFunc("/health", func(w http.ResponseWriter, r *http.Request) {
		_, _ = w.Write([]byte("ok"))
	})
	srv := &http.Server{Handler: mux, ReadHeaderTimeout: 2 * time.Second}
	go func() {
		if err := srv.Serve(ln); err != nil && err != http.ErrServerClosed {
			log.Printf("local server: %v", err)
		}
	}()
	return srv, "http://" + ln.Addr().String() + "/", nil
}

func main() {
	runtime.LockOSThread()
	defer runtime.UnlockOSThread()

	enableNativeDPIAwareness()
	configureWebView2Rendering()

	if !acquireSingleInstance() {
		return
	}
	defer releaseSingleInstance()
	defer setNativeAwake(false)

	stopLogging := initLogging()
	defer stopLogging()
	log.Printf("WebView2 args: %s", os.Getenv("WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS"))

	srv, url, err := startLocalServer()
	if err != nil {
		log.Printf("Bridge Timer local server: %v", err)
		showStartupError("Bridge Timer ne peut pas démarrer son serveur local.\n\n" + err.Error())
		return
	}
	defer srv.Shutdown(context.Background())

	dataPath := filepath.Join(appDataPath(), "WebView2Data")
	_ = os.MkdirAll(dataPath, 0700)

	startX, startY, startWidth, startHeight, hasSavedPosition := startupWindowGeometry()
	w := webview.NewWithOptions(webview.WebViewOptions{
		Debug: false,
		DataPath: dataPath,
		AutoFocus: true,
		WindowOptions: webview.WindowOptions{
			Title: appTitle,
			Width: startWidth,
			Height: startHeight,
			Center: !hasSavedPosition,
			X: int(startX),
			Y: int(startY),
			UsePosition: hasSavedPosition,
		},
	})
	if w == nil {
		log.Printf("WebView2 initialization failed")
		showStartupError("Bridge Timer ne peut pas initialiser Microsoft Edge WebView2.\n\nVérifie que le runtime WebView2 est installé sur Windows.")
		return
	}
	// The settings and timer opening size is the SAME 16:9 client-area target.
	// The native WndProc keeps a matching 16:9 minimum for both views.
	// The native opening size is also the minimum resizable size.
	// The window may still be enlarged or maximized normally.
	w.SetSize(defaultWindowWidth, defaultWindowHeight, webview.HintMin)
	defer w.Destroy()

	hwnd := uintptr(w.Window())
	applyDarkTitleBar(hwnd)
	installDarkTitleHook(hwnd)
	// Consume close requests on the JS side, without calling WebView/COM from WndProc.
	if err := w.Bind("nativeConsumeCloseRequest", func() bool {
		if !closePromptPending.Swap(false) { return false }
		closeRequestAt.Store(0)
		return true
	}); err != nil {
		log.Printf("close request bind: %v", err)
	}
	// The approved path bypasses the confirmation intercept exactly once.
	if err := w.Bind("nativeExit", func() bool {
		closeApproved.Store(true)
		posted, _, _ := postMessageW.Call(hwnd, wmClose, 0, 0)
		if posted == 0 {
			closeApproved.Store(false)
		}
		return posted != 0
	}); err != nil {
		log.Printf("exit bind: %v", err)
	}
	if err := w.Bind("nativeSetView", func(mode string, serial int64) bool {
		return setNativeView(hwnd,mode,serial)
	}); err != nil {
		log.Printf("native view bind: %v", err)
	}
	if err := w.Bind("nativeFullscreen", func() bool {
		return toggleNativeFullscreen(hwnd)
	}); err != nil {
		log.Printf("fullscreen bind: %v", err)
	}
	if err := w.Bind("nativeSetAwake", func(on bool) bool {
		return setNativeAwake(on)
	}); err != nil {
		log.Printf("awake bind: %v", err)
	}
	if err := w.Bind("nativeStateReadAll", nativeStateReadAll); err != nil {
		log.Printf("native state read bind: %v", err)
	}
	if err := w.Bind("nativeStateWrite", nativeStateWrite); err != nil {
		log.Printf("native state write bind: %v", err)
	}
	if err := w.Bind("nativeStateDelete", nativeStateDelete); err != nil {
		log.Printf("native state delete bind: %v", err)
	}
	if err := w.Bind("nativeDiagnostics", func() nativeDiagInfo {
		return getNativeDiagnostics(hwnd)
	}); err != nil {
		log.Printf("diagnostics bind: %v", err)
	}
	if err := w.Bind("nativeExportDiagnostics", func(payload string) bool {
		return exportDiagnosticsFile(hwnd, payload)
	}); err != nil {
		log.Printf("diagnostic export bind: %v", err)
	}

	w.Navigate(url)
	w.Run()
}
