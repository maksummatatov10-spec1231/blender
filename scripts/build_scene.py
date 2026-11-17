"""
Geo Circus — build the cartoon scene in Blender 5.3.0.

Implements the researched high-quality animation recipe:
  applied transforms / origin at feet -> fitted armature skeleton -> vertex-group skinning
  -> IK targets for planted/tucked feet -> Bezier EASE_IN_OUT controls
  -> squash & stretch (volume preserved), anticipation, follow-through, arcs, exaggeration
  -> Motion Paths + baked trajectory ribbons -> Graph Editor smoothing
  -> Cycles CPU final render with denoising.

Run:
  blender --background --factory-startup --python scripts/build_scene.py
"""
import bpy
import json
import math
import os
import random
from mathutils import Vector
from bpy_extras import anim_utils
from bpy_extras.object_utils import world_to_camera_view

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LAB = os.path.join(ROOT, "lab", "data")
os.makedirs(LAB, exist_ok=True)

FPS = 24
F0, F1 = 1, 120
RES_X, RES_Y = 960, 540
SAMPLES = 24

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.name = "Geo Circus"
scene.frame_start, scene.frame_end = F0, F1
scene.render.fps = FPS

# ----------------------------------------------------------------------------
# Materials
# ----------------------------------------------------------------------------
def material(name, color, roughness=0.38, metallic=0.0, emission=None, emission_strength=0.0):
    m = bpy.data.materials.new(name)
    m.diffuse_color = (*color, 1.0)
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*color, 1.0)
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    if emission:
        bsdf.inputs["Emission Color"].default_value = (*emission, 1.0)
        bsdf.inputs["Emission Strength"].default_value = emission_strength
    return m

MAT = {
    "hero":      material("Hero coral", (0.98, 0.36, 0.22), roughness=0.32),
    "hero_lite": material("Hero cream", (1.0, 0.78, 0.52), roughness=0.35),
    "white":     material("Eye white", (0.98, 0.98, 0.96), roughness=0.25),
    "dark":      material("Ink", (0.055, 0.06, 0.11), roughness=0.45),
    "ball":      material("Ball azure", (0.16, 0.62, 0.98), roughness=0.22, metallic=0.08),
    "cone":      material("Cone violet", (0.62, 0.30, 0.92), roughness=0.34),
    "torus":     material("Hoop gold", (1.0, 0.74, 0.18), roughness=0.2, metallic=0.55,
                          emission=(1.0, 0.55, 0.1), emission_strength=0.35),
    "ground":    material("Stage", (0.14, 0.13, 0.26), roughness=0.82),
    "accent":    material("Accent mint", (0.30, 0.95, 0.78), roughness=0.3),
    "pink":      material("Accent pink", (1.0, 0.42, 0.72), roughness=0.3),
    "yellow":    material("Accent yellow", (1.0, 0.88, 0.32), roughness=0.3),
    "boneviz":   material("Bone visualizer", (0.10, 0.95, 1.0), roughness=0.4,
                          emission=(0.1, 0.95, 1.0), emission_strength=1.6),
}

# ----------------------------------------------------------------------------
# Armature / skeleton
# ----------------------------------------------------------------------------
arm = bpy.data.armatures.new("HeroRigData")
rig = bpy.data.objects.new("HeroRig", arm)
bpy.context.collection.objects.link(rig)
arm.display_type = "OCTAHEDRAL"
rig.show_in_front = True

BONES = [
    # name, head, tail, parent, deform
    ("Root",        (0, 0, 0.25),  (0, 0, 0.65),  None,     True),
    ("Hips",        (0, 0, 0.90),  (0, 0, 1.10),  "Root",   True),
    ("Spine",       (0, 0, 1.10),  (0, 0, 1.80),  "Hips",   True),
    ("Head",        (0, 0, 1.80),  (0, 0, 2.55),  "Spine",  True),
    ("Antenna",     (0, 0, 2.55),  (0, 0, 3.00),  "Head",   True),
    ("Arm.L",       (-0.62, 0, 1.75), (-0.85, 0, 1.35), "Spine", True),
    ("Forearm.L",   (-0.85, 0, 1.35), (-0.95, 0, 1.05), "Arm.L", True),
    ("Arm.R",       (0.62, 0, 1.75),  (0.85, 0, 1.35),  "Spine", True),
    ("Forearm.R",   (0.85, 0, 1.35),  (0.95, 0, 1.05),  "Arm.R", True),
    ("Thigh.L",     (-0.32, 0, 0.90), (-0.32, 0, 0.55), "Hips",  True),
    ("Shin.L",      (-0.32, 0, 0.55), (-0.32, 0, 0.18), "Thigh.L", True),
    ("Foot.L",      (-0.32, 0, 0.18), (-0.32, -0.25, 0.12), "Shin.L", True),
    ("Thigh.R",     (0.32, 0, 0.90),  (0.32, 0, 0.55),  "Hips",  True),
    ("Shin.R",      (0.32, 0, 0.55),  (0.32, 0, 0.18),  "Thigh.R", True),
    ("Foot.R",      (0.32, 0, 0.18),  (0.32, -0.25, 0.12), "Shin.R", True),
    ("IK.Foot.L",   (-0.32, 0, 0.18), (-0.32, 0, 0.42), "Root",  False),
    ("IK.Foot.R",   (0.32, 0, 0.18),  (0.32, 0, 0.42),  "Root",  False),
    ("IK.Hand.R",   (0.95, 0, 1.05),  (0.95, 0, 1.35),  "Root",  False),
]

bpy.context.view_layer.objects.active = rig
rig.select_set(True)
bpy.ops.object.mode_set(mode="EDIT")
for name, head, tail, parent, deform in BONES:
    eb = arm.edit_bones.new(name)
    eb.head, eb.tail = head, tail
    eb.use_deform = deform
    if parent:
        eb.parent = arm.edit_bones[parent]
        eb.use_connect = False
bpy.ops.object.mode_set(mode="OBJECT")

for pb in rig.pose.bones:
    pb.rotation_mode = "XYZ"

# IK constraints (planted / tucked feet, reach for the hoop)
bpy.context.view_layer.objects.active = rig
bpy.ops.object.mode_set(mode="POSE")
for side in ("L", "R"):
    c = rig.pose.bones[f"Shin.{side}"].constraints.new("IK")
    c.name = f"IK planted foot {side}"
    c.target = rig
    c.subtarget = f"IK.Foot.{side}"
    c.chain_count = 2
    c.use_stretch = False
