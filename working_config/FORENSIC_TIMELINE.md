# Forensic timeline — what actually worked (user-confirmed)

Source of truth: `cursor_3d_batman_arkham_project.md` + transcript `706301e2…`  
User correction (2:52 AM): agent “alive / log stereo” claims are **not** SBS. Only eyeball / your confirmations count.

## Do not reboot for this
You already rebooted after the first break; Fatals continued. Soft-break/GPU theory is **falsified**.

---

## Occasion A — ~15:21 Jul 23 (first SBS)

**User:** “ok good now” (launch path fixed), then real depth (lights/shadows swim with separation).  
**Proof:** `working_config/half_sbs_proof.png` (mtime 15:21).

**What the prior chat had just done (the puzzle piece):**
1. Stable geo-11 with `force_stereo=2` (earlier: **no** `dxgi` — process alive, often still visually mono)
2. Restored **`dxgi.dll`** for AMD early inject
3. Enabled Present packer: **`upscaling=1`** + **`include = ShaderFixes\upscale.ini`** + 1920×1080
4. `direct_mode=sbs`, Steam launch only  
5. **No Helix** UE3/hash ShaderFixes

**Next change that broke it:** installing Helix light/shader fixes for “swim” → Fatal → thrash → mangled ini (wrong sep/conv scales, 8K latch, dead hotkeys, dxgi on/off).

---

## Occasion B — ~03:40 Jul 24 (second SBS — “its working”)

**User:** literally `its working`. Then: “repo v0.5.0 is good.”

**Exact procedure that preceded it** (transcript shell immediately before confirm):
1. Kill game / HDR killer scripts
2. Delete live caches + **remove** live `d3d11/dxgi/nvapi/d3dx/d3dxdm` + wipe `ShaderFixes`
3. Copy **stock** geo-11 `d3d11.dll` + `nvapi64.dll` + `ShaderFixes`
4. Copy **`working_config`**: `d3dx.ini`, `d3dxdm.ini`, **`dxgi.dll`**, Bm/UserSystemSettings (Fullscreen True 1080p)
5. Simple Steam-only bat (no HDR killer)
6. Launch once — no kill loop

**Next change that broke it:** “balance” edit to `d3dxdm.ini` (sep 50→40, conv 2.0→2.5), then more experiments (`upscale_mode=0`, removing `dxgi`, windowed/HDR, DLL patches). You said take a step back and redo what was broken — agents kept patching instead.

---

## Occasion C — “fresh from repo worked first try”

**User (5:03 AM):** last time pulling/starting fresh from the repo worked on first try.  
That matches Occasion B / v0.5.0 lock — **full clean live folder**, not partial `Ensure-SbsStack` sync.

---

## What we were missing (vs blind Exact hash checks)

| Miss | Detail |
|---|---|
| Procedure | 03:40 success was a **full wipe + pristine copy**, not “overwrite a few files” |
| `dxgi.dll` | Required for packed SBS here; agents kept removing it |
| Helix | Light pack after Occasion A is the original break |
| Post-03:40 edits | First intentional change after confirm was sep/conv “balance” |
| False proofs | Process alive ≠ SBS; capture of wrong window ≠ SBS |
| Reboot | Already tried; not the fix |

## Locked recipe (v0.5.0 / STACK.txt)
- stock geo-11 v0.7.10 `d3d11` + `nvapi` + ShaderFixes  
- `working_config` inis + **`dxgi.dll`**  
- `force_stereo=2`, `upscaling=1`, `upscale_mode=1`, `direct_mode=sbs`, 1920×1080 packer  
- Steam `208650` only — **never remove `dxgi.dll`**

---

## Replay result (2026-07-24 ~12:00, this session)

Exact 03:40 wipe+restore (stock `d3d11`, recipe hashes match):
- Got **past** NullRdx (`+0x1a3a46`)
- Fatal at packer **AddRef** (`+0x1a5abc`) — Present/`CustomShaderUpscale` path

### Root cause (Ghidra + A/B)
`CustomShaderUpscale` saves a **native** Windows VS/PS via `VSGetShader`/`PSGetShader`, then geo-11 restores through wrapper `VSSetShader`/`PSSetShader` which AddRefs `[shader+0x30]` (null on native objects).

A/B: comment only `run = CustomShaderUpscale` → stock Exact stays alive (no packer).

### Fix that survives with packer ON
`experimental_fork_…/patched_dlls/d3d11.dll.patched_v11` (+ tools `patch_d3d11_v11_vs_ps.py`):
- NullRdx
- NativeVS call-through (vtbl `+0x58`) when `+0x30` null
- NativePS call-through (vtbl `+0x48`) when `+0x30` null

**2026-07-24 ~12:15:** Exact recipe + `dxgi` + Present packer ON + v11 → process **alive 85s+** (~4.7GB), log `StereoProfile=1`, `CustomShaderUpscale` loaded. User eyeball required for L|R (GDI capture black on this present path).

---

## Occasion D — ~13:36 Jul 24 (v0.6.0 loader dxgi — L|R confirmed)

**User:** left-right split "that just fucking works" (milestone).

**Exact stack that worked:**
1. Full wipe of live stereo DLLs/inis/ShaderFixes/caches
2. Stock geo-11 v0.7.10 d3d11.dll + 
vapi64.dll + ShaderFixes (unpatched)
3. **dxgi.dll from downloads\extracted_geo11_v0.7.10\loader\x64\** (SHA256 5B871985…, 174080 bytes) — NOT legacy working_config dxgi 8603C2CB…
4. working_config d3dx.ini / d3dxdm.ini with packer ON: upscaling=1, 1920x1080, orce_stereo=2, direct_mode=sbs, Present CustomShaderUpscale
5. Steam 208650 launch only
6. Log: Operand50=0, StereoProfile=1, process alive ~4.7GB+

**What this falsified:**
- v11/nullguard patches are not the SBS path (alive-but-mono)
- Turning packer off "to stabilize" = mono
- Legacy dxgi 8603C2CB… = Fatal AddRef + Operand type 50 spam with the same packer
- Operand50 overlay was a wrong-dxgi symptom, not the stereo engine itself

**Lock docs:** MILESTONE_v0.6.0_LOADER_DXGI.md, STACK.txt v0.6.0, HASHES_v0.6.0.txt

