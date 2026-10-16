"""Generate a separate Windows comparison binary without changing the usual edition.

The regular BridgeTimer.exe keeps its original mutex, WebView2 profile and port.
The comparison edition is independent so both processes can run concurrently.
"""
from pathlib import Path
import shutil

root = Path(__file__).resolve().parents[1]
source = (root / "main.go").read_text(encoding="utf-8")

replacements = [
    ('appTitle = "Bridge Timer"', 'appTitle = "Bridge Timer - Comparaison"'),
    ('port = 43831', 'port = 43832'),
    ('p := filepath.Join(base, "BridgeTimerWebView2")',
     'p := filepath.Join(base, "BridgeTimerWebView2Comparaison")'),
    (r'Local\\BridgeTimerWebView2', r'Local\\BridgeTimerWebView2Comparaison'),
]

for old, new in replacements:
    count = source.count(old)
    if count != 1:
        raise SystemExit(f"Expected exactly one occurrence ({count}): {old!r}")
    source = source.replace(old, new, 1)

output = root / "comparison_build"
output.mkdir(parents=True, exist_ok=True)
(output / "main.go").write_text(source, encoding="utf-8")
for filename in ("timer.html", "resource_windows_amd64.syso"):
    shutil.copy2(root / filename, output / filename)

# Prevent accidentally shipping an edition that still grabs the normal app's
# single-instance mutex or consumes its listening port.
assert 'port = 43831' not in source
assert r'Local\\BridgeTimerWebView2"' not in source
assert 'BridgeTimerWebView2Comparaison' in source
assert 'appTitle = "Bridge Timer - Comparaison"' in source
print("Separate comparison edition prepared with unique window title, port, mutex and data directory")