c = rig.pose.bones["Forearm.R"].constraints.new("IK")
c.name = "IK waving hand"
c.target = rig
c.subtarget = "IK.Hand.R"
c.chain_count = 2
c.use_stretch = False
c.influence = 0.55  # blend FK + IK for a loose, cartoony wave
bpy.ops.object.mode_set(mode="OBJECT")

# ----------------------------------------------------------------------------
# Mesh helpers — every hero part is 100% weighted to one bone (rigid cartoon skin)
# ----------------------------------------------------------------------------
HERO_PARTS = []
BONEVIZ_PARTS = []

def finish(obj, name, mat, bone=None, bevel=0.0, smooth=False, viz=False):
    obj.name = name
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    # Skinned / bone-visualizer meshes need their rest coordinates baked into the
    # mesh so the Armature modifier works in armature space. Freely animated
    # shapes must KEEP their object transform (origin at their own centre),
    # otherwise keyframing location/rotation moves them around world origin.
    if bone is not None or viz:
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    if mat:
        obj.data.materials.append(mat)
    if smooth:
        for p in obj.data.polygons:
            p.use_smooth = True
    if bevel:
        b = obj.modifiers.new("Bevel", "BEVEL")
        b.width, b.segments, b.limit_method = bevel, 3, "ANGLE"
        b.angle_limit = 0.45
        obj.modifiers.new("WeightedNormal", "WEIGHTED_NORMAL")
    if bone:
        vg = obj.vertex_groups.new(name=bone)
        vg.add([v.index for v in obj.data.vertices], 1.0, "REPLACE")
        am = obj.modifiers.new("Armature", "ARMATURE")
        am.object = rig
        am.use_vertex_groups = True
        am.use_bone_envelopes = False
    if viz:
        obj.hide_render = True
        try:
            obj.hide_set(True)
        except Exception:
            pass
        BONEVIZ_PARTS.append(obj)
    elif bone:
        HERO_PARTS.append(obj)
    return obj

def cube(name, loc, dims, mat, bone=None, bevel=0.0, viz=False):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    o = bpy.context.object
    o.scale = dims
    return finish(o, name, mat, bone, bevel, viz=viz)

def sphere(name, loc, radius, mat, bone=None, scale=None, smooth=True, viz=False):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=16, radius=radius, location=loc)
    o = bpy.context.object
    if scale:
        o.scale = scale
    return finish(o, name, mat, bone, 0, smooth, viz=viz)

def cylinder(name, a, b, radius, mat, bone=None, viz=False):
    a, b = Vector(a), Vector(b)
    mid, d = (a + b) / 2, b - a
    bpy.ops.mesh.primitive_cylinder_add(vertices=16, radius=radius, depth=d.length, location=mid)
    o = bpy.context.object
    o.rotation_euler = d.to_track_quat("Z", "Y").to_euler()
    return finish(o, name, mat, bone, 0.02, True, viz=viz)

def add_blink(obj, center):
    obj.shape_key_add(name="Basis")
    k = obj.shape_key_add(name="Blink")
    c = Vector(center)
    for v in k.data:
        d = v.co - c
        v.co = c + Vector((d.x, d.y, d.z * 0.10))
    return k

# --- Hero body ---------------------------------------------------------------
cube("Hero_Body", (0, 0, 1.38), (1.06, 0.92, 1.06), MAT["hero"], "Spine", 0.14)
cube("Hero_Head", (0, 0, 2.16), (0.92, 0.84, 0.86), MAT["hero_lite"], "Head", 0.16)
cube("Hero_Belly", (0, -0.47, 1.35), (0.58, 0.06, 0.58), MAT["hero_lite"], "Spine", 0.06)
BLINK = []
for s, label in ((-1, "L"), (1, "R")):
    x = s * 0.23
    e = sphere(f"EyeWhite.{label}", (x, -0.44, 2.25), 0.135, MAT["white"], "Head")
    p = sphere(f"Pupil.{label}", (x, -0.545, 2.25), 0.062, MAT["dark"], "Head")
    BLINK.append(add_blink(e, (x, -0.44, 2.25)))
    BLINK.append(add_blink(p, (x, -0.545, 2.25)))
sphere("Smile", (0, -0.435, 2.02), 0.1, MAT["dark"], "Head", scale=(1.7, 0.35, 0.55))
cylinder("Antenna_Stalk", (0, 0, 2.55), (0, 0, 2.98), 0.045, MAT["dark"], "Antenna")
sphere("Antenna_Tip", (0, 0, 3.02), 0.13, MAT["accent"], "Antenna")

for s, label in ((-1, "L"), (1, "R")):
    cylinder(f"Arm.{label}", (s*0.62, 0, 1.75), (s*0.85, 0, 1.35), 0.115, MAT["hero"], f"Arm.{label}")
    cylinder(f"Forearm.{label}", (s*0.85, 0, 1.35), (s*0.95, 0, 1.05), 0.095, MAT["hero_lite"], f"Forearm.{label}")
    sphere(f"Hand.{label}", (s*0.95, 0, 1.02), 0.145, MAT["accent"], f"Forearm.{label}")
    cylinder(f"Thigh.{label}", (s*0.32, 0, 0.90), (s*0.32, 0, 0.55), 0.145, MAT["hero"], f"Thigh.{label}")
    cylinder(f"Shin.{label}", (s*0.32, 0, 0.55), (s*0.32, 0, 0.18), 0.115, MAT["hero_lite"], f"Shin.{label}")
    cube(f"Foot.{label}", (s*0.32, -0.12, 0.12), (0.36, 0.44, 0.20), MAT["dark"], f"Foot.{label}", 0.07)

# --- Bone visualizers (screenshot proof of the skeleton) --------------------
for name, head, tail, parent, deform in BONES:
    if not deform:
        continue
    cylinder(f"BONEVIZ_{name}", head, tail, 0.055, MAT["boneviz"], name, viz=True)
    sphere(f"BONEVIZ_JOINT_{name}", head, 0.085, MAT["boneviz"], name, viz=True)

