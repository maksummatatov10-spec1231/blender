"""Diagnostic renders: real skeleton (bones) and visible motion paths.

Usage: blender -b geo_cartoon.blend --python scripts/verify_screens.py
Does NOT save the .blend, so the delivered file keeps its clean render state.
"""
import bpy
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "renders", "screenshots")
os.makedirs(OUT, exist_ok=True)
scene = bpy.context.scene
scene.render.engine = "CYCLES"
scene.cycles.device = "CPU"
scene.cycles.samples = 16
scene.cycles.use_denoising = True
scene.render.use_motion_blur = False
scene.render.resolution_percentage = 100
scene.render.image_settings.media_type = "IMAGE"
scene.render.image_settings.file_format = "PNG"
scene.render.image_settings.color_mode = "RGB"
scene.frame_set(44)

drawables = [o for o in bpy.data.objects if o.type in {"MESH", "CURVE"}]
bonemesh = [o for o in drawables if o.name.startswith("BONEVIZ_")]
paths = [o for o in drawables if o.name.startswith(("Path_", "ArcMarker_"))]
stage = [o for o in drawables if o.name in ("Stage_Ground", "Backdrop")]

def visibility(keep):
    for o in drawables:
        o.hide_render = o not in keep

# 1) Skeleton screenshot — only the emissive bone/joint visualizers
visibility(set(bonemesh) | set(stage))
for o in bonemesh:
    try:
        o.hide_set(False)
    except Exception:
        pass
scene.render.filepath = os.path.join(OUT, "skeleton.png")
bpy.ops.render.render(write_still=True)
print("SKELETON_SHOT_OK", flush=True)

# 2) Motion-path screenshot — trajectories + keyframe markers, stock camera
visibility(set(paths) | set(stage))
scene.render.filepath = os.path.join(OUT, "motion_paths.png")
bpy.ops.render.render(write_still=True)
print("PATHS_SHOT_OK", flush=True)

# 3) Skeleton + character overlay (semi proof that bones drive the mesh)
visibility(set(bonemesh) | set(stage) | {bpy.data.objects["Hero_Body"]})
scene.render.filepath = os.path.join(OUT, "skeleton_overlay.png")
bpy.ops.render.render(write_still=True)
print("OVERLAY_SHOT_OK", flush=True)

print("VERIFY_SCREENS_DONE", flush=True)
