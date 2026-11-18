"""Encode the 240-frame GEO STORY v2 PNG sequence into the final H.264 MP4."""
import glob
import os
import subprocess
import imageio_ffmpeg

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FR = os.path.join(ROOT, "renders", "v2", "frames")
OUT = os.path.join(ROOT, "geo_story_v2.mp4")
frames = sorted(glob.glob(os.path.join(FR, "frame_*.png")))
if len(frames) != 240:
    raise SystemExit(f"Expected 240 frames, found {len(frames)} in {FR}")

ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
cmd = [
    ffmpeg, "-y", "-hide_banner", "-loglevel", "warning",
    "-framerate", "24", "-start_number", "1",
    "-i", os.path.join(FR, "frame_%04d.png"),
    "-frames:v", "240", "-an",
    "-vf", "pad=ceil(iw/2)*2:ceil(ih/2)*2",
    "-c:v", "libx264", "-preset", "medium", "-crf", "18",
    "-pix_fmt", "yuv420p", "-movflags", "+faststart",
    "-metadata", "title=GEO STORY v2 — Red visits Blue (Blender 5.3.0)",
    OUT,
]
print("ENCODING_V2", " ".join(cmd), flush=True)
subprocess.run(cmd, check=True)
print("MP4_V2_OK", OUT, os.path.getsize(OUT), "bytes", flush=True)
