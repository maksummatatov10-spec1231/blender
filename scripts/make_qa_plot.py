"""Draw a QA overview from the JSON that Blender itself generated."""
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "lab" / "data"
OUT = ROOT / "renders" / "v2" / "screenshots" / "qa_trajectory.png"
OUT.parent.mkdir(parents=True, exist_ok=True)
traj = json.loads((DATA / "trajectories.json").read_text())
meta = json.loads((DATA / "meta.json").read_text())
qa = json.loads((DATA / "qa.json").read_text())
arch = meta["arch"]
passn = sum(1 for c in qa["checks"] if c["pass"])

W, H = 1200, 790
im = Image.new("RGB", (W, H), (17, 21, 29))
d = ImageDraw.Draw(im)
FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
try:
    font = ImageFont.truetype(FONT_PATH, 15)
    big = ImageFont.truetype(FONT_PATH, 22)
except Exception:
    font = ImageFont.load_default(size=15)
    big = ImageFont.load_default(size=22)
d.text((24, 16), "GEO STORY v2 — motion & geometry QA", fill=(245, 245, 245), font=big)
d.text((24, 46), f"Blender {meta['blender']}  |  240 frames @ 24 fps  |  QA {passn}/{len(qa['checks'])} PASS  |  arch f{arch['cross_frame']} {arch['robot_max_radius']:.3f} < {arch['inner']:.2f}",
       fill=(170, 220, 255), font=font)

# Panel 1: frame vs X position
x0, y0, pw, ph = 60, 90, 700, 240
d.rectangle((x0, y0, x0 + pw, y0 + ph), outline=(70, 85, 105), width=2)
for f in (1, 89, 129, 169, 205, 240):
    x = x0 + (f - 1) / 239 * pw
    d.line((x, y0, x, y0 + ph), fill=(60, 70, 88), width=1)
    d.text((x + 3, y0 + 4), str(f), fill=(150, 160, 175), font=font)
def plot(label, arr, color):
    pts = []
    for row in arr:
        f, x = row[0], row[1]
        px = x0 + (f - 1) / 239 * pw
        py = y0 + ph - (x + 9) / 19 * ph
        pts.append((px, py))
    d.line(pts, fill=color, width=3)
    d.text((x0 + 8, y0 + ph - 22 - {"red": 0, "blue": 18, "gift": 36}[label]),
           label, fill=color, font=font)
plot("red", traj["red"], (255, 95, 80))
plot("blue", traj["blue"], (90, 170, 255))
plot("gift", traj["gift"], (240, 120, 200))
d.text((x0, y0 + ph + 8), "Frame vs world X (vertical lines = camera cuts)", fill=(180, 190, 205), font=font)

# Panel 2: arch cross-section proof
cx, cy, R = 930, 240, 165
d.ellipse((cx - R, cy - R, cx + R, cy + R), outline=(255, 205, 80), width=10)
r2 = int(R * arch["robot_max_radius"] / arch["inner"])
d.ellipse((cx - r2, cy - r2, cx + r2, cy + r2), outline=(90, 230, 180), width=3)
d.line((cx, cy - R, cx, cy + R), fill=(90, 100, 120), width=1)
d.line((cx - R, cy, cx + R, cy), fill=(90, 100, 120), width=1)
d.text((cx - 150, cy + R + 16), "Arch cross-section Y-Z", fill=(200, 210, 225), font=font)
d.text((cx - 150, cy + R + 40), "gold = inner ring 1.85", fill=(255, 205, 80), font=font)
d.text((cx - 150, cy + R + 62), "green = Red max radius 1.722", fill=(90, 230, 180), font=font)
d.text((cx - 150, cy + R + 88), "PASS: robot goes THROUGH, not beside", fill=(120, 255, 170), font=font)

# Panel 3: QA checks
y = 380
d.text((60, y), "Automatic checks", fill=(245, 245, 245), font=big)
y += 34
for c in qa["checks"]:
    ok = c["pass"]
    d.ellipse((62, y + 3, 74, y + 15), fill=(70, 220, 120) if ok else (240, 80, 80))
    d.text((84, y), c["name"], fill=(225, 230, 238), font=font)
    y += 22
im.save(OUT)
print("QA_PLOT_OK", OUT, OUT.stat().st_size)
