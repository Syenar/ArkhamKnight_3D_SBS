# Fresh start — 2026-07-24

## What we proved
- **Vanilla game (no geo-11):** Windows HDR stays **OFF** the whole time.
- So HDR was coming from the **injector / upscale swap-chain stack**, not from the game or a Windows “HDR mode” for Arkham.

## What was wiped
- Everything stereo-related moved out of `Binaries\Win64` into `FULL_RESET_*`.
- No `dxgi.dll`, no Loader, no Helix `ShaderFixes` hashes, no old Desktop bat logic.

## What was reinstalled (minimal)
From stock geo-11 v0.7.10 + `working_config` inis only:
- `d3d11.dll`, `nvapi64.dll`
- pristine `ShaderFixes` (stock: upscale / mouse / 3dvision2sbs / help)
- `d3dx.ini`: `force_stereo=2`, `force_no_nvapi=1`, `upscaling=1`, `1920x1080`, `upscale_mode=1`, `include=upscale.ini`, `get_resolution_from=swap_chain`
- `d3dxdm.ini`: `direct_mode=sbs`, sep 50 / conv 2.0, FPS monitor off
- Launch bat: `steam://rungameid/208650` only
- Game ini: 1920×1080, `Fullscreen=True`, `UpscaleScreenPercentage=False`, read-only

## Launch
Use Desktop `Launch_ArkhamKnight_3D.bat` (or the one in Win64).
Optional HDR watchdog: `scripts\Disable-DisplayHdr.ps1 -WatchSeconds 120`
