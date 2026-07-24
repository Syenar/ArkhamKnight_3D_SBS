# Arkham Knight 3D — Locked half-SBS recipe (2026-07-24)

## What actually packs L|R

Prior verified session (`sbs_after_sep.png`, user said "ok good now"):
**`direct_mode = sbs` alone does not pack the output.**

Required Present packer:

1. `force_stereo = 2`
2. `direct_mode = sbs`
3. `upscaling = 1` with `width = 1920` `height = 1080`
4. `include = ShaderFixes\upscale.ini` (CustomShaderUpscale)
5. no `nvapi64.dll`, no Helix hash ShaderFixes
6. `BmSystemSettings.ini` UTF-8 **without BOM**

**Do not** turn `upscaling` off to "stabilize" — that is how the split was lost.

## dxgi.dll

Optional AMD early-inject. One older working session had it; **2026-07-24** restore with `downloads\dxgi.dll` Fatal'd immediately on render thread → kept **OFF**. Retry only after packer is re-proven (prefer geo-11 loader x64 `dxgi` over the downloads copy).

## Full SBS

Not incompatible. Same packer with `width = 3840` `height = 1080`, projector set to **Full** Side-by-Side.

## Do not

- Rewrite `BmSystemSettings.ini` with PowerShell `Set-Content -Encoding UTF8` (BOM → Fatal).
- Reinstall full Helix light fixes on AMD until packer is solid.
- Global-replace `dm_stereo_enabled` (breaks `= !dm_stereo_enabled` hotkeys).

## Hotkeys

- Ctrl+F1 — Sep/Conv overlay
- Ctrl+F3 / Ctrl+F4 — separation
- Ctrl+F5 / Ctrl+F6 — convergence (±0.15)
- Ctrl+F — FPS overlay

## Launch

`Launch_ArkhamKnight_3D.bat` → Steam `-applaunch 208650`
Projector: **Half SBS**. Title/menu frames can look nearly mono — judge on gameplay.
