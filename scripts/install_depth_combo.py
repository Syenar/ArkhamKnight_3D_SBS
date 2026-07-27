"""Install surviving depth/light combo: dm_patching + UE3 slices, no Present upscale."""
from pathlib import Path
import hashlib
import re
import shutil
import sys

proj = Path(sys.argv[1])
live = Path(sys.argv[2])
snap = proj / "SNAPSHOT_v060_before_helix_20260724_134355"
ue3_src = proj / "downloads/extracted_geo11_fix/FixFiles/ShaderFixes/UE3_BatmanAK.ini"

expect_dxgi = "5B8719852BBA918166CA3C8F25BDB3A41E65DA1090720B3931B66B0AB3220BB6"
expect_d3d = "C89AEE44CCFA0240E1BFEA37F5F7357514AA6FBCB2E92AD34A974AC192BC0E4E"

keep = [
    "ShaderRegex_SpecularPS1",
    "ShaderRegex_SpecularPS2",
    "ShaderRegex_SpecularPS3",
    "ShaderRegex_ParallaxPS1",
    "ShaderRegex_ParallaxPS2",
    "ShaderRegex_Regex2",
    "ShaderRegex_Decals1",
    "ShaderRegex_Decals2",
    "ShaderRegex_Decals3",
    "ShaderRegex_Tile_Lights1",
]


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest().upper()


for name in ("ShaderFixesDM", "ShaderCache", "ShaderCacheDM"):
    p = live / name
    if p.exists():
        shutil.rmtree(p, ignore_errors=True)

for name in ("d3d11.dll", "dxgi.dll", "nvapi64.dll", "d3dx.ini", "d3dxdm.ini"):
    shutil.copy2(snap / name, live / name)
if (live / "ShaderFixes").exists():
    shutil.rmtree(live / "ShaderFixes")
shutil.copytree(snap / "ShaderFixes", live / "ShaderFixes")
for p in (live / "ShaderFixes").glob("upscale*.bin"):
    p.unlink(missing_ok=True)

assert sha(live / "dxgi.dll") == expect_dxgi
assert sha(live / "d3d11.dll") == expect_d3d

# Present upscale OFF — required while CustomShaderUpscale AVs
up = (live / "ShaderFixes" / "upscale.ini").read_text(encoding="utf-8", errors="replace")
up = re.sub(r"(?m)^run\s*=\s*CustomShaderUpscale\s*$", ";run = CustomShaderUpscale", up)
(live / "ShaderFixes" / "upscale.ini").write_text(up, encoding="utf-8")

# dm_patching_mode=1 survived and used most RAM (likely doing work)
dm = (live / "d3dxdm.ini").read_text(encoding="utf-8", errors="replace")
dm = re.sub(r"(?m)^dm_patching_mode\s*=\s*.*$", "dm_patching_mode = 1", dm)
(live / "d3dxdm.ini").write_text(dm, encoding="utf-8")

# UE3 combo ini
text = ue3_src.read_text(encoding="utf-8", errors="replace")
parts = re.split(r"(?=^\[ShaderRegex_)", text, flags=re.M)
out = ["; Depth/light combo from surviving probes (no Helix hash ShaderFixes)\n"]
keep_set = set(keep)
for part in parts[1:]:
    m = re.match(r"\[(ShaderRegex_[^\].]+)", part)
    if not m:
        continue
    root = m.group(1).split(".")[0]
    if root in keep_set:
        out.append(part if part.endswith("\n") else part + "\n")
body = "".join(out)
for k in keep:
    assert f"[{k}]" in body, k
combo = live / "ShaderFixes" / "UE3_BatmanAK_combo.ini"
combo.write_text(body, encoding="utf-8")

ini = (live / "d3dx.ini").read_text(encoding="utf-8", errors="replace")
ini = re.sub(r"(?m)^;?\s*include\s*=\s*ShaderFixes\\UE3_.*\r?\n", "", ini)
inc = "include = ShaderFixes\\UE3_BatmanAK_combo.ini"
if inc not in ini:
    m = re.search(r"(?m)^\[Include\]\s*\r?\n", ini)
    ini = ini[: m.end()] + inc + "\n" + ini[m.end() :]
(live / "d3dx.ini").write_text(ini, encoding="utf-8")

print("OK combo")
print("dm_patching_mode=1")
print("Present CustomShaderUpscale=OFF")
print("UE3 sections", keep)
print("replace count", len(list((live / "ShaderFixes").glob("*replace*"))))
print("note: packer Present still disabled (AV); direct_mode=sbs + upscaling=1 kept")
