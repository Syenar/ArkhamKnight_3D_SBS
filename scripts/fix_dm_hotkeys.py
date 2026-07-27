"""Rewrite d3dxdm.ini sep/conv presets to drive dm_separation / dm_convergence."""
from pathlib import Path
import re
import sys

src = Path(sys.argv[1])
dst = Path(sys.argv[2])
text = src.read_text(encoding="utf-8", errors="replace")

text = re.sub(r"(?m)^dm_separation\s*=\s*.*$", "dm_separation = 80", text)
text = re.sub(r"(?m)^dm_convergence\s*=\s*.*$", "dm_convergence = 1.5", text)

presets = {
    "PresetIncreaseSeparationSlow": """condition = ($increaseSeparation == 1 && $increaseseparationspeed == 0 && $increaseseparationtransition == 1)
$adj_sep = dm_separation + 1
dm_separation = dm_separation + 1
$increaseseparationtransition = 0
transition = 100
transition_type = linear
""",
    "PresetIncreaseSeparationFast": """condition = ($increaseSeparation == 1 && $increaseseparationspeed == 1 && $increaseseparationtransition == 1)
$adj_sep = dm_separation + 1
dm_separation = dm_separation + 1
$increaseseparationtransition = 0
transition = 25
transition_type = linear
""",
    "PresetDecreaseSeparationSlow": """condition = ($decreaseseparation == 1 && $decreaseseparationspeed == 0 && $decreaseseparationtransition == 1)
$adj_sep = dm_separation - 1
dm_separation = dm_separation - 1
$decreaseseparationtransition = 0
transition = 100
transition_type = linear
""",
    "PresetDecreaseSeparationFast": """condition = ($decreaseseparation == 1 && $decreaseseparationspeed == 1 && $decreaseseparationtransition == 1)
$adj_sep = dm_separation - 1
dm_separation = dm_separation - 1
$decreaseseparationtransition = 0
transition = 25
transition_type = linear
""",
    "PresetIncreaseConvergenceSlow": """condition = ($increaseconvergence == 1 && $increaseconvergencespeed == 0 && autoconvergence_enabled == 0 && $increaseconvergencetransition == 1)
$adj_conv = dm_convergence + 0.01
dm_convergence = dm_convergence + 0.01
$increaseconvergencetransition = 0
transition = 100
transition_type = linear
""",
    "PresetIncreaseConvergenceFast": """condition = ($increaseconvergence == 1  && $increaseconvergencespeed == 1 && autoconvergence_enabled == 0 && $increaseconvergencetransition == 1)
$adj_conv = dm_convergence * $increaseconvergencefast
dm_convergence = dm_convergence * $increaseconvergencefast
$increaseconvergencetransition = 0
transition = 50
transition_type = cosine
""",
    "PresetDecreaseConvergenceSlow": """condition = ($decreaseconvergence == 1 && $decreaseconvergencespeed == 0 && autoconvergence_enabled == 0 && dm_convergence > 0.01 && $decreaseconvergencetransition == 1)
$adj_conv = dm_convergence - 0.01
dm_convergence = dm_convergence - 0.01
$decreaseconvergencetransition = 0
transition = 100
transition_type = linear
""",
    "PresetDecreaseConvergenceFast": """condition = ($decreaseconvergence == 1 && $decreaseconvergencespeed == 1 && autoconvergence_enabled == 0 && dm_convergence > 0.01 && $decreaseconvergencetransition == 1)
$adj_conv = dm_convergence * $decreaseconvergencefast
dm_convergence = dm_convergence * $decreaseconvergencefast
$decreaseconvergencetransition = 0
transition = 50
transition_type = cosine
""",
}

for header, body in presets.items():
    pat = re.compile(
        rf"(?ms)(^\[{re.escape(header)}\]\r?\n)(.*?)(?=^\[|\Z)"
    )
    m = pat.search(text)
    if not m:
        raise SystemExit(f"missing section {header}")
    text = text[: m.start()] + m.group(1) + body + "\n" + text[m.end() :]

repls = [
    (
        "if ((convergence * $increaseconvergencefast) - convergence) < 0.01",
        "if ((dm_convergence * $increaseconvergencefast) - dm_convergence) < 0.01",
    ),
    (
        "$increaseconvergencefast = (convergence + 0.01) / convergence",
        "$increaseconvergencefast = (dm_convergence + 0.01) / dm_convergence",
    ),
    (
        "if ((convergence - (convergence * $decreaseconvergencefast)) < 0.01 && $decreaseconvergencespeed == 1)",
        "if ((dm_convergence - (dm_convergence * $decreaseconvergencefast)) < 0.01 && $decreaseconvergencespeed == 1)",
    ),
    (
        "$decreaseconvergencefast = (convergence - 0.01) / convergence",
        "$decreaseconvergencefast = (dm_convergence - 0.01) / dm_convergence",
    ),
    (
        "if ($adj_sep == separation || $adj_conv == convergence || $adj_popout_bias == dm_popout_bias)",
        "if ($adj_sep == dm_separation || $adj_conv == dm_convergence || $adj_popout_bias == dm_popout_bias)",
    ),
    (
        "if ($adj_sep == separation)\n\tpre persist separation = $adj_sep",
        "if ($adj_sep == dm_separation)\n\tpre persist dm_separation = $adj_sep",
    ),
    (
        "if ($adj_conv == convergence)\n\tpre persist convergence = $adj_conv",
        "if ($adj_conv == dm_convergence)\n\tpre persist dm_convergence = $adj_conv",
    ),
]
for a, b in repls:
    text = text.replace(a, b)
    text = text.replace(a.replace("\n", "\r\n"), b.replace("\n", "\r\n"))

dst.write_text(text, encoding="utf-8")
# sanity
assert "$adj_sep = dm_separation + 1" in text
assert "dm_separation = dm_separation + 1" in text
assert "$increaseSeparation" in text
assert "condition = ( == 1" not in text
print("OK", dst)
