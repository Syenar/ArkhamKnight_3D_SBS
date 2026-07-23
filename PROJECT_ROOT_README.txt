ARKHAM 3D PROJECTS

Purpose
Separate, documented projects for getting Batman: Arkham Knight and Batman: Arkham City into true stereoscopic 3D for a 3D projector first, then evaluating VR display options.

Current status
- Neither game is installed in the C: or D: Steam libraries currently registered on this PC.
- No game files, executables, or rendering DLLs have been changed.
- Install each game through Steam before beginning its project checklist.

Project folders
- Arkham Knight 3D\ARKHAM_KNIGHT_3D_PLAN.txt
- Arkham City 3D\ARKHAM_CITY_3D_PLAN.txt

Shared goal
1. Achieve true left/right stereoscopic output in Story Mode.
2. Start with SBS (side-by-side) because it is easiest to validate on the projector.
3. Test TAB (top-and-bottom) if the projector supports it; this can preserve more horizontal detail.
4. Only consider VR after stable projector stereo works.

Shared technology
- Existing game-specific HelixMod / 3D Vision fix.
- Geo-11, a DX11/DX9 stereoscopic driver that can output SBS, TAB, or interlaced images.
- 3D Fix Manager, where compatible, to manage fixes and display settings.

Safety rules
- Keep Steam’s original game installation recoverable through Verify Integrity of Game Files.
- Copy/record all added mod files before changing anything.
- Never use random DLL downloads; use the documented HelixMod / Geo-11 sources for the game-specific fix.
- Test one game at a time.
- Do not start building a custom mod unless the known stereo fix fails on the exact installed game version.
