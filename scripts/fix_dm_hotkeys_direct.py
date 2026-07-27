"""Simplify d3dxdm.ini depth keys to direct dm_* assigns (no Present presets)."""
from pathlib import Path
import re
import sys

src = Path(sys.argv[1])
dst = Path(sys.argv[2])
text = src.read_text(encoding="utf-8", errors="replace")

text = re.sub(r"(?m)^dm_separation\s*=\s*.*$", "dm_separation = 80", text)
text = re.sub(r"(?m)^dm_convergence\s*=\s*.*$", "dm_convergence = 1.5", text)

new_keys = """
;------------------------------------------------------------------------------------------------------
; v0.6.1 depth keys: assign dm_* directly (Present presets were not adjusting).
; Ctrl+F1 = stereo params overlay (grid/text)
; Ctrl+F3 / F4 = decrease / increase dm_separation
; Ctrl+F5 / F6 = decrease / increase dm_convergence
; Ctrl+T = toggle stereo
; Ctrl+F7 = save (persist)
;------------------------------------------------------------------------------------------------------

[KeyToggleStereo]
Key = ctrl t
type = toggle
dm_stereo_enabled = !dm_stereo_enabled

[KeyToggleOverlayStereoParams]
Key = ctrl F1
type = toggle
show_stereo_params = !show_stereo_params

[KeyDecreaseSeparation]
Key = ctrl F3
type = hold
dm_separation = dm_separation - 2

[KeyIncreaseSeparation]
Key = ctrl F4
type = hold
dm_separation = dm_separation + 2

[KeyDecreaseConvergence]
Key = ctrl F5
type = hold
dm_convergence = dm_convergence - 0.05

[KeyIncreaseConvergence]
Key = ctrl F6
type = hold
dm_convergence = dm_convergence + 0.05

[KeySaveSettings]
Key = ctrl F7
type = hold
pre persist dm_separation = dm_separation
pre persist dm_convergence = dm_convergence
pre persist dm_popout_bias = dm_popout_bias
show_osd_change_indicator = 4
"""

# Replace from [KeyToggleStereo] through end of [KeySaveSettings] block
pat = re.compile(
    r"(?ms)^\[KeyToggleStereo\].*?(?=^;---------------------------------------\r?\n\[CommandListSaveSettings\]|^;---------------------------------------\r?\n\[Present\]|^\[Present\])"
)
m = pat.search(text)
if not m:
    # fallback: from KeyToggleStereo to CommandListSaveSettings
    pat = re.compile(r"(?ms)^\[KeyToggleStereo\].*?(?=^\[CommandListSaveSettings\]|^\[Present\])")
    m = pat.search(text)
if not m:
    raise SystemExit("could not find Key* block to replace")

text = text[: m.start()] + new_keys + "\n" + text[m.end() :]

# Comment out Present preset lines that try to apply sep/conv presets (noise / operand issues)
def comment_preset_lines(section_text: str) -> str:
    out = []
    for line in section_text.splitlines(True):
        if re.match(r"(?i)^\s*preset\s*=\s*Preset(Increase|Decrease)(Separation|Convergence)", line):
            if not line.lstrip().startswith(";"):
                out.append(";" + line)
            else:
                out.append(line)
        else:
            out.append(line)
    return "".join(out)

pres = re.search(r"(?ms)^\[Present\].*", text)
if pres:
    text = text[: pres.start()] + comment_preset_lines(pres.group(0))

dst.write_text(text, encoding="utf-8")
assert "dm_separation = dm_separation + 2" in text
assert "show_stereo_params = !show_stereo_params" in text
print("OK", dst)
