//go:build windows

package main

import (
 "runtime"
 "testing"
)

// Verify actual Windows SetThreadExecutionState calls on one locked thread.
// This test does not prove that any display hardware makes an audible sound.
func TestNativeAwakeRequestAndRelease(t *testing.T) {
 runtime.LockOSThread()
 defer runtime.UnlockOSThread()
 defer setNativeAwake(false)
 if !setNativeAwake(true) {
  t.Fatal("Windows refused ES_CONTINUOUS|ES_SYSTEM_REQUIRED|ES_DISPLAY_REQUIRED")
 }
 if !isNativeAwake() { t.Fatal("native wake state not set") }
 if !setNativeAwake(false) { t.Fatal("Windows refused releasing the anti-sleep request") }
 if isNativeAwake() {t.Fatal("native wake state was not released")}
}
