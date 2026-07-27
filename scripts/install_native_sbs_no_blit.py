"""Try visible SBS without CustomShaderUpscale blit (blit AVs on this AMD box).

Path A config: upscaling=0, force_stereo=2, direct_mode=sbs, no Present packer.
"""
from pathlib import Path
import hashlib
import re
import shutil
import sys

proj = Path(sys.argv[1])
live = Path(sys.argv[2])
mode = sys.argv[3] if len(sys.argv) > 3 else "native"
snap = proj / "SNAPSHOT_v060_before_helix_20260724_134355"

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

ini = (live / "d3dx.ini").read_text(encoding="utf-8")
dm = (live / "d3dxdm.ini").read_text(encoding="utf-8")

if mode == "native":
    ini = re.sub(r"(?m)^upscaling\s*=\s*.*$", "upscaling = 0", ini)
    # no Present packer
    up = (live / "ShaderFixes" / "upscale.ini").read_text(encoding="utf-8")
    up = re.sub(r"(?m)^run\s*=\s*CustomShaderUpscale\s*$", ";run = CustomShaderUpscale", up)
    (live / "ShaderFixes" / "upscale.ini").write_text(up, encoding="utf-8")
elif mode == "switch":
    # upscaling on, Present only flips bb reference — no draw/f_bb sample
    ini = re.sub(r"(?m)^upscaling\s*=\s*.*$", "upscaling = 1", ini)
    ini = re.sub(r"(?m)^upscale_mode\s*=\s*.*$", "upscale_mode = 1", ini)
    (live / "ShaderFixes" / "upscale.ini").write_text(
        "[Constants]\n"
        "global $ups_ready = 0\n"
        "\n"
        "[KeyEnableUpscale]\n"
        "Key = NO_MODIFIERS VK_F8\n"
        "type = cycle\n"
        "$ups_ready = 0, 1\n"
        "\n"
        "[Present]\n"
        "if $ups_ready == 1\n"
        "\tspecial = upscaling_switch_bb\n"
        "endif\n",
        encoding="utf-8",
    )
elif mode == "fixd3d_key":
    fix = proj / "downloads/extracted_geo11_fix/FixFiles"
    shutil.copy2(fix / "d3d11.dll", live / "d3d11.dll")
    shutil.copy2(fix / "nvapi64.dll", live / "nvapi64.dll")
    ini = re.sub(r"(?m)^upscaling\s*=\s*.*$", "upscaling = 1", ini)
    (live / "ShaderFixes" / "upscale.ini").write_text(
        "[Constants]\n"
        "global $ups_ready = 0\n"
        "\n"
        "[KeyEnableUpscale]\n"
        "Key = NO_MODIFIERS VK_F8\n"
        "type = cycle\n"
        "$ups_ready = 0, 1\n"
        "\n"
        "[Present]\n"
        "if $ups_ready == 1\n"
        "\trun = CustomShaderUpscale\n"
        "endif\n"
        "\n"
        "[Resource3DVisionUpscaleBackupTexture]\n"
        "[CustomShaderUpscale]\n"
        "vs = upscale.hlsl\n"
        "ps = upscale.hlsl\n"
        "hs = null\n"
        "ds = null\n"
        "gs = null\n"
        "blend = disable\n"
        "cull = none\n"
        "sampler = anisotropic_filter\n"
        "topology = triangle_strip\n"
        "o0 = set_viewport r_bb\n"
        "Resource3DVisionUpscaleBackupTexture = reference ps-t101\n"
        "ps-t101 = f_bb\n"
        "draw = 4, 0\n"
        "post ps-t101 = reference Resource3DVisionUpscaleBackupTexture\n"
        "special = upscaling_switch_bb\n",
        encoding="utf-8",
    )
else:
    raise SystemExit("mode native|switch|fixd3d_key")

(live / "d3dx.ini").write_text(ini, encoding="utf-8")
(live / "d3dxdm.ini").write_text(dm, encoding="utf-8")
print("OK mode=", mode)
print("upscaling", re.search(r"(?m)^upscaling\s*=\s*.*$", ini).group(0))
print("d3d", hashlib.sha256((live / "d3d11.dll").read_bytes()).hexdigest()[:16])
