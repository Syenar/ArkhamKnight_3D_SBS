# Milestone v0.6.0 — Loader `dxgi` unlocks stock packer L|R

**User confirmed:** 2026-07-24 ~13:36 (local) — visible left-right split (“that just fucking works”).

**Authority:** eyeball only. Process-alive / StereoProfile / log flags are not proof.

This document is the complete replication recipe. Follow it exactly. Do not substitute the old v0.5.0 `dxgi.dll`.

---

## 1. One-sentence root cause

Visible half-SBS needs **stock geo-11 `d3d11` + Present `CustomShaderUpscale` packer + the geo-11 *loader* `dxgi.dll`**.  
The older `working_config` `dxgi` (`8603C2CB…`) made the same packer **Fatal** (AddRef null) and flooded **Operand type 50** bugs; the loader `dxgi` (`5B871985…`) does not.

---

## 2. Locked file set (copy these, these hashes)

| Role | Exact file to use | SHA256 | Size |
|---|---|---|---|
| Stereo driver | `downloads\extracted_geo11_v0.7.10\x64\d3d11.dll` | `C89AEE44CCFA0240E1BFEA37F5F7357514AA6FBCB2E92AD34A974AC192BC0E4E` | 13661696 |
| Early inject **REQUIRED** | `downloads\extracted_geo11_v0.7.10\loader\x64\dxgi.dll` → also locked as `working_config\dxgi.dll` | `5B8719852BBA918166CA3C8F25BDB3A41E65DA1090720B3931B66B0AB3220BB6` | **174080** |
| NVAPI shim | `downloads\extracted_geo11_v0.7.10\x64\nvapi64.dll` | `6537BAC7CE310A0F92E199AFC4CDD0D0B58FD5F272E59B687609A0E5C9DC993C` | 258560 |
| Device / packer ini | `working_config\d3dx.ini` | `9E6569BDDEAED5574BD0C0DD8249A7E229145E21E77C98DFEE4866E5B9833B05` | 58259 |
| DirectMode ini | `working_config\d3dxdm.ini` | `4B0F602691C83C8CBADB7F50E0E70B1714EECC6264AE4B8B953DA3A5D6CBF71D` | 18786 |
| Present packer | stock `ShaderFixes\upscale.ini` | `DE2BBD916F9801720133FA72BC8F49272FE6B7A36C45459429C161ECBE2FA4C7` | (stock) |
| Game res | `working_config\BmSystemSettings.ini` + `UserSystemSettings.ini` | Fullscreen=True, 1920×1080 | |

Also stored:
- `working_config\dxgi.dll.loader_geo11_v0.7.10` — same bytes as good dxgi
- `working_config\dxgi.dll.v050_legacy_8603C2CB_FATAL` — **DO NOT USE** (old 146944-byte dxgi)

See `HASHES_v0.6.0.txt`.

---

## 3. Exact live layout after restore

Target directory:

`D:\SteamLibrary\steamapps\common\Batman Arkham Knight\Binaries\Win64\`

Must contain:

```
d3d11.dll          ← stock geo-11 x64 only (NEVER patched_v9/v11/v12)
dxgi.dll           ← LOADER x64 (5B871985… / 174080 bytes)  *** critical ***
nvapi64.dll        ← stock geo-11 x64
d3dx.ini           ← working_config
d3dxdm.ini         ← working_config
Launch_ArkhamKnight_3D.bat
ShaderFixes\       ← wipe then copy stock geo-11 x64 ShaderFixes (8 source files)
  upscale.ini      ← must have uncommented: run = CustomShaderUpscale
  upscale.hlsl
  (other stock files: 3dvision2sbs*, mouse*)
  upscale.*.bin    ← OK if created at runtime; not required beforehand