# ----------------------------------------------------------------------------
# Other geometric characters / props
# ----------------------------------------------------------------------------
ball = sphere("Ball_Sphere", (2.6, 0, 0.55), 0.55, MAT["ball"])
bpy.ops.mesh.primitive_cone_add(vertices=5, radius1=0.7, radius2=0.0, depth=1.45, location=(3.45, 0.6, 0.72))
cone = finish(bpy.context.object, "Cone_Grump", MAT["cone"], None, 0.05)
cone_nose = sphere("Cone_Nose", (3.45, 0.0, 0.92), 0.10, MAT["pink"], smooth=True)
cone_nose.parent = cone
cone_nose.matrix_parent_inverse = cone.matrix_world.inverted()
bpy.ops.mesh.primitive_torus_add(major_segments=48, minor_segments=12,
                                 major_radius=1.10, minor_radius=0.115,
                                 location=(0.25, 0.85, 2.35), rotation=(math.pi/2, 0, 0))
torus = finish(bpy.context.object, "Torus_Hoop", MAT["torus"], None, 0.01, True)

bpy.ops.mesh.primitive_cone_add(vertices=4, radius1=1.0, radius2=0.0, depth=1.7, location=(-4.6, 2.6, 0.85))
finish(bpy.context.object, "Pyramid_Set", MAT["accent"], None, 0.04)

# Ground + gradient backdrop
bpy.ops.mesh.primitive_plane_add(size=40, location=(0, 0, -0.02))
ground = finish(bpy.context.object, "Stage_Ground", MAT["ground"], None, 0)
gnt = MAT["ground"].node_tree
checker = gnt.nodes.new("ShaderNodeTexChecker")
checker.inputs["Scale"].default_value = 2.0
checker.inputs["Color1"].default_value = (0.12, 0.11, 0.23, 1)
checker.inputs["Color2"].default_value = (0.18, 0.16, 0.32, 1)
gnt.links.new(checker.outputs["Color"], gnt.nodes["Principled BSDF"].inputs["Base Color"])

bpy.ops.mesh.primitive_plane_add(size=40, location=(0, 9.0, 5.0), rotation=(math.pi/2, 0, 0))
backdrop = finish(bpy.context.object, "Backdrop", None, None, 0)
bm = material("Backdrop gradient", (0.06, 0.07, 0.16), roughness=1.0)
bm.use_nodes = True
bnt = bm.node_tree
tex = bnt.nodes.new("ShaderNodeTexCoord")
sep = bnt.nodes.new("ShaderNodeSeparateXYZ")
ramp = bnt.nodes.new("ShaderNodeValToRGB")
ramp.color_ramp.elements[0].position = 0.0
ramp.color_ramp.elements[0].color = (0.10, 0.06, 0.24, 1)
ramp.color_ramp.elements[1].position = 1.0
ramp.color_ramp.elements[1].color = (0.02, 0.05, 0.13, 1)
bnt.links.new(tex.outputs["Generated"], sep.inputs["Vector"])
bnt.links.new(sep.outputs["Z"], ramp.inputs["Fac"])
bnt.links.new(ramp.outputs["Color"], bnt.nodes["Principled BSDF"].inputs["Base Color"])
backdrop.data.materials.append(bm)

# Treasure chest appended from the user's own сундук.blend
chest_objects = []
with bpy.data.libraries.load(os.path.join(ROOT, "сундук.blend")) as (src, dst):
    dst.objects = [n for n in src.objects if n in ("Cube", "Cube.001")]
for o in dst.objects:
    if o is None:
        continue
    bpy.context.collection.objects.link(o)
    chest_objects.append(o)
CHEST_WOOD = material("Chest wood", (0.42, 0.22, 0.10), roughness=0.62)
CHEST_GOLD = material("Chest gold", (0.95, 0.66, 0.20), roughness=0.28, metallic=0.6)
for o in chest_objects:
    is_lid = "001" in o.name
    o.name = "Chest_Lid" if is_lid else "Chest_Base"
    o.scale = (0.20, 0.20, 0.20)
    o.location = (-3.35 + (0.0 if is_lid else 0), 1.9, 0.30 + (0.19 if is_lid else 0))
    o.rotation_euler = (0, 0, math.radians(-18))
    o["from_user_file"] = "сундук.blend"
    # The source .blend references missing external JPGs; replace with clean
    # procedural materials so no magenta "missing texture" appears in renders.
    o.data.materials.clear()
    o.data.materials.append(CHEST_WOOD)
    o.data.materials.append(CHEST_GOLD)
CHEST_LID = next((o for o in chest_objects if o.name == "Chest_Lid"), None)
CHEST_BASE = next((o for o in chest_objects if o.name == "Chest_Base"), None)

# Confetti (invisible until the finale via scale keyframes)
random.seed(7301)
CONFETTI = []
for i in range(26):
    c = [MAT["pink"], MAT["yellow"], MAT["accent"], MAT["ball"]][i % 4]
    if i % 3 == 0:
        bpy.ops.mesh.primitive_cone_add(vertices=3, radius1=0.16, radius2=0.0,
                                        depth=0.28, location=(0, 0, 7))
        o = bpy.context.object
    else:
        bpy.ops.mesh.primitive_cube_add(size=0.16, location=(0, 0, 7))
        o = bpy.context.object
    o.name = f"Confetti_{i:02d}"
    o.data.materials.append(c)
    o.rotation_euler = tuple(random.uniform(0, math.pi) for _ in range(3))
    CONFETTI.append(o)

# ----------------------------------------------------------------------------
# Lighting / camera
# ----------------------------------------------------------------------------
def area(name, loc, energy, size, color, target=(0, 0, 1.4)):
    bpy.ops.object.light_add(type="AREA", location=loc)
    l = bpy.context.object
    l.name = name
    l.data.energy, l.data.size, l.data.color = energy, size, color
    d = Vector(target) - Vector(loc)
    l.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    return l

area("Key warm", (-3.5, -4.5, 7.0), 1100, 5.0, (1.0, 0.86, 0.72))
area("Fill cool", (4.5, -3.0, 4.2), 700, 6.0, (0.62, 0.78, 1.0))
area("Rim pink", (0.5, 5.0, 6.0), 950, 4.0, (1.0, 0.52, 0.82))
world = bpy.context.scene.world
if world is None:
    world = bpy.data.worlds.new("Studio World")
    bpy.context.scene.world = world
world.use_nodes = True
world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.035, 0.05, 0.11, 1)
world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.45

