"""Delayed SBS packer: stock blit path minus UnbindAll (UnbindAll AVs when armed)."""
from pathlib import Path
import hashlib
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

text = """[Constants]
global $ups_ready = 0

[KeyEnableUpscale]
; Force SBS packer on/off
Key = ctrl shift U
type = cycle
$ups_ready = 0, 1

[Present]
if $ups_ready == 0 && time > 60
\t$ups_ready = 1
endif
if $ups_ready == 1
\trun = CustomShaderUpscale
endif

[Resource3DVisionUpscaleBackupTexture]
[CustomShaderUpscale]
vs = upscale.hlsl
ps = upscale.hlsl
hs = null
ds = null
gs = null
blend = disable
cull = none
sampler = anisotropic_filter
topology = triangle_strip
; NOTE: BuiltInCommandListUnbindAllRenderTargets omitted — AVs on this AMD box
o0 = set_viewport r_bb
Resource3DVisionUpscaleBackupTexture = reference ps-t101
ps-t101 = f_bb
draw = 4, 0
post ps-t101 = reference Resource3DVisionUpscaleBackupTexture
special = upscaling_switch_bb
"""
(live / "ShaderFixes" / "upscale.ini").write_text(text, encoding="utf-8")
shutil.copy2(live / "ShaderFixes" / "upscale.ini", wc / "upscale.ini")

dm = (live / "d3dxdm.ini").read_text(encoding="utf-8")
if "ups_ready" not in dm:
    dm = dm.replace(
        "global $popout_bias_step_down = 0.001",
        "global $popout_bias_step_down = 0.001\nglobal $ups_ready = 0",
    )
    (live / "d3dxdm.ini").write_text(dm, encoding="utf-8")

assert "$ups_ready" in text
assert "UnbindAll" not in text
assert "special = upscaling_switch_bb" in text
assert "Resource3DVisionUpscaleBackupTexture" in text
print("OK delayed safe packer (backup+special, no UnbindAll)")
