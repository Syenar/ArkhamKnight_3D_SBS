"""Hard restore v0.6.0: wipe Helix ShaderFixes, stock inis, no Present sep hacks."""
from pathlib import Path
import hashlib
import shutil
import sys

proj = Path(sys.argv[1])
live = Path(sys.argv[2])
wc = proj / "working_config"
stock = proj / "downloads" / "extracted_geo11_v0.7.10" / "x64"

expect_dxgi = "5B8719852BBA918166CA3C8F25BDB3A41E65DA1090720B3931B66B0AB3220BB6"
expect_d3d11 = "C89AEE44CCFA0240E1BFEA37F5F7357514AA6FBCB2E92AD34A974AC192BC0E4E"


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    h.update(p.read_bytes())
    return h.hexdigest().upper()


def wipe_dir(p: Path) -> None:
    if p.exists():
        shutil.rmtree(p)


# Wipe polluted shader folders
for name in ("ShaderFixes", "ShaderFixesDM", "ShaderCache", "ShaderCacheDM"):
    wipe_dir(live / name)

# Stock ShaderFixes only (8 files, no Helix replaces)
shutil.copytree(stock / "ShaderFixes", live / "ShaderFixes")

# Stock binaries
for name in ("d3d11.dll", "nvapi64.dll"):
    shutil.copy2(stock / name, live / name)

# Locked loader dxgi + milestone inis (NO hotkey Present hacks)
for name in ("dxgi.dll", "d3dx.ini", "d3dxdm.ini"):
    shutil.copy2(wc / name, live / name)

# Clear persisted stereo that may fight dm_* defaults
(live / "d3dx_user.ini").write_text(
    "; AUTOMATICALLY GENERATED FILE - DO NOT EDIT\n"
    ";\n"
    "; Clean v0.6.0 defaults (Helix + sep-hack session wiped)\n"
    ";\n"
    "[Constants]\n"
    "pre persist separation = 50\n"
    "pre persist convergence = 2.0\n"
    "pre persist target_display = -1\n"
    "pre persist dm_popout_bias = 0.02\n",
    encoding="utf-8",
)

dxgi = sha256(live / "dxgi.dll")
d3d = sha256(live / "d3d11.dll")
sf = list((live / "ShaderFixes").glob("*"))
replace = list((live / "ShaderFixes").glob("*replace*"))
dm_text = (live / "d3dxdm.ini").read_text(encoding="utf-8", errors="replace")

assert dxgi == expect_dxgi, dxgi
assert d3d == expect_d3d11, d3d
assert len(replace) == 0, f"replace leftovers: {len(replace)}"
assert "dm_separation = separation" not in dm_text
assert "sep_synced" not in dm_text

print(f"dxgi={dxgi}")
print(f"d3d11={d3d}")
print(f"ShaderFixes={len(sf)} replace={len(replace)}")
print("PASS hard restore v0.6.0 clean")
