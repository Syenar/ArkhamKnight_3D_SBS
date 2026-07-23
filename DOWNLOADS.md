# Downloaded stereo packages (2026-07-23)

All files live under this project folder. **Do not copy into the game until Steam finish installs** `BatmanAK.exe` under `D:\SteamLibrary\steamapps\common\Batman Arkham Knight\Binaries\Win64`.

## Archives (`downloads\`)

| File | Source | Purpose |
|---|---|---|
| `Batman_Arkham_Knight_geo11_fix.7z` | HelixMod / masterotaku S3 | Preferred game-specific geo-11 fix (includes geo-11 ~v0.6.182) |
| `Batman_Arkham_Knight_3D_Vision_fix.7z` | HelixMod / masterotaku S3 | Older 3D Vision-only fix (keep as backup; not for first install) |
| `geo-11_v0.7.10.7z` | bo3b S3 | Latest standalone geo-11 (loader + x64 DLLs) |
| `dxgi.dll` | 3Dmigoto 1.3.16 GitHub release | Fallback if stereo never engages |

## Ready to install (`ready_to_install\`)

### `Win64\` — copy this entire folder into the game’s `Binaries\Win64`

Already configured:
- `d3dxdm.ini` → `direct_mode = sbs`
- `d3dx.ini` → `force_stereo=2`

Top-level injectors: `d3d11.dll`, `nvapi64.dll`, `d3dx.ini`, `d3dxdm.ini`, `d3dcompiler_47.dll`, `uninstall.bat`, plus `ShaderFixes` / caches.

### `companions\` — only if needed after first test

| File | When to use |
|---|---|
| `dxgi_3dmigoto_1.3.16.dll` | Rename to `dxgi.dll` in Win64 if SBS never appears |
| `3DMigoto Loader.exe` + `dxgi_geo11_loader.dll` | Alternate inject path if DLL load fails (some newer drivers) |

## Extracted references

- `downloads\extracted_geo11_fix\` — unpacked HelixMod package
- `downloads\extracted_geo11_v0.7.10\` — standalone geo-11 (includes `loader\x64\3DMigoto Loader.exe`)
- `downloads\extracted_3dvision_fix\` — unpacked legacy 3D Vision package

## Install command (after game is ready)

```powershell
$src = "C:\Users\samsa\Desktop\Workplace\Projects\Arkham 3D Projects\Arkham Knight 3D\ready_to_install\Win64\*"
$dst = "D:\SteamLibrary\steamapps\common\Batman Arkham Knight\Binaries\Win64"
Copy-Item $src $dst -Recurse -Force
```
