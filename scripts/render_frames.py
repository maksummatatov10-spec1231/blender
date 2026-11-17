"""Render the animation to a PNG sequence (one image for EVERY frame).
Usage: blender -b geo_cartoon.blend --python scripts/render_frames.py -- START END [SAMPLES] [PERCENT]
"""
import bpy
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
start = int(args[0]) if len(args) > 0 else bpy.context.scene.frame_start
end = int(args[1]) if len(args) > 1 else bpy.context.scene.frame_end
samples = int(args[2]) if len(args) > 2 else 24
percent = int(args[3]) if len(args) > 3 else 100
blur = int(args[4]) if len(args) > 4 else 0

scene = bpy.context.scene
scene.render.engine = "CYCLES"
scene.cycles.device = "CPU"
scene.cycles.samples = samples
scene.cycles.use_denoising = True
scene.render.resolution_percentage = percent
scene.render.use_motion_blur = bool(blur)
if blur and hasattr(scene.render, "motion_blur_shutter"):
    scene.render.motion_blur_shutter = 0.5
scene.render.image_settings.media_type = "IMAGE"
scene.render.image_settings.file_format = "PNG"
scene.render.image_settings.color_mode = "RGB"
scene.render.image_settings.color_depth = "8"
scene.render.image_settings.compression = 20
scene.render.use_file_extension = True
scene.render.filepath = os.path.join(ROOT, "renders", "frames", "frame_")
os.makedirs(os.path.join(ROOT, "renders", "frames"), exist_ok=True)
scene.frame_start, scene.frame_end = start, end

print(f"RENDER_RANGE {start}-{end} samples={samples} percent={percent}", flush=True)
t0 = time.time()
bpy.ops.render.render(animation=True)
print(f"RENDER_DONE {start}-{end} {time.time()-t0:.1f}s", flush=True)
