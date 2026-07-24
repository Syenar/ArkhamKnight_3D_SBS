# Status after fork + Exact restore (2026-07-24)

## Progress preserved
- Folder: experimental_fork_20260724_nullguards/
- Branch: experimental/nullguard-progress (if committed earlier)
- Contents: patched_dlls v1-v9, tools, live_snapshot, README

## Exact working recipe ON DISK NOW
Ensure-SbsStack PASS:
- stock d3d11 C89AEE44CCFA0240
- dxgi 8603C2CB3AEED294 (REQUIRED — do not remove)
- working_config d3dx.ini / d3dxdm.ini
- force_stereo=2, upscaling=1, upscale_mode=1, direct_mode=sbs, upscale.ini
- Launch only: steam://rungameid/208650 or working_config\Launch_ArkhamKnight_3D.bat

## Launch results today
1. Exact stock → Fatal ~30s at d3d11 NullRdx (same soft-break as post-15:21 thrash in prior chat)
2. Exact + fork v9 nullguards → still Fatal
3. AMD device restart → Access denied (needs elevated reboot)
4. Left Exact stock on disk (no experimental DLL left live)

## Next (matches prior-chat conclusion)
1. Full PC reboot (or elevated GPU driver restart)
2. ONE cold launch via Launch_ArkhamKnight_3D.bat — no kill loops, no patches
3. Only claim SBS if visible L|R like working_config/half_sbs_proof.png
4. If still Fatals after reboot: then carefully re-apply fork v9 ON TOP of Exact recipe (survival only)