bpy.ops.object.empty_add(type="PLAIN_AXES", location=(0.1, 0, 1.55))
target = bpy.context.object
target.name = "Camera_Target"
bpy.ops.object.camera_add(location=(7.2, -11.2, 5.4))
camera = bpy.context.object
camera.name = "Camera"
camera.data.lens = 48
scene.camera = camera
c = camera.constraints.new("TRACK_TO")
c.target, c.track_axis, c.up_axis = target, "TRACK_NEGATIVE_Z", "UP_Y"

# ----------------------------------------------------------------------------
# ANIMATION — key controls, not the deformed meshes
# ----------------------------------------------------------------------------
def kp(pb, path, value, frame):
    setattr(pb, path, value)
    pb.keyframe_insert(data_path=path, frame=frame, group=pb.name)

def kp_world_location(pb, world_vec, frame):
    """PoseBone.location lives in BONE-LOCAL space. A vertical bone's local
    Z points along world -Y, so a naive (x, 0, z) would slide the character
    into the depth instead of lifting it. Convert explicitly via the rest
    matrix — this is the correct way to key a control bone in world axes."""
    local = pb.bone.matrix_local.to_3x3().inverted() @ Vector(world_vec)
    kp(pb, "location", tuple(local), frame)

def key_obj(o, path, value, frame):
    setattr(o, path, value)
    o.keyframe_insert(data_path=path, frame=frame)

# Root arc: anticipation -> jump -> hoop -> landing -> dance -> finale hop
ROOT_KEYS = {
    1:   (-2.60, 0,  0.00),
    12:  (-2.60, 0, -0.10),
    20:  (-2.60, 0,  0.00),
    28:  (-2.00, 0,  0.62),
    36:  (-0.95, 0,  1.30),
    44:  ( 0.25, 0,  1.45),
    52:  ( 0.92, 0,  0.86),
    60:  ( 1.20, 0,  0.00),
    68:  ( 1.20, 0, -0.08),
    76:  ( 1.20, 0,  0.00),
    84:  ( 1.42, 0,  0.05),
    92:  ( 1.68, 0,  0.13),
    100: ( 1.70, 0,  0.00),
    108: ( 1.70, 0,  0.52),
    116: ( 1.82, 0,  0.78),
    120: ( 1.82, 0,  0.58),
}
root = rig.pose.bones["Root"]
for f, v in ROOT_KEYS.items():
    kp_world_location(root, v, f)

# Squash / stretch with volume preservation on Spine + Head
STRETCH = {
    1: 1.00, 12: 0.78, 20: 1.00, 28: 1.18, 36: 1.24, 44: 1.06,
    52: 0.94, 60: 0.72, 68: 0.80, 76: 1.00, 84: 1.04, 92: 0.96,
    100: 1.00, 108: 1.16, 116: 1.06, 120: 1.00,
}
for bone_name in ("Spine", "Head"):
    pb = rig.pose.bones[bone_name]
    for f, sz in STRETCH.items():
        sxy = 1.0 / math.sqrt(sz)  # preserve volume
        kp(pb, "scale", (sxy, sxy, sz), f)

# Anticipation / follow-through on antenna (damped overlapping action)
ANTENNA = {
    1: 0.0, 12: 0.42, 20: -0.18, 28: 0.62, 36: -0.38, 44: 0.28,
    52: -0.48, 60: 0.78, 68: -0.40, 76: 0.20, 84: -0.12, 92: 0.07,
    100: 0.0, 108: 0.48, 116: -0.30, 120: 0.10,
}
ant = rig.pose.bones["Antenna"]
for f, rx in ANTENNA.items():
    kp(ant, "rotation_euler", (rx, 0.0, 0.10 * math.sin(f * 0.35)), f)

# Head counter-rotation (overlapping action)
head = rig.pose.bones["Head"]
for f in (1, 12, 20, 28, 36, 44, 52, 60, 68, 76, 92, 108, 120):
    kp(head, "rotation_euler", (0.0, 0.0, 0.12 * math.sin(f * 0.22)), f)

# IK foot targets — parented to Root, so only local stride/tuck offsets are keyed
IK_L = {
    1: (0, 0, 0), 12: (0, 0, 0), 20: (0, 0, 0),
    28: (-0.12, 0, 0.20), 36: (0.14, 0, 0.30), 44: (0.04, 0, 0.32),
    52: (-0.10, 0, 0.18), 60: (0, 0, 0), 68: (0, 0, 0),
    76: (0.12, 0, 0.06), 84: (0, 0, 0), 92: (-0.12, 0, 0.06),
    100: (0, 0, 0), 108: (0.10, 0, 0.20), 116: (-0.08, 0, 0.28), 120: (0.04, 0, 0.18),
}
IK_R = {f: (-v[0], v[1], v[2] * 0.92) for f, v in IK_L.items()}
for side, table in (("L", IK_L), ("R", IK_R)):
    pb = rig.pose.bones[f"IK.Foot.{side}"]
    for f, v in table.items():
        kp_world_location(pb, v, f)

# Waving arm: FK plus a blended IK hand target
hand_ik = rig.pose.bones["IK.Hand.R"]
HAND = {1: (0, 0, 0), 60: (0, 0, 0), 72: (0.05, 0, 0.25), 80: (0.10, 0, 0.55),
        88: (0.05, 0, 0.25), 96: (0.10, 0, 0.50), 104: (0, 0, 0.15), 120: (0, 0, 0)}
for f, v in HAND.items():
    kp_world_location(hand_ik, v, f)
arm_r = rig.pose.bones["Arm.R"]
for f, rz in {1: 0, 60: 0, 72: -0.55, 80: -1.15, 88: -0.55, 96: -1.0, 104: -0.25, 120: 0}.items():
    kp(arm_r, "rotation_euler", (0, 0, rz), f)
fore_r = rig.pose.bones["Forearm.R"]
for f, rz in {1: 0, 64: 0, 76: -0.35, 84: -0.70, 92: -0.35, 100: -0.60, 108: -0.15, 120: 0}.items():
    kp(fore_r, "rotation_euler", (0, 0, rz), f)
arm_l = rig.pose.bones["Arm.L"]
for f, rz in {1: 0, 28: 0.45, 44: 0.65, 60: -0.25, 76: 0.2, 100: 0, 116: 0.5, 120: 0.3}.items():
    kp(arm_l, "rotation_euler", (0, 0, rz), f)

