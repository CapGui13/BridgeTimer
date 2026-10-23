from pathlib import Path
import hashlib

source = Path("timer.html").read_bytes()
exe = Path("dist/BridgeTimer.exe").read_bytes()
assert exe[:2] == b"MZ", "Output is not a Windows executable"
assert exe.count(source) == 1, "Windows EXE does not contain the exact published timer.html"
print("Verified byte-exact production UI in EXE", hashlib.sha256(source).hexdigest())
