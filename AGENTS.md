# Arkham Knight 3D — Agent rules

## #1 — `dxgi.dll` is REQUIRED (read this every time)

**Never remove `dxgi.dll`.**

- Path: `Binaries\Win64\dxgi.dll`
- **Must be the geo-11 v0.7.10 LOADER dxgi** from `working_config\dxgi.dll`
  - SHA256 `5B871985…`, size **174080**
  - Source: `downloads\extracted_geo11_v0.7.10\loader\x64\dxgi.dll`
- Without any dxgi → **mono**
- With legacy dxgi `8603C2CB…` (146944) → packer **Fatal** + Operand type 50 spam — **do not use**
- Do **not** quarantine dxgi to “fix Fatals,” A/B without it, or leave it out of the launch bat
- If you are about to move/rename/delete `dxgi.dll`, **stop**

Also enforced in: `.cursor/rules/dxgi-required.mdc`, `NEVER_REMOVE_DXGI.txt`, `working_config/STACK.txt`

## Locked recipe — v0.6.0

Full detail: `working_config/MILESTONE_v0.6.0_LOADER_DXGI.md`

- stock geo-11 v0.7.10 `d3d11.dll` + `nvapi64.dll` + `ShaderFixes` (unpatched)
- loader `dxgi.dll` (`5B871985…`)
- `force_stereo=2`, `direct_mode=sbs`, `upscaling=1`, `upscale_mode=1`, 1920×1080
- `include = ShaderFixes\upscale.ini` with Present `run = CustomShaderUpscale`
- Steam `steam://rungameid/208650` only
- NO Helix ShaderFixes, NO patched d3d11 (v11 etc.), NO `3dvision2sbs` include

Pass/fail = **visible L|R**, not process alive / StereoProfile alone.

## Do not regress

- Do not reinstall Helix light/hash fixes
- Do not “stabilize” by setting `upscaling=0`
- Do not use experimental_fork patched DLLs as the default path
- Do not use width=3840 unless the user asks for that experiment again