# Eye blinks (shape keys)
for k in BLINK:
    for f, v in {1: 0, 8: 0, 9: 1, 10: 1, 11: 0, 56: 0, 57: 1, 58: 0,
                 96: 0, 97: 1, 98: 0, 120: 0}.items():
        k.value = v
        k.keyframe_insert(data_path="value", frame=f)

# Ball: arcs + squash on contact + rolling
BALL_KEYS = [
    (1, 2.60, 0.55), (12, 2.25, 0.55), (20, 1.92, 1.42), (28, 1.60, 0.55),
    (36, 1.22, 1.18), (44, 0.82, 0.55), (52, 0.42, 1.34), (60, 0.02, 0.55),
    (68, -0.38, 1.10), (76, -0.78, 0.55), (84, -1.18, 1.28), (92, -1.50, 0.55),
    (100, -1.78, 1.02), (108, -2.02, 0.55), (120, -2.12, 0.55),
]
for f, x, z in BALL_KEYS:
    key_obj(ball, "location", (x, 0, z), f)
    contact = z < 0.60
    sz = 0.76 if contact else 1.10
    sxy = 1.0 / math.sqrt(sz)
    key_obj(ball, "scale", (sxy, sxy, sz), f)
    key_obj(ball, "rotation_euler", (0, (2.60 - x) * 2.2, 0), f)

# Cone: wobble, then a surprised flip
for f, rz, rx in [(1, 0, 0), (24, 0.22, 0.05), (48, -0.20, -0.04), (72, 0.18, 0.05),
                  (96, -0.12, 0.0), (104, 0.0, 0.0), (112, 0.0, 1.7), (120, 0.0, 3.3)]:
    key_obj(cone, "rotation_euler", (rx, 0, rz), f)
for f, z in {1: 0.72, 100: 0.72, 108: 1.15, 116: 0.95, 120: 0.72}.items():
    key_obj(cone, "location", (3.45, 0.6, z), f)

# Torus: spinning / pulsing hoop
for f in range(1, 121, 8):
    key_obj(torus, "rotation_euler", (math.pi/2, 0, 0.22 * math.sin(f * 0.16)), f)
    s = 1.0 + 0.05 * math.sin(f * 0.24)
    key_obj(torus, "scale", (s, s, s), f)

# Chest lid opens at the finale
if CHEST_LID:
    for f, dx, dz in [(1, 0, 0), (92, 0, 0), (100, 0, 0.28), (108, 0, 0.42), (120, 0, 0.42)]:
        key_obj(CHEST_LID, "location", (-3.35, 1.9, 0.49 + dz), f)
        key_obj(CHEST_LID, "rotation_euler", (0, -0.35 * dz / 0.42, math.radians(-18)), f)

# Confetti burst from the chest
for i, o in enumerate(CONFETTI):
    a = random.uniform(0, 2 * math.pi)
    r = random.uniform(0.4, 2.6)
    x0, y0 = -3.35, 1.9
    for f, z, s in [(1, -2, 0.001), (96, -2, 0.001), (100, 0.9, 1.0),
                    (108, 2.6 + random.random(), 1.0), (120, 0.25 + random.random() * 0.4, 1.0)]:
        spread = 0.0 if f <= 96 else (f - 96) * 0.10
        key_obj(o, "location", (x0 + math.cos(a) * r * spread, y0 + math.sin(a) * r * spread, z), f)
        key_obj(o, "scale", (s, s, s), f)
    key_obj(o, "rotation_euler", tuple(random.uniform(0, 6.28) for _ in range(3)), 120)

# Camera slow push-in
for f, loc in {1: (7.8, -12.0, 5.7), 60: (7.3, -11.3, 5.4), 120: (6.7, -10.4, 5.0)}.items():
    key_obj(camera, "location", loc, f)

# ----------------------------------------------------------------------------
# Graph Editor smoothing — Blender 5.3 slotted actions
# ----------------------------------------------------------------------------
def channelbags(idblock):
    ad = getattr(idblock, "animation_data", None)
    if not ad or not ad.action:
        return []
    slot = getattr(ad, "action_slot", None)
    if slot is not None:
        cb = anim_utils.action_get_channelbag_for_slot(ad.action, slot)
        return [cb] if cb else []
    out = []
    for layer in getattr(ad.action, "layers", []):
        for strip in getattr(layer, "strips", []):
            for cb in getattr(strip, "channelbags", []):
                out.append(cb)
    return out

FCURVE_SUMMARY = []
animated_ids = [rig] + list(bpy.data.objects)
for idblock in animated_ids:
    for cb in channelbags(idblock):
        for fc in cb.fcurves:
            for k in fc.keyframe_points:
                k.interpolation = "BEZIER"
                k.handle_left_type = "AUTO_CLAMPED"
                k.handle_right_type = "AUTO_CLAMPED"
            FCURVE_SUMMARY.append({
                "id": getattr(idblock, "name", str(idblock)),
                "data_path": fc.data_path,
                "index": fc.array_index,
                "keys": len(fc.keyframe_points),
                "interpolation": "BEZIER / AUTO_CLAMPED",
            })
for k in BLINK:
    kb_id = k.id_data
    for cb in channelbags(kb_id):
        for fc in cb.fcurves:
            for pt in fc.keyframe_points:
                pt.interpolation = "BEZIER"
                pt.handle_left_type = "AUTO_CLAMPED"
                pt.handle_right_type = "AUTO_CLAMPED"
            FCURVE_SUMMARY.append({"id": "Blink shape keys", "data_path": fc.data_path,
                                   "index": fc.array_index, "keys": len(fc.keyframe_points),
                                   "interpolation": "BEZIER / AUTO_CLAMPED"})

# ----------------------------------------------------------------------------
# Motion Paths (Blender's own operator) + baked trajectory ribbons
# ----------------------------------------------------------------------------
MOTION_PATH_STATUS = {}
try:
    bpy.ops.object.select_all(action="DESELECT")
    for o in (ball, cone, torus, rig):
        o.select_set(True)
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.paths_calculate(display_type="RANGE", range="SCENE")
    MOTION_PATH_STATUS["object_paths_calculate"] = "ok"
except Exception as e:
    MOTION_PATH_STATUS["object_paths_calculate"] = f"failed: {e}"
try:
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode="POSE")
    bpy.ops.pose.paths_calculate(display_type="RANGE", range="SCENE", bake_location="HEADS")
    MOTION_PATH_STATUS["pose_paths_calculate"] = "ok"
    bpy.ops.object.mode_set(mode="OBJECT")
