"""Ensure unlock_separation / unlock_convergence are enabled in d3dx.ini."""
from pathlib import Path
import re
import sys

p = Path(sys.argv[1])
t = p.read_text(encoding="utf-8", errors="replace")
t = re.sub(r"(?m)^;?unlock_separation\s*=\s*.*$", "unlock_separation=1", t)
t = re.sub(r"(?m)^;?unlock_convergence\s*=\s*.*$", "unlock_convergence=1", t)
if "unlock_separation=1" not in t:
    t = re.sub(
        r"(?m)^(force_stereo\s*=\s*2\s*)$",
        r"\1\nunlock_separation=1\nunlock_convergence=1",
        t,
    )
p.write_text(t, encoding="utf-8")
print("unlock_separation=1" in t, "unlock_convergence=1" in t)
