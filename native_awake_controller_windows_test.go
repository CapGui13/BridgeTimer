//go:build windows

package main

import (
 "sync"
 "testing"
)

func TestAwakeControllerPersistsAcrossCallsAndReleases(t *testing.T) {
 c:=newAwakeController()
 defer c.close()
 if !c.set(true,1) || !isNativeAwake() {t.Fatal("dedicated thread failed to set anti-sleep")}
 if !c.set(true,2) || !isNativeAwake() {t.Fatal("paused tournament must remain protected")}
 // A stale asynchronous callback must not change a newer request.
 if !c.set(false,1) || !isNativeAwake() {t.Fatal("stale release wrongly disabled anti-sleep")}
 if !c.set(false,3) || isNativeAwake() {t.Fatal("stop must release anti-sleep")}
 if !c.set(true,4) || !isNativeAwake() {t.Fatal("restart failed")}
 c.close()
 if isNativeAwake() {t.Fatal("shutdown must release on the SAME OS thread")}
 if c.set(true,5) {t.Fatal("closed controller must reject new requests")}
}

func TestAwakeControllerConcurrentOutOfOrder(t *testing.T) {
 c:=newAwakeController()
 defer c.close()
 var wg sync.WaitGroup
 wg.Add(2)
 go func(){defer wg.Done();c.set(true,10)}()
 go func(){defer wg.Done();c.set(false,20)}()
 wg.Wait()
 // Whether an obsolete request is delivered early or late, the highest
 // sequence MUST win and the controller's actual native state is off.
 if isNativeAwake() {t.Fatal("late stale request must not reactivate anti-sleep")}
}