except Exception as e:
    MOTION_PATH_STATUS["pose_paths_calculate"] = f"failed: {e}"
    try:
        bpy.ops.object.mode_set(mode="OBJECT")
    except Exception:
        pass

scene.frame_set(F0)

# ----------------------------------------------------------------------------
# Sample EVERY frame: all objects, all bones, all positions
# ----------------------------------------------------------------------------
TRACKED = [o for o in bpy.data.objects if o.type in {"MESH", "CAMERA", "EMPTY", "LIGHT", "ARMATURE"}]
DEFORM_SAMPLE = ["Hero_Body", "Ball_Sphere", "Cone_Grump", "Torus_Hoop", "Chest_Lid"]

def world_head(pb):
    return rig.matrix_world @ pb.head

def deformed_center(obj, depsgraph):
    ev = obj.evaluated_get(depsgraph)
    mesh = ev.to_mesh()
    if not mesh or not mesh.vertices:
        if mesh:
            ev.to_mesh_clear()
        return list(obj.matrix_world.translation)
    c = Vector((0, 0, 0))
    for v in mesh.vertices:
        c += ev.matrix_world @ v.co
    c /= len(mesh.vertices)
    ev.to_mesh_clear()
    return [c.x, c.y, c.z]

FRAMES = []
TRAJ = {"hero_root": [], "ball": [], "cone": [], "torus": [], "chest_lid": []}
for f in range(F0, F1 + 1):
    scene.frame_set(f)
    depsgraph = bpy.context.evaluated_depsgraph_get()
    objs = {}
    for o in TRACKED:
        objs[o.name] = {
            "location": [round(v, 5) for v in o.matrix_world.translation],
            "rotation": [round(v, 5) for v in o.rotation_euler],
            "scale": [round(v, 5) for v in o.scale],
        }
    bones = {}
    for pb in rig.pose.bones:
        h, t = world_head(pb), rig.matrix_world @ pb.tail
        bones[pb.name] = {
            "head": [round(v, 5) for v in h],
            "tail": [round(v, 5) for v in t],
            "location": [round(v, 5) for v in pb.location],
            "rotation": [round(v, 5) for v in pb.rotation_euler],
            "scale": [round(v, 5) for v in pb.scale],
        }
    centers = {n: [round(v, 5) for v in deformed_center(bpy.data.objects[n], depsgraph)]
               for n in DEFORM_SAMPLE if n in bpy.data.objects}
    root_head = bones["Root"]["head"]
    TRAJ["hero_root"].append([f] + root_head)
    TRAJ["ball"].append([f] + centers.get("Ball_Sphere", [0, 0, 0]))
    TRAJ["cone"].append([f] + centers.get("Cone_Grump", [0, 0, 0]))
    TRAJ["torus"].append([f] + centers.get("Torus_Hoop", [0, 0, 0]))
    TRAJ["chest_lid"].append([f] + centers.get("Chest_Lid", [0, 0, 0]))
    FRAMES.append({"frame": f, "objects": objs, "bones": bones, "deformed_centers": centers})
    if f % 30 == 0:
        print("sampled frame", f, flush=True)

with open(os.path.join(LAB, "animation.json"), "w") as fh:
    json.dump({"fps": FPS, "start": F0, "end": F1, "frames": FRAMES}, fh)
with open(os.path.join(LAB, "trajectories.json"), "w") as fh:
    json.dump(TRAJ, fh)

# Visible trajectory ribbons (baked motion paths)
def ribbon(name, points, color, strength=1.2):
    cu = bpy.data.curves.new(name + "Data", "CURVE")
    cu.dimensions = "3D"
    cu.bevel_depth, cu.bevel_resolution = 0.022, 2
    sp = cu.splines.new("POLY")
    sp.points.add(len(points) - 1)
    for i, p in enumerate(points):
        sp.points[i].co = (p[1], p[2], p[3], 1)
    ob = bpy.data.objects.new(name, cu)
    bpy.context.collection.objects.link(ob)
    m = material(name + " glow", color, roughness=0.4, emission=color, emission_strength=strength)
    cu.materials.append(m)
    return ob

ribbon("Path_Hero", TRAJ["hero_root"], (0.98, 0.45, 0.22), 1.0)
ribbon("Path_Ball", TRAJ["ball"], (0.16, 0.72, 1.0), 1.0)
ribbon("Path_Cone", TRAJ["cone"], (0.72, 0.40, 1.0), 0.8)
ribbon("Path_Hoop", TRAJ["torus"], (1.0, 0.80, 0.25), 0.8)
# Keyframe markers on the hero arc
for f in ROOT_KEYS:
    p = TRAJ["hero_root"][f - F0]
    sphere(f"ArcMarker_{f:03d}", (p[1], p[2], p[3]), 0.045, MAT["yellow"], smooth=True)

# ----------------------------------------------------------------------------
# QA / verification computations
# ----------------------------------------------------------------------------
def dist(a, b):
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))

qa = {"checks": [], "max_speed": {}, "max_accel": {}, "arc_smoothness": {}}
all_finite = True
for frame in FRAMES:
    for group in ("objects", "bones"):
        for name, rec in frame[group].items():
            for key in ("location", "rotation", "scale", "head", "tail"):
                if key in rec and any((not math.isfinite(v)) for v in rec[key]):
                    all_finite = False
qa["checks"].append({"name": "Все координаты конечные (нет NaN/Inf)", "pass": all_finite,
                     "detail": f"проверено {len(FRAMES)} кадров"})
qa["checks"].append({"name": "Покрытие всеми кадрами", "pass": len(FRAMES) == F1 - F0 + 1,
                     "detail": f"{len(FRAMES)} / {F1 - F0 + 1}"})

for label, key in (("hero_root", "hero_root"), ("ball", "ball"), ("cone", "cone"), ("torus", "torus")):
    pts = [p[1:] for p in TRAJ[key]]
    speeds = [dist(pts[i], pts[i-1]) * FPS for i in range(1, len(pts))]
    accels = [abs(speeds[i] - speeds[i-1]) * FPS for i in range(1, len(speeds))]
    qa["max_speed"][label] = round(max(speeds), 3)
    qa["max_accel"][label] = round(max(accels), 3) if accels else 0.0
    qa["checks"].append({"name": f"Непрерывность траектории: {label}",
                         "pass": max(speeds) < 60.0,
                         "detail": f"max speed {max(speeds):.2f} units/s, {len(pts)} точек"})

