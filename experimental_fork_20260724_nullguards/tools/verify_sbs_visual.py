"""Visual SBS gate: require duplicated scene, not just half difference."""
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont


def analyze(path: Path, out_dir: Path) -> str:
    img = Image.open(path).convert("RGB")
    arr = np.asarray(img, dtype=np.float32)
    h, w, _ = arr.shape
    mid = w // 2
    left = arr[:, :mid]
    right = arr[:, mid : mid + left.shape[1]]

    def down(a, nh=160, nw=280):
        im = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).resize(
            (nw, nh), Image.Resampling.BOX
        )
        g = np.asarray(im, dtype=np.float32).mean(axis=2)
        g = (g - g.mean()) / (g.std() + 1e-6)
        return g

    lg, rg = down(left), down(right)
    ncc = float(np.mean(lg * rg))
    mean_diff = float(np.mean(np.abs(left - right)))
    left_mean = float(left.mean())
    right_mean = float(right.mean())

    # Build labeled contact sheet: full | L | R
    left_im = Image.fromarray(left.astype(np.uint8))
    right_im = Image.fromarray(right.astype(np.uint8))
    scale = 480 / h
    fw, fh = int(w * scale), int(h * scale)
    hw = fw // 2
    sheet = Image.new("RGB", (fw + hw * 2 + 40, fh + 40), (20, 20, 20))
    sheet.paste(img.resize((fw, fh)), (10, 30))
    sheet.paste(left_im.resize((hw, fh)), (20 + fw, 30))
    sheet.paste(right_im.resize((hw, fh)), (30 + fw + hw, 30))
    draw = ImageDraw.Draw(sheet)
    draw.text((10, 5), "FULL", fill=(255, 255, 0))
    draw.text((20 + fw, 5), "LEFT HALF", fill=(255, 255, 0))
    draw.text((30 + fw + hw, 5), "RIGHT HALF", fill=(255, 255, 0))
    # center seam on full
    seam_x = 10 + fw // 2
    draw.line((seam_x, 30, seam_x, 30 + fh), fill=(0, 255, 0), width=2)

    out_dir.mkdir(parents=True, exist_ok=True)
    sheet_path = out_dir / "verify_sheet.png"
    sheet.save(sheet_path)
    left_im.save(out_dir / "verify_L.png")
    right_im.save(out_dir / "verify_R.png")
    img.save(out_dir / "verify_full.png")

    if left_mean < 8 and right_mean < 8:
        verdict = "BLACK_FAIL"
    elif left_mean < 8 or right_mean < 8:
        verdict = "HALF_BLACK_FAIL"
    elif ncc >= 0.60 and mean_diff >= 3.0:
        # Similar structure + measurable parallax -> likely true SBS
        verdict = "TRUE_SBS_CANDIDATE"
    elif ncc >= 0.85 and mean_diff < 3.0:
        verdict = "NEAR_IDENTICAL_HALVES"
    elif ncc < 0.35:
        verdict = "MONO_ASYMMETRIC_FAIL"
    else:
        verdict = "NEEDS_HUMAN_EYE"

    print(
        f"verdict={verdict} size={w}x{h} ncc={ncc:.3f} meanDiff={mean_diff:.2f} "
        f"leftMean={left_mean:.1f} rightMean={right_mean:.1f} sheet={sheet_path}"
    )
    return verdict


if __name__ == "__main__":
    analyze(Path(sys.argv[1]), Path(sys.argv[2]))
