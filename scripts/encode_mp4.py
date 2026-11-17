"""Encode the rendered PNG sequence into the final H.264 MP4."""
import glob
import os
import subprocess
import imageio_ffmpeg

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FR = os.path.join(ROOT, "renders", "frames")
OUT = os.path.join(ROOT, "geo_cartoon.mp4")
frames = sorted(glob.glob(os.path.join(FR, "frame_*.png")))
if len(frames) != 120:
    raise SystemExit(f"Expected 120 frames, found {len(frames)}")

ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
cmd = [
    ffmpeg, "-y", "-hide_banner", "-loglevel", "warning",
    "-framerate", "24",
    "-start_number", "1",
    "-i", os.path.join(FR, "frame_%04d.png"),
    "-frames:v", "120",
    # 720x405 -> 720x406: yuv420p requires even dimensions
    "-vf", "pad=ceil(iw/2)*2:ceil(ih/2)*2",
    "-c:v", "libx264", "-preset", "medium", "-crf", "18",
    "-pix_fmt", "yuv420p", "-movflags", "+faststart",
    "-metadata", "title=Geo Circus — Blender 5.3.0 geometric cartoon",
    OUT,
]
print("ENCODING", " ".join(cmd), flush=True)
subprocess.run(cmd, check=True)
print("MP4_OK", OUT, os.path.getsize(OUT), "bytes", flush=True)
