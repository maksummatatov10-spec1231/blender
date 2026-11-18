"""Render the GEO STORY v2 .blend as a PNG sequence.

The saved scene uses Cycles CPU + camera cuts via timeline markers. Rendering
frame-by-frame keeps camera-marker switching explicit and gives a crash-safe
image sequence that is later encoded into an MP4.

Usage:
  blender --background geo_story_v2.blend --python scripts/render_v2.py -- \
      START END SAMPLES PERCENT BLUR OUTPUT_DIR [FRAME,FRAME,...]
Example:
  ... -- 1 240 14 75 0 renders/v2/frames
  ... -- 0 0 12 75 0 renders/v2/screenshots 1,24,54,...
"""
import bpy, os, sys, time

argv = sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else []
start = int(argv[0]) if len(argv) > 0 else 1
end = int(argv[1]) if len(argv) > 1 else 240
samples = int(argv[2]) if len(argv) > 2 else 14
pct = int(argv[3]) if len(argv) > 3 else 75
blur = int(argv[4]) if len(argv) > 4 else 0
outdir = argv[5] if len(argv) > 5 else "renders/v2/frames"
frames = [int(x) for x in argv[6].split(",")] if len(argv) > 6 and argv[6] else list(range(start, end + 1))
os.makedirs(outdir, exist_ok=True)

scene = bpy.context.scene
scene.render.engine = "CYCLES"
scene.cycles.device = "CPU"
scene.cycles.samples = samples
scene.cycles.use_denoising = True
scene.render.threads_mode = "FIXED"
scene.render.threads = 2
scene.render.resolution_percentage = pct
scene.render.image_settings.media_type = "IMAGE"
scene.render.image_settings.file_format = "PNG"
scene.render.image_settings.color_mode = "RGB"
if hasattr(scene.render, "use_motion_blur"):
    scene.render.use_motion_blur = bool(blur)
if hasattr(scene.cycles, "use_adaptive_sampling"):
    scene.cycles.use_adaptive_sampling = True
if hasattr(scene.cycles, "adaptive_threshold"):
    scene.cycles.adaptive_threshold = 0.06

t0 = time.time()
for i, f in enumerate(frames):
    scene.frame_set(f)
    cam = scene.camera.name if scene.camera else "NONE"
    path = os.path.join(outdir, f"frame_{f:04d}.png")
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    print(f"V2_FRAME {f:04d} {cam} {path} elapsed={time.time()-t0:.1f}s", flush=True)
print(f"RENDER_V2_DONE {len(frames)} frames {time.time()-t0:.1f}s", flush=True)
