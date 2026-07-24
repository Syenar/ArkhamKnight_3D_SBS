# Arkham Knight 3D — Status Breakdown

**Date:** 2026-07-23  
**Author:** Agent session notes (honest status for handoff / reset)

---

## 1. Goal (intent)

Get **Batman: Arkham Knight** outputting **visible half side-by-side (half-SBS) stereoscopic 3D** for a **3D projector** on **AMD Radeon RX 7900 XTX**.

| Requirement | Detail |
|---|---|
| Success criteria | Screen shows a clear **left \| right** split with real parallax — not “DLL loaded” or “process alive” |
| Format | **Half SBS** (geo-11 `direct_mode = sbs`) |
| Resolution | **1920×1080** feel — not 4K/8K mono |
| Hardware | AMD (no NVIDIA 3D Vision driver) |
| Stack | geo-11 **v0.7.10** wrapper (`d3d11.dll`) + `d3dx.ini` / `d3dxdm.ini` |
| Out of scope (for now) | Perfect lights/shadows via Helix/masterotaku fixes (those Fatal on this AMD box) |

**Not the goal:** UEBS2 Mods / StereoMod. That repo was only the Cursor workspace that happened to be open.

---

## 2. Where things live

| What | Path |
|---|---|
| **Cursor workspace (open in IDE)** | `C:\Users\samsa\Desktop\Workplace\Projects\UEBS2 Mods` |
| **Actual 3D project (notes, proofs, downloads)** | `C:\Users\samsa\Desktop\Workplace\Projects\Arkham 3D Projects\Arkham Knight 3D\` |
| **Game install (live DLLs / ini)** | `D:\SteamLibrary\steamapps\common\Batman Arkham Knight\` |
| **Live geo-11 folder** | `D:\SteamLibrary\steamapps\common\Batman Arkham Knight\Binaries\Win64\` |
| **Launch bat** | `...\Binaries\Win64\Launch_ArkhamKnight_3D.bat` |
| **Steam app** | `208650` (`BatmanAK.exe`) |
| **geo-11 package** | `...\Arkham Knight 3D\downloads\extracted_geo11_v0.7.10\` |
| **Working config backup** | `...\Arkham Knight 3D\working_config\` |
| **Long log / history** | `...\Arkham Knight 3D\NOTES.txt` |
| **This breakdown** | `...\Arkham Knight 3D\STATUS_BREAKDOWN.md` |

Agents keep editing files under the **game Win64** folder and documenting under the **Arkham Knight 3D** project folder, while Cursor is rooted in **UEBS2 Mods**. Easy to confuse.

---

## 3. Issues currently / recently hitting

### A. Mono output (user-visible failure)
- geo-11 can report stereo on (`force_stereo=2`, `StereoProfile=1`, green FPS) while the picture stays **one full-frame mono image**.
- Half-SBS packing on this AMD box has been unreliable.
- `upscaling=1` + `ShaderFixes\upscale.ini` was the path that once produced a real L\|R proof; it is a **geo-11 Present packer**, not the game “rendering in higher res.”
- Agent screenshots / brightness metrics were **wrong several times** (false “SBS good” on moon-left cinematics, black `CopyFromScreen` on some presents). **User eyeball is the authority.**

### B. Fatals (`Rendering thread exception` / `0xc0000005`)
- Crash stack goes through **game-folder `d3d11.dll` (geo-11)** → `BatmanAK.exe`.
- Reproduced with `force_stereo=2`; `force_stereo=0` (proxy only) stayed alive.
- Not fixed by reboot alone; not explained by Helix leftovers once those were removed.
- Correlated with relaunch thrash and (at one point) massive **nvapi64 LoadLibrary hook spam** in `d3d11_log.txt` (~11MB log).

### C. “8K” feel
- Game ini was often already `1920×1080`.
- Real culprit: `get_resolution_from = large_2d_depth_stencil_if_swap_chain_native` latching **huge UE3 depth targets**, so stereo internal cost feels like 8K.
- Last lock attempt: `get_resolution_from = swap_chain` + explicit `width/height = 1920/1080` (note: `swap_chain` has Fatals’d before on bare stack — tradeoff).

### D. Dead hotkeys (“macro does nothing”)
- Stock geo-11 toggle is: `dm_stereo_enabled = !dm_stereo_enabled`.
- A **global regex** meant to set Device `dm_stereo_enabled = 1` also rewrote the hotkey lines to `= 1`, so F8 / Ctrl+T **never inverted** — looked like “keys do nothing.”
- Fixed on disk when caught; easy to re-break with careless replace-all.

### E. Lights / shadows swim
- Expected on **bare geo-11** without Helix/masterotaku eye fixes.
- Full Helix `UE3_BatmanAK.ini` / hash ShaderFixes → **Fatal ~80s on AMD**.
- Cannot ship light fixes until a non-Fatal subset exists.

---

## 4. Recurring issues (same problems looping)

1. **False success** — process alive / log says stereo ≠ visible SBS. User correctly rejects this every time.
2. **Relaunch thrash** — kill → relaunch → Fatal loops that make diagnosis muddy.
3. **Overlapping proxies** — `d3d11.dll` (geo-11) + `dxgi.dll` (3Dmigoto or geo-11 loader) → hang, Operand spam, or Fatal on this AMD box. On again / off again in notes.
4. **`nvapi64.dll` on AMD** — wrapper + `force_no_nvapi=1` still caused hook spam; removing it helped clarity, didn’t fully end Fatals.
5. **Helix / light-fix temptation** — install fixes → Fatal → strip → SBS works briefly → try lights again → break.
6. **Ini edit footguns** — global replaces break hotkeys; `upscaling` on/off thrash; `get_resolution_from` flips between 8K-feel and Fatal.
7. **Bad automated “proof”** — column brightness / eyeDiff false positives; black captures; vision descriptions disagree with metrics.
8. **Workspace confusion** — working in UEBS2 Mods chat/workspace while the real project is Arkham Knight 3D + game on `D:\`.

---

## 5. What has worked (at least once)

Around **2026-07-23 ~15:21**, agent captured `half_sbs_proof.png` with a real L\|R split (later also measured parallax). Stack intent at that time:

- geo-11 v0.7.10 `d3d11.dll`
- `force_stereo=2`, `force_no_nvapi=1`
- `direct_mode = sbs`
- `upscaling=1` + `include = ShaderFixes\upscale.ini` (packer)
- Game ~1920×1080
- **No Helix hash ShaderFixes**
- Steam launch (`-applaunch 208650`)
- Notes disagree whether `dxgi` was required that moment; later `dxgi` Fatals on this machine

After lights/shader work and audits, that state was **lost** and not cleanly re-proven.

---

## 6. Locked intent on disk (last agent pass)

Treat as **intent**, not as verified success:

| Item | Value |
|---|---|
| `force_stereo` | `2` |
| `direct_mode` | `sbs` |
| Packer | `upscaling=1`, `width/height=1920/1080`, `upscale.ini` Present run |
| `get_resolution_from` | `swap_chain` (avoid large_2d 8K latch) |
| `nvapi64.dll` / `dxgi.dll` | **absent** (disabled) |
| Hotkeys | `dm_stereo_enabled = !dm_stereo_enabled` on Ctrl+T and F8 |
| Game res | `ResX/ResY=1920/1080` |
| Helix light shaders | **off** |

Launch: `Binaries\Win64\Launch_ArkhamKnight_3D.bat`  
Projector: **Half SBS / Side-by-Side**.

---

## 7. What “done” means (acceptance)

Only this:

1. Cold Steam launch via the bat, no Fatal for a full play session.
2. On-screen **half-SBS** (duplicated scene / HUD / green FPS in **both** halves).
3. Feels like **1080p**, not 8K.
4. F8 / Ctrl+T visibly toggles 3D.
5. No Helix Fatal path required for basic play (lights may swim).

Until the user confirms that on the projector/display, the job is **not done**.

---

## 8. Practical rules for the next session

1. Work and document in **Arkham Knight 3D** + **game Win64** — don’t treat UEBS2 Mods as the project.
2. **One** cold launch after a change; no kill-loops.
3. Never claim SBS without a user-confirmed or unambiguous dual-eye proof (e.g. green FPS in both halves).
4. Do not global-replace `dm_stereo_enabled` (breaks `!` hotkeys).
5. Do not reinstall full Helix/masterotaku ShaderFixes on AMD.
6. Prefer fixing **packing + res latch + crash** before lights.

---

## 9. Live session update (2026-07-23 ~17:53)

Agent confirmed in-game: **mono**. geo-11 DirectMode **initializes** (log) but **does not present** half-SBS.

Broken approaches this session: upscale_mode=1 (black-half), 3dvision2sbs packer (wrong path / edge crop).

Disk now: stock DirectMode SBS, ull_screen=1, upscaling=0, no Helix/dxgi/nvapi file.


---

## 10. Session update (2026-07-24 ~01:16)

### Fixed
- **Fatal storm root cause:** BmSystemSettings.ini got a UTF-8 BOM (EF BB BF) from PowerShell Set-Content -Encoding UTF8, which broke UE3 launches (same BatmanAK.exe AV offset even with orce_stereo=0).
- After restoring bak + writing **no BOM**: orce_stereo=0 stable; then orce_stereo=2 **alive 70s+** with Full SBS ini (no Fatal Message).

### Still not done
- Visible **Full SBS packing** not confirmed. Capture showed black-left / content-right (one-eye / bad pack), not clear duplicated L|R.
- 
vapi64 restore failed on AMD (NvAPI_Initialize failed, GetFakeDirectMode missing) — leave **absent** + orce_no_nvapi=1.
- Agent screen captures often hit wrong window (Fight Night) or black PrintWindow — **user eyeball on projector is authority**.

### Disk now
- orce_stereo=2, upscaling=1, width/height=1920/1080 (packing proof pass; bump to 3840x1080 for Full SBS once both halves lit)
- no nvapi, no dxgi, show_fps_monitor=false, BmSystemSettings 1920x1080 no BOM
