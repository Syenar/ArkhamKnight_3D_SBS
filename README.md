# Batman: Arkham Knight — Half-SBS 3D (geo-11)

**Current lock: v0.6.0** (user-confirmed L|R split, 2026-07-24)

## Start here

1. **Full recipe / replication:** [`working_config/MILESTONE_v0.6.0_LOADER_DXGI.md`](working_config/MILESTONE_v0.6.0_LOADER_DXGI.md)
2. **Short lock card:** [`working_config/STACK.txt`](working_config/STACK.txt)
3. **Hashes:** [`working_config/HASHES_v0.6.0.txt`](working_config/HASHES_v0.6.0.txt)
4. **Restore script:** `working_config/Ensure-SbsStack.ps1` then `Launch_ArkhamKnight_3D.bat`

## Critical fact

Use the **geo-11 loader** `dxgi.dll` (`5B871985…`, 174080 bytes).  
Do **not** use the legacy `8603C2CB…` (146944) dxgi — it Fatals the packer.

**Never remove `dxgi.dll`.** See `NEVER_REMOVE_DXGI.txt` and `AGENTS.md`.
