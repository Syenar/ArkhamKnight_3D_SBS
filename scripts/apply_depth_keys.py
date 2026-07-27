"""Restore sane geo-11 depth controls: clamp + cycle keys only (no hold runaway)."""
from pathlib import Path
import re
import sys

wc = Path(sys.argv[1])
live = Path(sys.argv[2])
text = wc.read_text(encoding="utf-8", errors="replace")

text = re.sub(r"(?m)^dm_separation\s*=\s*.*$", "dm_separation = 80", text)
text = re.sub(r"(?m)^dm_convergence\s*=\s*.*$", "dm_convergence = 1.5", text)

if "global $sep_synced" not in text:
    text = text.replace(
        "global $popout_bias_step_down = 0.001",
        "global $popout_bias_step_down = 0.001\nglobal $sep_synced = 0",
    )

# Cycle-only controls — hold presets can race separation into thousands
backup = """
[KeySepCycle]
Key = ctrl shift F4
type = cycle
separation = 40, 50, 60, 70, 80, 100, 120, 150

[KeyConvCycle]
Key = ctrl shift F6
type = cycle
convergence = 0.8, 1.0, 1.2, 1.5, 2.0, 2.5, 3.0

[KeySepReset]
Key = ctrl shift F3
type = cycle
separation = 80
convergence = 1.5
"""

needle = "[KeySaveSettings]\nKey = ctrl F7\nrun = CommandListSaveSettings"
needle_cr = "[KeySaveSettings]\r\nKey = ctrl F7\r\nrun = CommandListSaveSettings"
# strip any previous backup keys we may have inserted
text = re.sub(
    r"\n\[KeySepUpNumpad\][\s\S]*?(?=\n;------|\n\[CommandListSaveSettings\]|\n\[Present\])",
    "\n",
    text,
    count=1,
)
if "[KeySepCycle]" not in text:
    if needle in text:
        text = text.replace(needle, needle + "\n" + backup)
    elif needle_cr in text:
        text = text.replace(needle_cr, needle_cr + "\r\n" + backup.replace("\n", "\r\n"))
    else:
        raise SystemExit("KeySaveSettings block not found")

# Disable stock hold keys that can runaway (comment Key lines)
for section in (
    "KeyIncreaseSeparation",
    "KeyDecreaseSeparation",
    "KeyIncreaseConvergence",
    "KeyDecreaseConvergence",
):
    text = re.sub(
        rf"(?ms)^(\[{section}\]\r?\n)Key = ",
        rf"\1; DISABLED runaway hold — use Ctrl+Shift+F4/F6\r\n;Key = ",
        text,
        count=1,
    )

sync = """[Present]
; Force sane stereo params, then keep dm_* mirrored from separation/convergence
if ($sep_synced == 0)
\tseparation = 80
\tconvergence = 1.5
\t$sep_synced = 1
endif
; Clamp — hold bugs previously raced sep to ~2500 and broke L/R
if (separation > 150)
\tseparation = 80
endif
if (separation < 1)
\tseparation = 80
endif
if (convergence > 5)
\tconvergence = 1.5
endif
if (convergence < 0.1)
\tconvergence = 1.5
endif
dm_separation = separation
dm_convergence = convergence
"""

text = re.sub(r"(?m)^\[Present\]\s*\n", sync + "\n", text, count=1)

assert "if ($sep_synced == 0)" in text
assert "$sep_synced = 1" in text
assert "if (separation > 150)" in text
assert "separation = 40, 50, 60, 70, 80, 100, 120, 150" in text
assert "dm_separation = separation" in text
assert "; DISABLED runaway hold" in text

live.write_text(text, encoding="utf-8")

user = live.parent / "d3dx_user.ini"
user.write_text(
    "; AUTOMATICALLY GENERATED FILE - DO NOT EDIT\n"
    ";\n"
    "; Reset to sane SBS defaults (was racing to Sep ~2500)\n"
    ";\n"
    "[Constants]\n"
    "pre persist separation = 80\n"
    "pre persist convergence = 1.5\n"
    "pre persist target_display = -1\n"
    "pre persist dm_popout_bias = 0.02\n",
    encoding="utf-8",
)
print("OK", live)
print("OK", user)
