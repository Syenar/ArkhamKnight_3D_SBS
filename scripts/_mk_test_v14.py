from pathlib import Path
import hashlib

p = Path(__file__).resolve().parent.parent
t = (p / "scripts" / "test_v13_sbs.py").read_text(encoding="utf-8")
dll = p / "experimental_fork_20260724_nullguards" / "patched_dlls" / "d3d11.dll.patched_v14"
h = hashlib.sha256(dll.read_bytes()).hexdigest().upper()
repls = [
    ("patched_v13", "patched_v14"),
    ("TEST_V13", "TEST_V14"),
    ("LEFT_RUNNING_V13", "LEFT_RUNNING_V14"),
    ("V13_SBS", "V14_SBS"),
    ("STACK_V13", "STACK_V14"),
    ("v0.7.0-v13", "v0.7.0-v14"),
    ("=== v13", "=== v14"),
    (
        'assert sha(LIVE / "d3d11.dll").startswith("7D56ED23")',
        f'assert sha(LIVE / "d3d11.dll") == "{h}"',
    ),
]
for a, b in repls:
    if a not in t:
        raise SystemExit(f"missing pattern: {a!r}")
    t = t.replace(a, b)
out = p / "scripts" / "test_v14_sbs.py"
out.write_text(t, encoding="utf-8")
print("OK", h, "->", out)
