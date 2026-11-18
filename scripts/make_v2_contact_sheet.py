"""Create a labelled contact sheet from V2 key screenshots."""
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
import sys

src = Path(sys.argv[1] if len(sys.argv) > 1 else "renders/v2/screenshots")
out = Path(sys.argv[2] if len(sys.argv) > 2 else "renders/v2/screenshots/contact_sheet.png")
files = sorted(src.glob("frame_*.png"))
if not files:
    raise SystemExit("no frames")
cols = 4
W, H = 360, 203
LABELS = {1:"Выход / дверь",18:"Забыл закрыть",30:"Дорожка",54:"ПРОХОД СКВОЗЬ АРКУ",
          89:"Синий у окна",100:"Реакция",129:"Подходит / стук",150:"Стук",
          169:"Дверь открыта",186:"Внутри / подарок",205:"Хлопушка",220:"Ленты",240:"Финал"}
FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
try:
    font = ImageFont.truetype(FONT_PATH, 16)
except Exception:
    font = ImageFont.load_default(size=16)
rows = (len(files)+cols-1)//cols
sheet = Image.new("RGB", (cols*W, rows*(H+26)), (18,22,30))
d = ImageDraw.Draw(sheet)
for i,p in enumerate(files):
    im = Image.open(p).convert("RGB")
    im.thumbnail((W,H), Image.Resampling.LANCZOS)
    x,y = (i%cols)*W, (i//cols)*(H+26)
    sheet.paste(im,(x,y))
    f = int(p.stem.split("_")[-1])
    d.text((x+6,y+H+4), f"f{f:03d}  {LABELS.get(f,'')}", fill=(245,245,245), font=font)
sheet.save(out)
print("CONTACT_SHEET_OK",out,sheet.size,len(files))
