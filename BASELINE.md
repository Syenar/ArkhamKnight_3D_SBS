# Arkham Knight 3D — Stable baseline (2026-07-24)

## Full SBS compatibility

**Full SBS is compatible** with geo-11 on this stack. It is not a separate unsupported mode.

- geo-11 `direct_mode = sbs` outputs **half** SBS (960+960 into 1920).
- **Full SBS** (1920 per eye) = same stereo path + `upscaling=1` with `width=3840` `height=1080`.
- Projector must be set to **Full Side-by-Side** (not Half). If the projector only accepts Half SBS, use half packing instead.

## Locked stable files

Copied from live `Binaries\Win64` into `working_config/`:

| Item | Value |
|------|--------|
| force_stereo | 2 |
| force_no_nvapi | 1 |
| direct_mode | sbs |
| upscaling | 0 (enable after eye proof) |
| show_fps_monitor | false |
| nvapi64 / dxgi | absent |
| Helix ShaderFixes | off |
| Game Res | 1920x1080, InteractiveSmoke=False |
| BmSystemSettings encoding | UTF-8 **without BOM** |

## Do not

- Rewrite `BmSystemSettings.ini` with PowerShell `Set-Content -Encoding UTF8` (adds BOM → Fatal).
- Reinstall full Helix light fixes on AMD until bare SBS works.
- Stack dxgi + d3d11 until packing is proven.

## Next

1. Anaglyph eye proof  
2. Half SBS visible  
3. Full SBS 3840x1080  
4. Optional: 3Dmigoto 1.3.16 dxgi / Loader  
