"""Build the constant image set used for screenshot verification."""
from PIL import Image, ImageDraw, ImageFont
import os
import shutil

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FR = os.path.join(ROOT, "renders", "frames")
OUT = os.path.join(ROOT, "renders", "screenshots")
os.makedirs(OUT, exist_ok=True)

KEY = [1, 12, 20, 28, 36, 44, 52, 60, 68, 84, 100, 120]
ALL = list(range(1, 121))

def load(f):
    p = os.path.join(FR, f"frame_{f:04d}.png")
    return Image.open(p).convert("RGB") if os.path.exists(p) else None

def label(draw, xy, text, font):
    x, y = xy
    draw.rectangle([x, y, x + 150, y + 20], fill=(12, 12, 24))
    draw.text((x + 5, y + 3), text, fill=(240, 240, 255), font=font)

try:
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 13)
except Exception:
    font = ImageFont.load_default()

# 12-frame storyboard
thumb_w, thumb_h, cols = 360, 203, 4
rows = (len(KEY) + cols - 1) // cols
sheet = Image.new("RGB", (cols * thumb_w, rows * (thumb_h + 24)), (16, 16, 30))
d = ImageDraw.Draw(sheet)
for i, f in enumerate(KEY):
    im = load(f)
    if im is None:
        continue
    im = im.resize((thumb_w, thumb_h), Image.LANCZOS)
    x, y = (i % cols) * thumb_w, (i // cols) * (thumb_h + 24)
    sheet.paste(im, (x, y))
    label(d, (x, y + thumb_h), f"frame {f:03d}  t={(f-1)/24:.2f}s", font)
sheet.save(os.path.join(OUT, "contact_sheet.png"))

# Every single frame, as a constant visual record
cols, tw, th = 12, 120, 68
rows = (len(ALL) + cols - 1) // cols
grid = Image.new("RGB", (cols * tw, rows * (th + 16)), (14, 14, 26))
d = ImageDraw.Draw(grid)
for i, f in enumerate(ALL):
    im = load(f)
    if im is None:
        continue
    im = im.resize((tw, th), Image.LANCZOS)
    x, y = (i % cols) * tw, (i // cols) * (th + 16)
    grid.paste(im, (x, y))
    d.text((x + 2, y + th + 1), f"{f:03d}", fill=(210, 210, 235), font=font)
grid.save(os.path.join(OUT, "all_frames.png"))

# Standalone verification screenshots
for f in (1, 36, 44, 60, 100, 120):
    src = os.path.join(FR, f"frame_{f:04d}.png")
    if os.path.exists(src):
        shutil.copy(src, os.path.join(OUT, f"frame_{f:04d}.png"))

print("CONTACT_SHEETS_OK", os.listdir(OUT))