```

Must **NOT** contain:

- Helix / UE3 hash ShaderFixes (`UE3_*.ini`, tons of `.txt` fixes)
- Patched `d3d11.dll` from `experimental_fork_20260724_nullguards\patched_dlls\`
- Old dxgi `8603C2CB…` (146944 bytes)
- Extra includes of `3dvision2sbs.ini` in `d3dx.ini` (stock packer path only)

Game config:

`D:\SteamLibrary\steamapps\common\Batman Arkham Knight\BmGame\Config\`

- `BmSystemSettings.ini`: `Fullscreen=True`, `ResX=1920`, `ResY=1080`
- `UserSystemSettings.ini`: same

---

## 4. Required INI keys (must match)

### `d3dx.ini` (Device / Include)

```ini
include = ShaderFixes\upscale.ini
upscaling = 1
width = 1920
height = 1080
upscale_mode = 1
full_screen=0
force_stereo = 2
get_resolution_from = swap_chain
```

### `d3dxdm.ini`

```ini
direct_mode = sbs
dm_stereo_enabled = 1
dm_separation = 50
dm_convergence = 2.0
```

(Hotkey lines that toggle `dm_stereo_enabled` may exist; leave them as in working_config.)

### `ShaderFixes\upscale.ini` — `[Present]`

```ini
run = CustomShaderUpscale
```

Must be **uncommented**. This Present command list blits geo-11 `f_bb` → real swap chain `r_bb` via `upscale.hlsl` and `special = upscaling_switch_bb`.

`upscale.hlsl` is a full-screen blit of `ps-t101 = f_bb`. It does **not** invent stereo; it presents whatever DirectMode already put in the faked backbuffer. Without this Present run + `upscaling=1`, output stays mono even when logs say `StereoProfile=1`.

---

## 5. Full wipe + restore procedure (replicate from scratch)

Do this when SBS is broken or after any experiment. Partial “overwrite a few DLLs” is how we lost the stack before.

1. Kill `BatmanAK` (and any Fatal-Message killer if you want a clean start).
2. In `Binaries\Win64`, **delete**:
   - `d3d11.dll`, `dxgi.dll`, `nvapi64.dll`
   - `d3dx.ini`, `d3dxdm.ini`
   - `d3d11_log.txt`, `nvapi_log.txt` (optional)
   - folders `ShaderFixes`, `ShaderFixesDM`, `ShaderCache`, `ShaderCacheDM`
3. Copy **stock** geo-11:
   - `downloads\extracted_geo11_v0.7.10\x64\d3d11.dll`
   - `downloads\extracted_geo11_v0.7.10\x64\nvapi64.dll`
   - entire `...\x64\ShaderFixes\` → live `ShaderFixes\`
4. Copy **working_config**:
   - `d3dx.ini`, `d3dxdm.ini`
   - **`dxgi.dll`** (must be loader hash `5B871985…`)
   - `Launch_ArkhamKnight_3D.bat`
   - `BmSystemSettings.ini`, `UserSystemSettings.ini` → `BmGame\Config\` (clear read-only first)
5. Verify hashes (see §2) and keys (see §4).
6. Confirm `ShaderFixes\upscale.ini` has `run = CustomShaderUpscale` uncommented.
7. Launch **once** via:

```bat
@echo off
cd /d "D:\SteamLibrary\steamapps\common\Batman Arkham Knight\Binaries\Win64"
start "" steam://rungameid/208650
exit /b 0
```

8. Success criteria: **visible L|R split** on title / in-game (user eyeball).  
   Optional log health: `Operand type 50` count ≈ 0; `StereoProfile` present; process stays up past ~50s / ~4.5GB+.

Or run: `working_config\Ensure-SbsStack.ps1` (updated for v0.6.0 hash checks) then the bat.

---

## 6. What the working session actually was (forensics)

### Confirmed working combination (this milestone)

| Piece | Value |
|---|---|
| Time | 2026-07-24 ~13:29 launch, ~13:36 user confirm |
| `d3d11` | stock `C89AEE44…` (unpatched) |
| `dxgi` | loader `5B871985…` |
| Packer | `upscaling=1`, 1920×1080, `CustomShaderUpscale` ON |
| DirectMode | `direct_mode=sbs` |
| Launch | Steam `208650` |
| Log | `Operand50=0`, `StereoProfile=1`, process ~4.7–5.5GB alive |
| User words | “left-right split … that just fucking works” |

### Immediately preceding failed states (do not regress)

| Attempt | Result |
|---|---|
| Exact v0.5.0 with **legacy** dxgi `8603C2CB…` + stock packer | Fatal ~28s at geo-11 AddRef (`d3d11+0x1a5abc`) |
| Same stack, Present packer commented / `upscaling=0` | Alive, **mono** |
| Legacy dxgi aside (no dxgi) | Alive, Operand50=0, still **mono** |
| Red overlay `BUG: Operand type 50…` | Caused by **legacy** dxgi double-hook; noise for stereo, but marker of wrong dxgi |
| Patched `d3d11` v11 (native VS/PS call-through) + packer | Alive, **mono** (skips stereo wrapper path) |
| v12 soft-native | New Fatals |
| `width=3840` double-wide experiment | “Weird”, still read as mono |
| `full_screen=1` | Odd client sizes; not part of lock |
| Helix light ShaderFixes | Historic Fatal break (AMD) — never reinstall for this recipe |
| Anaglyph / no-packer probes | Did not re-establish visible stereo |

### Why v0.5.0 “Exact” stopped Fatalling-free

v0.5.0 locked the **wrong dxgi binary** relative to today’s packer survival:

- v0.5.0 / old chat: `working_config\dxgi.dll` = `8603C2CB…` (146944) — user-confirmed SBS earlier in the week, later Fatal+spam on packer restore.
- v0.6.0: replace with geo-11 package **loader** `dxgi.dll` = `5B871985…` (174080).

Same `d3dx.ini` / `d3dxdm.ini` content and same stock `d3d11`. The dxgi swap is the milestone delta.

NvAPI still logs `NvAPI_Initialize failed` / `unable to retrieve GetFakeDirectMode` on AMD — **same as when SBS worked**. Ignore for pass/fail.

---

## 7. Hard rules (agents + humans)

1. **Never remove `dxgi.dll`.** Without it → mono.  
2. **Never put back legacy `8603C2CB…` dxgi** “because v0.5.0 said so.” That binary Fatals the packer now.  
3. **Never ship patched `d3d11` (v11 etc.)** as the SBS solution — it can stay alive while forcing mono.  
4. **Never turn off the packer** (`upscaling=0` / comment `run = CustomShaderUpscale`) to “stabilize” — that is mono.  
5. **Never install Helix UE3/hash ShaderFixes** on this AMD box for this recipe.  
6. **Launch only** `steam://rungameid/208650`.  
7. Pass/fail = **visible L|R**, not log flags, not BitBlt/PrintWindow captures (often black on this title).