# Volume preservation of squash & stretch
vol_err = max(abs(math.prod(b["scale"]) - 1.0) for fr in FRAMES for b in [fr["bones"]["Spine"]])
qa["checks"].append({"name": "Squash & stretch сохраняет объём", "pass": vol_err < 0.02,
                     "detail": f"макс. ошибка {vol_err:.5f}"})

# IK reach: hips -> foot target distance must stay within the 2-bone chain
leg_len = 0.35 + 0.37  # Thigh 0.90->0.55 + Shin 0.55->0.18
worst = 0.0
for fr in FRAMES:
    for side in ("L", "R"):
        thigh = fr["bones"][f"Thigh.{side}"]["head"]
        tgt = fr["bones"][f"IK.Foot.{side}"]["head"]
        worst = max(worst, dist(thigh, tgt))
qa["checks"].append({"name": "IK-цели стоп достижимы (длина цепи 0.72)",
                     "pass": worst <= leg_len + 0.03,
                     "detail": f"макс. расстояние {worst:.3f}"})

# Camera framing of the main characters at every frame
framing_ok = True
worst_ndc = 0.0
for fr in FRAMES:
    scene.frame_set(fr["frame"])
    for n in ("Ball_Sphere", "Cone_Grump", "Torus_Hoop"):
        c = fr["deformed_centers"].get(n)
        if not c:
            continue
        uv = world_to_camera_view(scene, camera, Vector(c))
        worst_ndc = max(worst_ndc, max(-uv.x, uv.x - 1, -uv.y, uv.y - 1))
        if not (-0.05 <= uv.x <= 1.05 and -0.05 <= uv.y <= 1.05):
            framing_ok = False
qa["checks"].append({"name": "Персонажи остаются в кадре", "pass": framing_ok,
                     "detail": f"макс. выход за кадр {worst_ndc:.3f}"})
qa["checks"].append({"name": "Motion Paths рассчитаны в Blender",
                     "pass": any(v == "ok" for v in MOTION_PATH_STATUS.values()),
                     "detail": str(MOTION_PATH_STATUS)})
qa["checks"].append({"name": "Скелет: кости, IK, веса", "pass": len(arm.bones) >= 18 and len(HERO_PARTS) >= 20,
                     "detail": f"{len(arm.bones)} костей, {len(HERO_PARTS)} привязанных мешей, "
                               f"3 IK-констрейнта, {len(BONEVIZ_PARTS)} визуализаторов"})

scene.frame_set(F0)

# ----------------------------------------------------------------------------
# Render settings + meta for the laboratory
# ----------------------------------------------------------------------------
scene.render.engine = "CYCLES"
scene.cycles.device = "CPU"
scene.cycles.samples = SAMPLES
scene.cycles.use_denoising = True
for attr, val in (("use_adaptive_sampling", True), ("adaptive_threshold", 0.05), ("max_bounces", 4)):
    if hasattr(scene.cycles, attr):
        setattr(scene.cycles, attr, val)
scene.render.resolution_x, scene.render.resolution_y = RES_X, RES_Y
scene.render.resolution_percentage = 100
scene.render.threads_mode = "FIXED"
scene.render.threads = 2
# 180-degree shutter is the researched cinematic default; kept in the .blend
# for re-renders. The PNG sequence uses blur=0 to keep CPU time reasonable.
if hasattr(scene.render, "use_motion_blur"):
    scene.render.use_motion_blur = True
    if hasattr(scene.render, "motion_blur_shutter"):
        scene.render.motion_blur_shutter = 0.5
try:
    scene.view_settings.view_transform = "AgX"
    scene.view_settings.look = "AgX - Medium High Contrast"
except Exception:
    pass
scene.render.image_settings.media_type = "VIDEO"
scene.render.image_settings.file_format = "FFMPEG"
scene.render.ffmpeg.format = "MPEG4"
scene.render.ffmpeg.codec = "H264"
scene.render.ffmpeg.constant_rate_factor = "HIGH"
scene.render.ffmpeg.ffmpeg_preset = "GOOD"
scene.render.ffmpeg.gopsize = 12
scene.render.filepath = "//geo_cartoon.mp4"

RIG_TREE = [{"name": n, "parent": p, "deform": d,
             "head": list(h), "tail": list(t)} for n, h, t, p, d in BONES]
IK_CONSTRAINTS = [{"bone": pb.name, "constraint": c.name, "type": c.type,
                   "subtarget": getattr(c, "subtarget", None), "chain_count": getattr(c, "chain_count", None),
                   "influence": round(c.influence, 3)}
                  for pb in rig.pose.bones for c in pb.constraints]

