# Prior chat chain (cursor_3d_batman_arkham_project.md) — what actually happened

## Goal
Half-SBS 3D at 1080p on projector. Visible L|R from menus onward.

## What worked (~15:21 Jul 23) — USER CONFIRMED
User said "ok good now", then saw real depth (lights/shadows swim when changing separation).
Agent stack at that moment:
- bare geo-11 (NO Helix UE3/hash ShaderFixes)
- force_stereo=2, direct_mode=sbs
- upscaling=1 + include ShaderFixes\upscale.ini (same-res 1920x1080 packer Present path)
- dxgi.dll present (3Dmigoto) for early inject
- steam://rungameid/208650 launch
- Proof: working_config/half_sbs_proof.png + sbs_after_sep.png (L/R diff ~110, ~9px parallax)

## What broke it (after that)
1. Helix light/shader pack install → Fatal on AMD (~80s)
2. Strip shaders, thrash relaunches
3. "NVIDIA presets" applied: dm_separation=100, dm_convergence=168 (wrong geo-11 scale; conv should be ~2.0)
4. 8K feel: BmSystemSettings 3840x2160 + get_resolution_from=large_2d_depth_stencil...
5. Hotkey bug: dm_stereo_enabled = !dm_stereo_enabled replaced with = 1 → F8/Ctrl+T dead
6. dxgi / nvapi overlap thrash → DLL errors / Fatals when re-added
7. Agents contradicting the working comment and swapping in 3dvision2sbs / Loader experiments

## What the prior chat itself concluded later
- Bare SBS **without dxgi** can stay stable (task 13883) after light-fix removal
- dxgi often Fatals/hangs on this AMD box even though it was present at 15:21
- upscaling=1 + upscale.ini is still the packer (not game 4K upscale)
- Never reinstall Helix light fixes until packer is solid again
- show_fps_monitor=true can crash launch; use Ctrl+F if needed

## Do not
- Set conv=168 / treat NVIDIA 3D Vision numbers as geo-11 DirectMode units
- Re-enable Helix ShaderFixes on AMD
- Global-replace dm_stereo_enabled
- Call the user-verified working comment "wrong"