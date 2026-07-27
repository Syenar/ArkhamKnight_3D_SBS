"""Guard d3dxdm [Present] convergence reads that spam Operand type 50.

Keeps Key hotkeys (Ctrl+F3..F6) and presets; only skips evaluating
`convergence` when dm_stereo_enabled is 0 (type-50 outside stereo).
"""
from __future__ import annotations

import re
import sys
from pathlib import Path


def patch(text: str) -> str:
    # Wrap the two always-on convergence expressions.
    text = text.replace(
        """if ((convergence * $increaseconvergencefast) - convergence) < 0.01
	$increaseconvergencefast = (convergence + 0.01) / convergence
endif""",
        """if dm_stereo_enabled
	if ((convergence * $increaseconvergencefast) - convergence) < 0.01
		$increaseconvergencefast = (convergence + 0.01) / convergence
	endif
endif""",
    )
    text = text.replace(
        """if (convergence - (convergence * $decreaseconvergencefast)) < 0.01
	$decreaseconvergencefast = (convergence - 0.01) / convergence
endif""",
        """if dm_stereo_enabled
	if (convergence - (convergence * $decreaseconvergencefast)) < 0.01
		$decreaseconvergencefast = (convergence - 0.01) / convergence
	endif
endif""",
    )
    # Presets that assign separation/convergence only when stereo on.
    text = re.sub(
        r"(?m)^(preset = Preset(?:Increase|Decrease)(?:Convergence|Separation|PopoutBias)(?:Slow|Fast)\s*)$",
        r"if dm_stereo_enabled\n\t\1\nendif",
        text,
    )
    return text


def main() -> None:
    src = Path(sys.argv[1])
    dst = Path(sys.argv[2]) if len(sys.argv) > 2 else src
    raw = src.read_text(encoding="utf-8")
    out = patch(raw)
    if out == raw:
        raise SystemExit("no replacements made — d3dxdm Present shape changed")
    dst.write_text(out, encoding="utf-8")
    print("patched", dst, "delta", len(out) - len(raw))


if __name__ == "__main__":
    main()
