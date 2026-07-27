# Experimental fork — null-guard / packer crash work (2026-07-24)

Preserved so the exact 15:21 working stack can be restored without losing this work.

## What this fork contains
- `live_snapshot/` — Win64 files as left when forking (includes patched d3d11)
- `patched_dlls/` — d3d11.dll.patched_v* and pre_nullcheck backups
- `tools/` — patch_d3d11_nullguards.py, fatal Message killer, capture/verify scripts

## What we learned (do not mix into working restore)
- force_stereo=2 hits null rdx at geo-11 d3d11+0x1a3a46 → UE3 Fatal dialog
- force_stereo=0 is stable (mono)
- CustomShaderUpscale Present packer can AV on null AddRef (0x1a5abc)
- Helix UE3 ShaderFixes Fatal on this AMD box
- Hotkey `run = CustomShaderUpscale` is invalid in geo-11
- Cave in .text is RX (no runtime vtbl writes); ASLR breaks absolute dummy COM
- Auto-dismiss Fatal Message: tools/kill_fatal_message.cmd

## How to re-apply experimental stack later
1. Stop BatmanAK
2. Copy live_snapshot\* (and ShaderFixes if needed) back to game Win64
3. Or: copy patched_dlls\d3d11.dll.patched_v9 over live d3d11.dll
4. Re-enable packer keys in d3dx.ini if needed

## Do NOT use this fork for the user-confirmed working path
Working path = working_config + stock geo-11 v0.7.10 only (see STACK.txt / PRIOR_CHAT_CHAIN.md).
