"""Create a lightweight frame archive + lab preview + all-frames overview.

The full 960x540 PNG sequence stays local; GitHub receives a compact JPEG
archive and a 240-frame JPEG preview sequence for the laboratory slider.
"""
import glob
import json
import os
import zipfile
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "renders" / "v2" / "frames"
PREVIEW = ROOT / "renders" / "v2" / "frames_preview"
SHOTS = ROOT / "renders" / "v2" / "screenshots"
ARCHIVE = ROOT / "renders_v2_frames.zip"
META = ROOT / "lab" / "data" / "meta.json"
PREVIEW.mkdir(parents=True, exist_ok=True)
SHOTS.mkdir(parents=True, exist_ok=True)

files = sorted(SRC.glob("frame_*.png"))
if len(files) != 240:
    raise SystemExit(f"Expected 240 full frames, found {len(files)}")

# 240 small JPEGs for the live lab frame slider
for p in files:
    im = Image.open(p).convert("RGB")
    im.thumbnail((480, 270), Image.Resampling.LANCZOS)
    im.save(PREVIEW / (p.stem + ".jpg"), quality=82, optimize=True)

# compact archive with 720x405 JPEG frames
with zipfile.ZipFile(ARCHIVE, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
    for p in files:
        im = Image.open(p).convert("RGB")
        im.thumbnail((720, 405), Image.Resampling.LANCZOS)
        out = PREVIEW / ("archive_" + p.stem + ".jpg")
        im.save(out, quality=88, optimize=True)
        z.write(out, arcname=f"frames/{p.stem}.jpg")
        out.unlink()

# every frame on one overview sheet
cols, tw, th = 16, 96, 54
rows = (len(files) + cols - 1) // cols
sheet = Image.new("RGB", (cols * tw, rows * th), (18, 22, 30))
for i, p in enumerate(files):
    im = Image.open(p).convert("RGB")
    im.thumbnail((tw, th), Image.Resampling.LANCZOS)
    sheet.paste(im, ((i % cols) * tw, (i // cols) * th))
sheet.save(SHOTS / "all_frames.png")

meta = json.loads(META.read_text())
meta["output"]["frames"] = "renders/v2/frames/frame_%04d.png"
meta["output"]["preview"] = "renders/v2/frames_preview/frame_%04d.jpg"
meta["output"]["frame_archive"] = ARCHIVE.name
meta["output"]["frame_archive_bytes"] = ARCHIVE.stat().st_size
meta["output"]["preview_frames"] = 240
mp4 = ROOT / "geo_story_v2.mp4"
if mp4.exists():
    meta["output"]["mp4_bytes"] = mp4.stat().st_size
META.write_text(json.dumps(meta, ensure_ascii=False))
print("ARCHIVE_V2_OK", ARCHIVE, ARCHIVE.stat().st_size,
      "preview", len(files), "all_frames", (SHOTS / "all_frames.png").stat().st_size)
