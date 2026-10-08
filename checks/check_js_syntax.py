from pathlib import Path
import re
import subprocess
import tempfile

root = Path(__file__).resolve().parents[1]
html = (root / "timer.html").read_text(encoding="utf-8")

scripts = re.findall(r"<script>(.*?)</script>", html, flags=re.S | re.I)
if not scripts:
    raise SystemExit("No inline JavaScript found in timer.html")

js = "\n".join(scripts)
with tempfile.NamedTemporaryFile("w", suffix=".js", encoding="utf-8", delete=False) as f:
    f.write(js)
    path = f.name

try:
    subprocess.run(["node", "--check", path], check=True)
finally:
    Path(path).unlink(missing_ok=True)

print("JavaScript syntax OK")