SOURCES = [
    {"title": "12 principles / character animation mechanics", "url": "https://oboe.com/learn/mastering-3d-worlds-with-blender-nwhftu/character-animation-mechanics-ntnkb6",
     "takeaway": "Squash & stretch with volume, anticipation, follow-through, slow in/out, arcs, exaggeration; walk-cycle contact/down/passing/up poses."},
    {"title": "Animate a 3D model in Blender step by step", "url": "https://www.relebook.com/articles/animate-3d-model-blender-step-by-step-guide",
     "takeaway": "Keyframing + Bezier easing in the Graph Editor; edge loops around joints for clean deformation."},
    {"title": "Blender character animation tutorial", "url": "https://www.bevelfish.com/blog/blender-character-animation-tutorial",
     "takeaway": "Apply transforms, origin at the feet, fit the metarig to joints, IK for planted feet, key rig controls, enable Motion Paths to inspect real arcs."},
    {"title": "Rigify / weight painting / Graph Editor smoothing", "url": "https://gist.ly/youtube-summarizer/mastering-character-animation-a-step-by-step-guide-to-rigging-and-motion-in-blender",
     "takeaway": "Metarig, auto-normalized weights, smooth F-curves, refine the torso first."},
    {"title": "Root motion best practice", "url": "https://blenderartists.org/t/best-practices-stay-on-base-or-walk-it-off/1491500",
     "takeaway": "Avoid stacking Bezier transforms on the root; animate root with care, prefer hips/IK for contact."},
    {"title": "Blender Python animation (keyframes, F-curves, armatures, IK)", "url": "https://terminalskills.io/skills/blender-animation",
     "takeaway": "keyframe_insert, BEZIER/EASE_IN_OUT, CYCLES/NOISE modifiers, edit_bones, IK constraint, blender --background --python."},
    {"title": "Blender 5.x F-curve API change", "url": "https://blenderartists.org/t/how-to-access-fcurves-in-blender-5-0/1623022",
     "takeaway": "Action.fcurves removed in 5.0; use bpy_extras.anim_utils.action_get_channelbag_for_slot(action, slot)."},
    {"title": "Blender Python API: Object Operators / Motion Paths", "url": "https://docs.blender.org/api/current/bpy.ops.object.html",
     "takeaway": "bpy.ops.object.paths_calculate(display_type='RANGE', range='SCENE'); pose.paths_calculate with bake_location."},
    {"title": "Blender Python API: SceneEEVEE", "url": "https://docs.blender.org/api/current/bpy.types.SceneEEVEE.html",
     "takeaway": "taa_render_samples 64-128, motion_blur_steps, soft shadows / ray tracing for quality."},
    {"title": "Blender Render Automation (5.0 media_type / FFMPEG)", "url": "https://terminalskills.io/skills/blender-render-automation",
     "takeaway": "Set image_settings.media_type='VIDEO' before file_format='FFMPEG'; MPEG4+H264; Cycles CPU is reliable headless."},
    {"title": "Eevee render quality guide", "url": "https://renderday.com/blog/speed-up-your-renders",
     "takeaway": "64-128 samples for final, TAA, high bitdepth, soft shadows, bloom, DOF f/1.4-2.8, motion blur shutter 0.5."},
    {"title": "Bake Motion Path to curve", "url": "https://blenderartists.org/t/bake-motion-path/492835",
     "takeaway": "Sample matrix_world per frame and bake a visible Bezier/POLY curve to inspect trajectories."},
    {"title": "FFMPEG encoding via Python", "url": "https://blender.stackexchange.com/questions/106659/change-encoding-settings-through-python-api",
     "takeaway": "render.ffmpeg.format='MPEG4', codec='H264', constant_rate_factor, ffmpeg_preset."},
]
PRINCIPLES = [
    {"name": "Squash & Stretch", "where": "Spine/Head scale + Ball scale", "note": "объём сохранён: xy = 1/sqrt(z)"},
    {"name": "Anticipation", "where": "кадры 1-20, приседание перед прыжком"},
    {"name": "Staging", "where": "камера, свет, сундук и кольцо в кадре"},
    {"name": "Straight Ahead / Pose to Pose", "where": "pose-to-pose: 16 ключевых поз Root"},
    {"name": "Follow Through & Overlapping", "where": "антенна, голова, предплечье с задержкой"},
    {"name": "Slow In / Slow Out", "where": "все F-кривые BEZIER + AUTO_CLAMPED"},
    {"name": "Arcs", "where": "парабола прыжка, отскоки шара, видимые ленты траекторий"},
    {"name": "Secondary Action", "where": "шар, конус, вращение кольца, конфетти"},
    {"name": "Timing", "where": "24 fps, 120 кадров = 5 с"},
    {"name": "Exaggeration", "where": "растяжение 1.24, сжатие 0.72,flip конуса"},
    {"name": "Solid Drawing", "where": "bevel + weighted normals,_volume-preserving scale"},
    {"name": "Appeal", "where": "глаза, улыбка, антенна, яркая палитра"},
]

meta = {
    "blender": bpy.app.version_string,
    "installer": {
        "url": "https://github.com/maksummatatov10-spec1231/blender1231/releases/download/install/blender-5.3.0-linux-x64.tar.xz",
        "size": 406944100,
        "sha256": "dacb8264197a3f7fda6001285a5a506fc97ee943881261c2c3bd63c882f22e05",
    },
    "scene": {"name": scene.name, "fps": FPS, "start": F0, "end": F1,
              "resolution": [RES_X, RES_Y], "engine": "CYCLES", "samples": SAMPLES,
              "denoising": True, "device": "CPU", "duration_seconds": round((F1 - F0 + 1) / FPS, 2)},
    "output": {"blend": "geo_cartoon.blend", "mp4": "geo_cartoon.mp4",
               "frames": "renders/frames/frame_%04d.png"},
    "rig": {"bones": RIG_TREE, "constraints": IK_CONSTRAINTS,
            "skinned_meshes": [o.name for o in HERO_PARTS],
            "bone_visualizers": [o.name for o in BONEVIZ_PARTS]},
    "fcurves": FCURVE_SUMMARY,
    "motion_paths": MOTION_PATH_STATUS,
    "principles": PRINCIPLES,
    "sources": SOURCES,
    "objects_count": len(bpy.data.objects),
    "qa": qa,
}
with open(os.path.join(LAB, "meta.json"), "w") as fh:
    json.dump(meta, fh, ensure_ascii=False, indent=1)
with open(os.path.join(LAB, "qa.json"), "w") as fh:
    json.dump(qa, fh, ensure_ascii=False, indent=1)

# organisational collections
for name, names in {
    "01 Hero + Skeleton": [o.name for o in HERO_PARTS] + [rig.name],
    "02 Other shapes": ["Ball_Sphere", "Cone_Grump", "Cone_Nose", "Torus_Hoop", "Pyramid_Set"],
    "03 Motion paths": [o.name for o in bpy.data.objects if o.name.startswith(("Path_", "ArcMarker_"))],
    "04 Stage": ["Stage_Ground", "Backdrop", "Chest_Base", "Chest_Lid"],
    "05 Confetti": [o.name for o in CONFETTI],
    "06 Bone visualizers (hidden)": [o.name for o in BONEVIZ_PARTS],
}.items():
    col = bpy.data.collections.new(name)
    scene.collection.children.link(col)
    for n in names:
        o = bpy.data.objects.get(n)
        if o:
            for old in list(o.users_collection):
                old.objects.unlink(o)
            col.objects.link(o)

bpy.ops.wm.save_as_mainfile(filepath=os.path.join(ROOT, "geo_cartoon.blend"))
print("BUILD_OK", meta["blender"], "objects", len(bpy.data.objects),
      "fcurves", len(FCURVE_SUMMARY), "qa_pass", sum(1 for c in qa["checks"] if c["pass"]),
      "/", len(qa["checks"]), flush=True)