---

## 8. Quick verify checklist

```text
[ ] dxgi.dll SHA256 starts with 5B871985… and size 174080
[ ] d3d11.dll SHA256 starts with C89AEE44… (stock, not 3324D6F1… v11)
[ ] force_stereo=2
[ ] upscaling=1 / upscale_mode=1 / width=1920 / height=1080
[ ] include = ShaderFixes\upscale.ini
[ ] direct_mode = sbs
[ ] upscale.ini Present: run = CustomShaderUpscale
[ ] No Helix ShaderFixes
[ ] Steam launch 208650
[ ] Eyeball: clear L|R split
```

Optional log:

```text
[ ] Operand type 50 count == 0  (nonzero strongly suggests wrong/legacy dxgi)
[ ] StereoProfile seen
[ ] CustomShaderUpscale / upscaling=1 seen
```

---

## 9. Restore script

`working_config\Ensure-SbsStack.ps1`

- Copies `working_config` inis + **loader** `dxgi`
- Copies stock `d3d11` / `nvapi64` / `ShaderFixes`
- Copies Bm configs
- **Fails** if dxgi hash is not `5B871985…` or if packer keys missing

---

## 10. Repo / tag

- Repo: `https://github.com/Syenar/ArkhamKnight_3D_SBS.git`
- Milestone tag: **v0.6.0**
- Supersedes v0.5.0 dxgi choice; keeps the rest of the packer recipe.

Related docs:

- `STACK.txt` — short lock card  
- `HASHES_v0.6.0.txt` — hash list  
- `FORENSIC_TIMELINE.md` — history of what worked/broke  
- `NEVER_REMOVE_DXGI.txt` / `AGENTS.md` / `.cursor/rules/dxgi-required.mdc` — agent hard rules (updated for loader dxgi)  
- `experimental_fork_20260724_nullguards\` — preserved failed patch work; **not** the working path  
