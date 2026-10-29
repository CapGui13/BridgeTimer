//go:build windows

package main

import (
 "encoding/json"
 "os"
 "path/filepath"
 "testing"
)

func TestActiveSessionJournalAtomicOverwrite(t *testing.T) {
 t.Setenv("LOCALAPPDATA",t.TempDir())
 const key="bridgeTimerV2.activeSession"
 first := `{"schema":1,"state":{"pos":1}}`
 second := `{"schema":1,"state":{"pos":4}}`
 if !nativeStateWrite(key,first) {t.Fatal("initial checkpoint failed")}
 if !nativeStateWrite(key,second) {t.Fatal("atomic replacement failed")}
 p:=filepath.Join(appDataPath(),"native-session.json")
 data,err:=os.ReadFile(p)
 if err!=nil||string(data)!=second||!json.Valid(data) {t.Fatalf("last checkpoint: %q, err=%v",data,err)}
 loaded:=nativeStateReadAll()
 if loaded[key]!=second {t.Fatalf("native recovery read: %q",loaded[key])}
 if nativeStateWrite(key,"{damaged") {t.Fatal("must reject invalid checkpoint JSON")}
 data,err=os.ReadFile(p)
 if err!=nil||string(data)!=second {t.Fatal("invalid update should preserve last valid checkpoint")}
 if !nativeStateDelete(key) {t.Fatal("checkpoint deletion failed")}
 if _,err=os.Stat(p);!os.IsNotExist(err) {t.Fatalf("checkpoint still present: %v",err)}
}
