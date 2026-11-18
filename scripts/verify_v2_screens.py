"""Diagnostic renders for GEO STORY v2: skeleton, motion paths, arch proof.

Run with Blender 5.3.0:
  blender --background geo_story_v2.blend --python scripts/verify_v2_screens.py
Does NOT save the .blend.
"""
import bpy
import os
from mathutils import Vector

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "renders", "v2", "screenshots")
os.makedirs(OUT, exist_ok=True)
scene = bpy.context.scene
scene.render.engine = "CYCLES"
scene.cycles.device = "CPU"
scene.cycles.samples = 12
scene.cycles.use_denoising = True
scene.render.resolution_percentage = 75
scene.render.image_settings.media_type = "IMAGE"
scene.render.image_settings.file_format = "PNG"
scene.render.image_settings.color_mode = "RGB"
if hasattr(scene.render, "use_motion_blur"):
    scene.render.use_motion_blur = False

def add_cam(name, loc, target, lens):
    bpy.ops.object.camera_add(location=loc)
    c = bpy.context.object
    c.name = name
    c.data.lens = lens
    bpy.ops.object.empty_add(type="PLAIN_AXES", location=target)
    t = bpy.context.object
    t.name = name + "_Target"
    con = c.constraints.new("TRACK_TO")
    con.target, con.track_axis, con.up_axis = t, "TRACK_NEGATIVE_Z", "UP_Y"
    return c

def render(name, frame, cam):
    scene.frame_set(frame)
    scene.camera = cam   # override marker camera for diagnostics
    scene.render.filepath = os.path.join(OUT, name)
    bpy.ops.render.render(write_still=True)
    print("DIAG_OK", name, "frame", frame, flush=True)

meshes = [o for o in bpy.data.objects if o.type in {"MESH", "CURVE"}]
bonemesh = [o for o in meshes if o.name.startswith("BONEVIZ_")]
paths = [o for o in meshes if o.name.startswith(("Path_", "PathRibbon"))]
keep_stage = {"Ground", "SkyBackdrop", "PathRibbon", "GardenArch_Hoop",
              "GardenArch_PostL", "GardenArch_PostR"}
stage = [o for o in meshes if o.name in keep_stage or
         o.name.startswith(("Stone_", "ArchBead_"))]

wide = add_cam("DIAG_Wide", (-5.5, -10.0, 7.0), (3.0, 0.0, 1.6), 24)
archcam = add_cam("DIAG_Arch", (-5.0, 1.30, 2.0), (0.30, 1.30, 1.60), 45)

def visibility(keep):
    for o in meshes:
        o.hide_render = o not in keep

# 1) Skeleton: only cyan bone visualizers + the real path/arch stage
scene.frame_set(54)
visibility(set(bonemesh) | set(stage) | set(paths))
for o in bonemesh + paths:
    o.hide_render = False
render("skeleton.png", 54, wide)

# 2) Motion paths: trajectories + stage, no bone cylinders
scene.frame_set(54)
visibility(set(stage) | set(paths))
for o in paths:
    o.hide_render = False
render("motion_paths.png", 54, wide)

# 3) Clean arch proof: camera looks straight down the +X hole axis
scene.frame_set(54)
visibility(set(meshes))
for o in bonemesh + paths:
    o.hide_render = True
render("arch_pass.png", 54, archcam)

print("VERIFY_V2_SCREENS_DONE", flush=True)
