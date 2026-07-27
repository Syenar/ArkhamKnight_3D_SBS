"""Stock CustomShaderUpscale with delayed enable via $ups_ready (no PS $-eating)."""
from pathlib import Path
import hashlib
import re
import shutil
import sys

proj = Path(sys.argv[1])
live = Path(sys.argv[2])
snap = proj / "SNAPSHOT_v060_before_helix_20260724_134355"
wc = proj / "working_config"

for name in ("ShaderFixesDM", "ShaderCache", "ShaderCacheDM"):
    p = live / name
    if p.exists():
        shutil.rmtree(p, ignore_errors=True)

for name in ("d3d11.dll", "dxgi.dll", "nvapi64.dll", "d3dx.ini", "d3dxdm.ini"):
    shutil.copy2(snap / name, live / name)

if (live / "ShaderFixes").exists():
    shutil.rmtree(live / "ShaderFixes")
shutil.copytree(snap / "ShaderFixes", live / "ShaderFixes")
for p in (live / "ShaderFixes").glob("*.bin"):
    p.unlink(missing_ok=True)

assert hashlib.sha256((live / "dxgi.dll").read_bytes()).hexdigest().upper().startswith("5B871985")

stock = (snap / "ShaderFixes" / "upscale.ini").read_text(encoding="utf-8")
stock = re.sub(r"(?m)^;run\s*=\s*CustomShaderUpscale\s*$", "run = CustomShaderUpscale", stock)

present = """[Constants]
global $ups_ready = 0

[KeyEnableUpscale]
; Manual SBS packer enable if auto delay fails
Key = ctrl shift U
type = cycle
$ups_ready = 0, 1

[Present]
; Delay packer until after load — immediate Present AV'd during boot
if $ups_ready == 0 && time > 90
\t$ups_ready = 1
endif
if $ups_ready == 1
\trun = CustomShaderUpscale
endif

"""
body = re.sub(
    r"(?ms)^\[Present\].*?(?=^\[CustomShaderUpscale\])",
    present,
    stock,
    count=1,
)
(live / "ShaderFixes" / "upscale.ini").write_text(body, encoding="utf-8")
shutil.copy2(live / "ShaderFixes" / "upscale.ini", wc / "upscale.ini")

# Also declare in d3dxdm for persistence across includes
dm = (live / "d3dxdm.ini").read_text(encoding="utf-8")
if "ups_ready" not in dm:
    dm = dm.replace(
        "global $popout_bias_step_down = 0.001",
        "global $popout_bias_step_down = 0.001\nglobal $ups_ready = 0",
    )
    (live / "d3dxdm.ini").write_text(dm, encoding="utf-8")

text = (live / "ShaderFixes" / "upscale.ini").read_text(encoding="utf-8")
assert "$ups_ready" in text
assert "if $ups_ready == 1" in text
assert "run = CustomShaderUpscale" in text
assert "UnbindAll" in text
assert not text.startswith("\ufeff")
print("OK delayed stock packer")
print(text[:450])
