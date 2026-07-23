# Batman: Arkham Knight — Stereo 3D (SBS)

Project docs, launch helpers, and install notes for running **Batman: Arkham Knight** in true geometric stereoscopic 3D (side-by-side first) on a 3D projector via **HelixMod + geo-11**.

> This repository does **not** redistribute HelixMod / geo-11 binaries (third-party license forbids re-upload). Download them from the official sources linked below.

## Status (2026-07-23)

- Steam install: Arkham Knight DX11 (`Binaries\Win64\BatmanAK.exe`)
- **Working SBS stack on AMD RX 7900 XTX** (agent-verified): HelixMod ShaderFixes + **geo-11 v0.7.10** `d3d11.dll`/`nvapi64.dll`/`d3dxdm.ini` + 3Dmigoto `dxgi.dll`
- HelixMod’s bundled older geo-11 DLL **crashes** with `Rendering thread exception: Fatal error!` when `force_stereo=2` — replace injectors with v0.7.10
- Launch via **Steam** (`steam://rungameid/208650` / `Launch_ArkhamKnight_3D.bat`)
- Output: `direct_mode = sbs`, `force_stereo=2`, `show_fps_monitor = false`, `dm_auto_convergence = 0`

## Quick start

1. Own and install [Batman: Arkham Knight](https://store.steampowered.com/app/208650/) on Steam.
2. Download the **geo-11** Arkham Knight fix from HelixMod:  
   [Batman Arkham Knight (DX11)](https://helixmod.blogspot.com/2020/12/batman-arkham-knight-dx11.html)  
   Archive: `https://masterotaku.s3.amazonaws.com/Batman+Arkham+Knight/Batman_Arkham_Knight_geo11_fix.7z`
3. Extract into  
   `...\steamapps\common\Batman Arkham Knight\Binaries\Win64`  
   (same folder as `BatmanAK.exe`).
4. Download [geo-11 v0.7.10](https://helixmod.blogspot.com/2022/06/announcing-new-geo-11-3d-driver.html) and replace from the package’s `x64` folder:
   - `d3d11.dll`
   - `nvapi64.dll`
   - `d3dxdm.ini` (required — keep HelixMod `ShaderFixes` + `d3dx.ini`)
   Do **not** keep the older geo-11 DLL from the HelixMod archive; it fatals on this GPU.
5. Download [`dxgi.dll` from 3Dmigoto 1.3.16](https://github.com/bo3b/3Dmigoto/releases/download/1.3.16/dxgi.dll) into that same `Win64` folder.
6. Copy `3DMigoto Loader.exe` from geo-11’s `loader\x64` into `Win64`.
7. In `d3dx.ini` set / uncomment:
   ```ini
   [Loader]
   target = BatmanAK.exe
   module = d3d11.dll
   launch = BatmanAK.exe

   force_stereo=2
   ```
8. In `d3dxdm.ini` (from geo-11 v0.7.10):
   ```ini
   direct_mode = sbs
   show_fps_monitor = false
   dm_auto_convergence = 0
   ```
9. Launch with [`Launch_ArkhamKnight_3D.bat`](Launch_ArkhamKnight_3D.bat) (Steam protocol), **not** the standalone loader alone.
10. Set the projector to **SBS** 3D input. Disable chromatic aberration and AA in-game for sharper stereo.

Optional PowerShell helper: [`scripts/Install-FromDownloads.ps1`](scripts/Install-FromDownloads.ps1) (expects archives already downloaded into `downloads\`).

## Docs in this repo

| File | Purpose |
|---|---|
| [`ARKHAM_KNIGHT_3D_PLAN.txt`](ARKHAM_KNIGHT_3D_PLAN.txt) | Phase plan (install → SBS → projector → stability → VR later) |
| [`NOTES.txt`](NOTES.txt) | Machine notes, crash fix, launch test results |
| [`DOWNLOADS.md`](DOWNLOADS.md) | Exact archive URLs and staging layout |
| [`baseline_Win64_filelist.txt`](baseline_Win64_filelist.txt) | Stock Win64 files before stereo |

## Revert

- Run the fix’s `uninstall.bat`, or  
- Steam → **Verify Integrity of Game Files**

## Credits / upstream

- HelixMod geo-11 Arkham Knight fix (masterotaku et al.): https://helixmod.blogspot.com/2020/12/batman-arkham-knight-dx11.html
- geo-11 driver (davegl1234 / HelixMod): https://helixmod.blogspot.com/2022/06/announcing-new-geo-11-3d-driver.html
- 3Dmigoto: https://github.com/bo3b/3Dmigoto

## License

Project notes and scripts in this repo: use freely for personal non-commercial stereo setups.

**Do not** commit or re-host HelixMod / geo-11 binaries here — see their Personal Use Software License.
