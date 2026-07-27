"""Install Specular/Parallax UE3 regex only — no Helix hash ShaderFixes."""
from pathlib import Path
import re
import shutil
import sys

proj = Path(sys.argv[1])
live = Path(sys.argv[2])
src_ue3 = proj / "downloads/extracted_geo11_fix/FixFiles/ShaderFixes/UE3_BatmanAK.ini"
dst_sf = live / "ShaderFixes"
dst_ue3 = dst_sf / "UE3_BatmanAK_specular.ini"
d3dx = live / "d3dx.ini"

keep = {
    "ShaderRegex_SpecularPS1",
    "ShaderRegex_SpecularPS2",
    "ShaderRegex_SpecularPS3",
    "ShaderRegex_ParallaxPS1",
    "ShaderRegex_ParallaxPS2",
}

text = src_ue3.read_text(encoding="utf-8", errors="replace")
# Split into top-level sections (header comment blocks stay with following section)
parts = re.split(r"(?=^\[ShaderRegex_)", text, flags=re.M)
header = parts[0]
out = ["; Sanitized UE3 Batman AK — Specular + Parallax only (no hash ShaderFixes)\n", header]
for part in parts[1:]:
    m = re.match(r"\[(ShaderRegex_[^\].]+)", part)
    if not m:
        continue
    base = m.group(1)
    # Pattern/Replace/InsertDeclarations share prefix before first '.'
    root = base.split(".")[0]
    if root in keep:
        out.append(part if part.endswith("\n") else part + "\n")

dst_sf.mkdir(parents=True, exist_ok=True)
# Ensure stock upscale present; do not copy Helix hash txt/bin
stock_sf = proj / "downloads/extracted_geo11_v0.7.10/x64/ShaderFixes"
for name in ("upscale.ini", "upscale.hlsl"):
    shutil.copy2(stock_sf / name, dst_sf / name)

dst_ue3.write_text("".join(out), encoding="utf-8")

ini = d3dx.read_text(encoding="utf-8", errors="replace")
inc = "include = ShaderFixes\\UE3_BatmanAK_specular.ini"
# remove prior UE3 includes
ini = re.sub(
    r"(?m)^;?\s*include\s*=\s*ShaderFixes\\UE3_BatmanAK.*\r?\n",
    "",
    ini,
)
if inc not in ini:
    m = re.search(r"(?m)^\[Include\]\s*\r?\n", ini)
    if m:
        ini = ini[: m.end()] + inc + "\n" + ini[m.end() :]
    else:
        ini = "[Include]\n" + inc + "\n\n" + ini
d3dx.write_text(ini, encoding="utf-8")

body = dst_ue3.read_text(encoding="utf-8")
for k in keep:
    assert f"[{k}]" in body, k
assert "ShaderRegex_Decals" not in body
assert "ShaderRegex_Halo" not in body
assert "ShaderRegex_Tile_Lights" not in body
assert inc in d3dx.read_text(encoding="utf-8")
replace = list(dst_sf.glob("*replace*"))
assert len(replace) == 0, f"replace pollution: {len(replace)}"
print("OK", dst_ue3)
print("sections", sorted(keep))
print("ShaderFixes", len(list(dst_sf.glob("*"))), "replace", len(replace))
