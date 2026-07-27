"""Write stock Present packer on/off into live upscale.ini (for F10 reload)."""
from pathlib import Path
import re
import sys

live = Path(sys.argv[1])
enable = sys.argv[2] == "1"
snap_up = Path(sys.argv[3])

t = snap_up.read_text(encoding="utf-8")
if enable:
    t = re.sub(r"(?m)^;run\s*=\s*CustomShaderUpscale\s*$", "run = CustomShaderUpscale", t)
    if not re.search(r"(?m)^run\s*=\s*CustomShaderUpscale\s*$", t):
        t = re.sub(r"(?m)^(\[Present\]\s*\n)", r"\1run = CustomShaderUpscale\n", t)
else:
    t = re.sub(r"(?m)^run\s*=\s*CustomShaderUpscale\s*$", ";run = CustomShaderUpscale", t)

(live / "ShaderFixes" / "upscale.ini").write_text(t, encoding="utf-8")
print("armed" if enable else "disarmed", "unbind", "UnbindAll" in t)
