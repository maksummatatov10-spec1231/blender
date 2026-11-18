"""
GEO STORY v2 — "Красный идёт в гости к Синему"
Blender 5.3.0, Cycles CPU, fully procedural (no missing textures).

Story beats (240 frames / 24 fps / 10 s, 5 camera shots):
  1-88   Red robot leaves his warm brick house, forgets the door open,
         walks along the stone path THROUGH a correctly-oriented garden arch.
  89-128 Blue robot (different face, different tower house) spots him
         through the window, reacts, hurries to the door.
  129-168 Red knocks, Blue opens the door.
  169-204 Red enters, Blue offers the gift box.
  205-240 Lid pops, ribbons/confetti burst, both celebrate.

Quality recipe: applied transforms for skinned meshes, fitted armature with IK,
volume-preserving squash/stretch, anticipation, follow-through, arcs,
BEZIER easing, Motion Paths, camera cuts via timeline markers, procedural
Brick/Noise/Voronoi/Wave textures with bump, bevels + weighted normals,
soft area lights, AgX, Cycles denoising.
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

FPS, F0, F1 = 24, 1, 240
RES_X, RES_Y = 960, 540
SAMPLES = 20                     # .blend default (final PNG sequence uses 14)
random.seed(20261117)

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.name = "GEO STORY v2"
scene.frame_start, scene.frame_end = F0, F1
scene.render.fps = FPS

# ---------------------------------------------------------------------------
# Materials — 100% procedural (no external images can go missing)
# ---------------------------------------------------------------------------
def base_material(name, color, roughness=0.4, metallic=0.0, emission=None, strength=0.0):
    m = bpy.data.materials.new(name)
    m.diffuse_color = (*color, 1)
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes.get("Principled BSDF")
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Roughness"].default_value = roughness
    b.inputs["Metallic"].default_value = metallic
    if emission:
        b.inputs["Emission Color"].default_value = (*emission, 1)
        b.inputs["Emission Strength"].default_value = strength
    return m

def textured(name, colA, colB, kind="noise", scale=6.0, bump=0.12,
             roughness=0.5, metallic=0.0, detail=3.0):
    """Procedural texture + colour ramp + bump, driven by Generated/Object coords."""
    m = base_material(name, colA, roughness, metallic)
    nt = m.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    tc = nt.nodes.new("ShaderNodeTexCoord")
    mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (scale, scale, scale)
    nt.links.new(tc.outputs["Generated"], mp.inputs["Vector"])
    if kind == "brick":
        tex = nt.nodes.new("ShaderNodeTexBrick")
        tex.inputs["Color1"].default_value = (*colA, 1)
        tex.inputs["Color2"].default_value = (*colB, 1)
        tex.inputs["Mortar"].default_value = (0.08, 0.06, 0.07, 1)
        tex.inputs["Scale"].default_value = scale
        tex.inputs["Mortar Size"].default_value = 0.022
        tex.inputs["Mortar Smooth"].default_value = 0.02
        fac = tex.outputs["Color"]
        bump_src = tex.outputs["Fac"]
    elif kind == "wood":
        tex = nt.nodes.new("ShaderNodeTexWave")
        tex.wave_type = "BANDS"
        tex.bands_direction = "X"
        tex.inputs["Scale"].default_value = scale
        tex.inputs["Distortion"].default_value = 4.0
        tex.inputs["Detail Scale"].default_value = 2.0
        ramp = nt.nodes.new("ShaderNodeValToRGB")
        ramp.color_ramp.elements[0].color = (*colA, 1)
        ramp.color_ramp.elements[1].color = (*colB, 1)
        nt.links.new(tex.outputs["Color"], ramp.inputs["Fac"])
        fac = ramp.outputs["Color"]
        bump_src = tex.outputs["Fac"]
    elif kind == "voronoi":
        tex = nt.nodes.new("ShaderNodeTexVoronoi")
        tex.inputs["Scale"].default_value = scale
        ramp = nt.nodes.new("ShaderNodeValToRGB")
        ramp.color_ramp.elements[0].color = (*colA, 1)
        ramp.color_ramp.elements[1].color = (*colB, 1)
        nt.links.new(tex.outputs["Distance"], ramp.inputs["Fac"])
        fac = ramp.outputs["Color"]
        bump_src = tex.outputs["Distance"]
    else:  # noise
        tex = nt.nodes.new("ShaderNodeTexNoise")
        tex.inputs["Scale"].default_value = scale
        tex.inputs["Detail"].default_value = detail
        tex.inputs["Roughness"].default_value = 0.65
        ramp = nt.nodes.new("ShaderNodeValToRGB")
        ramp.color_ramp.elements[0].color = (*colA, 1)
        ramp.color_ramp.elements[1].color = (*colB, 1)
        nt.links.new(tex.outputs["Fac"], ramp.inputs["Fac"])
        fac = ramp.outputs["Color"]
        bump_src = tex.outputs["Fac"]
    nt.links.new(mp.outputs["Vector"], tex.inputs["Vector"])
    nt.links.new(fac, bsdf.inputs["Base Color"])
    if bump > 0:
        bn = nt.nodes.new("ShaderNodeBump")
        bn.inputs["Strength"].default_value = bump
        bn.inputs["Distance"].default_value = 0.035
        nt.links.new(bump_src, bn.inputs["Height"])
        nt.links.new(bn.outputs["Normal"], bsdf.inputs["Normal"])
    return m

M = {
    "red_body":   base_material("Red enamel", (0.86, 0.10, 0.09), 0.26, 0.35),
    "red_light":  base_material("Red cream", (1.0, 0.80, 0.68), 0.34),
    "red_dark":   base_material("Red joints", (0.16, 0.10, 0.14), 0.45, 0.5),
    "blue_body":  base_material("Blue enamel", (0.07, 0.32, 0.86), 0.22, 0.45),
    "blue_light": base_material("Blue ice", (0.62, 0.88, 1.0), 0.28, 0.2),
    "blue_dark":  base_material("Blue joints", (0.05, 0.10, 0.24), 0.4, 0.6),
    "white":      base_material("Eye white", (0.99, 0.99, 0.97), 0.18),
    "ink":        base_material("Ink", (0.03, 0.04, 0.09), 0.5),
    "glow_cyan":  base_material("Glow cyan", (0.20, 1.0, 0.95), 0.3,
                                emission=(0.2, 1.0, 0.95), strength=2.2),
    "glow_warm":  base_material("Warm window", (1.0, 0.72, 0.32), 0.3,
                                emission=(1.0, 0.62, 0.22), strength=1.5),
    "glow_red":   base_material("Red heart LED", (1.0, 0.25, 0.2), 0.3,
                                emission=(1.0, 0.15, 0.12), strength=2.0),
    "gold":       base_material("Brass", (0.95, 0.68, 0.22), 0.24, 0.75),
    "brick":      textured("Red brick", (0.55, 0.16, 0.11), (0.86, 0.35, 0.20),
                           "brick", 4.0, 0.30, 0.78),
    "roof_red":   textured("Terracotta tile", (0.62, 0.17, 0.10), (0.93, 0.42, 0.19),
                           "brick", 9.0, 0.22, 0.7),
    "wood":       textured("Oak door", (0.28, 0.12, 0.05), (0.66, 0.34, 0.12),
                           "wood", 7.0, 0.18, 0.62),
    "blue_wall":  textured("Blue panels", (0.06, 0.24, 0.52), (0.20, 0.58, 0.86),
                           "noise", 5.0, 0.10, 0.38, 0.35),
    "blue_roof":  textured("Slate dome", (0.10, 0.16, 0.34), (0.34, 0.48, 0.72),
                           "noise", 8.0, 0.16, 0.32, 0.5),
    "grass":      textured("Grass", (0.13, 0.34, 0.14), (0.32, 0.62, 0.24),
                           "noise", 22.0, 0.20, 0.9),
    "stone":      textured("Path stone", (0.48, 0.44, 0.42), (0.78, 0.74, 0.68),
                           "voronoi", 7.0, 0.28, 0.85),
    "soil":       textured("Soil", (0.20, 0.13, 0.10), (0.36, 0.24, 0.16),
                           "noise", 10.0, 0.15, 0.95),
    "bark":       textured("Bark", (0.22, 0.13, 0.08), (0.45, 0.29, 0.16),
                           "wood", 5.0, 0.25, 0.9),
    "leaf":       textured("Leaves", (0.10, 0.36, 0.16), (0.30, 0.72, 0.28),
                           "noise", 9.0, 0.15, 0.85),
    "gift":       textured("Gift wrap", (0.85, 0.14, 0.42), (1.0, 0.42, 0.68),
                           "noise", 7.0, 0.08, 0.42),
    "ribbon":     base_material("Ribbon gold", (1.0, 0.82, 0.25), 0.3, 0.3,
                                emission=(1.0, 0.7, 0.2), strength=0.4),
}
STREAMER_COLS = [
    base_material("Streamer pink", (1.0, 0.30, 0.62), 0.35, emission=(1.0, 0.3, 0.62), strength=0.8),
    base_material("Streamer cyan", (0.20, 0.92, 1.0), 0.35, emission=(0.2, 0.92, 1.0), strength=0.8),
    base_material("Streamer gold", (1.0, 0.82, 0.24), 0.35, emission=(1.0, 0.82, 0.24), strength=0.8),
    base_material("Streamer mint", (0.36, 1.0, 0.66), 0.35, emission=(0.36, 1.0, 0.66), strength=0.8),
    base_material("Streamer violet", (0.66, 0.40, 1.0), 0.35, emission=(0.66, 0.40, 1.0), strength=0.8),
]

# ---------------------------------------------------------------------------
# Geometry helpers
# ---------------------------------------------------------------------------
SKINNED = []
BONEVIZ = []

def finish(o, name, mat, bone=None, bevel=0.0, smooth=False, viz=False):
    o.name = name
    bpy.ops.object.select_all(action="DESELECT")
    o.select_set(True)
    bpy.context.view_layer.objects.active = o
    if bone is not None or viz:            # bake rest coords for the Armature modifier
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    if mat:
        o.data.materials.append(mat)
    if smooth:
        for p in o.data.polygons:
            p.use_smooth = True
    if bevel:
        b = o.modifiers.new("Bevel", "BEVEL")
        b.width, b.segments, b.limit_method = bevel, 4, "ANGLE"
        b.angle_limit = 0.4
        o.modifiers.new("WeightedNormal", "WEIGHTED_NORMAL")
    if bone:
        rig = BONE_RIG[0]
        vg = o.vertex_groups.new(name=bone)
        vg.add([v.index for v in o.data.vertices], 1.0, "REPLACE")
        am = o.modifiers.new("Armature", "ARMATURE")
        am.object = rig
        am.use_vertex_groups = True
        am.use_bone_envelopes = False
        SKINNED.append(o)
    if viz:
        o.hide_render = True
        BONEVIZ.append(o)
    return o

BONE_RIG = [None]

def cube(name, loc, dims, mat, bone=None, bevel=0.05, viz=False):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    o = bpy.context.object
    o.scale = dims
    return finish(o, name, mat, bone, bevel, viz=viz)

def sphere(name, loc, radius, mat, bone=None, scale=None, segments=24, viz=False):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=segments, ring_count=16,
                                         radius=radius, location=loc)
    o = bpy.context.object
    if scale:
        o.scale = scale
    return finish(o, name, mat, bone, 0, True, viz=viz)

def cylinder(name, a, b, radius, mat, bone=None, verts=20, viz=False):
    a, b = Vector(a), Vector(b)
    d = b - a
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=radius,
                                        depth=d.length, location=(a+b)/2)
    o = bpy.context.object
    o.rotation_euler = d.to_track_quat("Z", "Y").to_euler()
    return finish(o, name, mat, bone, 0.02, True, viz=viz)

def cone(name, loc, r1, r2, depth, mat, verts=24, rotation=(0,0,0), bone=None, bevel=0.03):
    bpy.ops.mesh.primitive_cone_add(vertices=verts, radius1=r1, radius2=r2,
                                    depth=depth, location=loc, rotation=rotation)
    return finish(bpy.context.object, name, mat, bone, bevel)

def shape_key(obj, name, center, fn):
    """Shape key relative to a mesh-space centre (skinned meshes have their
    rest WORLD coordinates baked into the vertices, so absolute scaling of
    v.co would fling the face across the scene)."""
    obj.shape_key_add(name="Basis")
    k = obj.shape_key_add(name=name)
    c = Vector(center)
    for v in k.data:
        d = v.co - c
        v.co = c + fn(d)
    return k

# ---------------------------------------------------------------------------
# ROBOT — two different designs, same expressive bone layout
# ---------------------------------------------------------------------------
BONES = [
    ("Root",      (0,0,0.22),  (0,0,0.62),  None,     True),
    ("Hips",      (0,0,0.88),  (0,0,1.08),  "Root",   True),
    ("Spine",     (0,0,1.08),  (0,0,1.78),  "Hips",   True),
    ("Head",      (0,0,1.78),  (0,0,2.48),  "Spine",  True),
    ("Antenna",   (0,0,2.48),  (0,0,2.92),  "Head",   True),
    ("Brow.L",    (-0.22,-0.46,2.22), (-0.10,-0.46,2.22), "Head", True),
    ("Brow.R",    (0.10,-0.46,2.22),  (0.22,-0.46,2.22),  "Head", True),
    ("Pupil.L",   (-0.22,-0.50,2.14), (-0.22,-0.50,2.20), "Head", True),
    ("Pupil.R",   (0.22,-0.50,2.14),  (0.22,-0.50,2.20),  "Head", True),
    ("Jaw",       (0,-0.46,1.94), (0,-0.46,2.02), "Head", True),
    ("Arm.L",     (-0.60,0,1.70), (-0.84,0,1.34), "Spine", True),
    ("Forearm.L", (-0.84,0,1.34), (-0.96,0,1.04), "Arm.L", True),
    ("Arm.R",     (0.60,0,1.70),  (0.84,0,1.34),  "Spine", True),
    ("Forearm.R", (0.84,0,1.34),  (0.96,0,1.04),  "Arm.R", True),
    ("Thigh.L",   (-0.30,0,0.88), (-0.30,0,0.54), "Hips",  True),
    ("Shin.L",    (-0.30,0,0.54), (-0.30,0,0.18), "Thigh.L", True),
    ("Foot.L",    (-0.30,0,0.18), (-0.30,-0.24,0.12), "Shin.L", True),
    ("Thigh.R",   (0.30,0,0.88),  (0.30,0,0.54),  "Hips",  True),
    ("Shin.R",    (0.30,0,0.54),  (0.30,0,0.18),  "Thigh.R", True),
    ("Foot.R",    (0.30,0,0.18),  (0.30,-0.24,0.12), "Shin.R", True),
    ("IK.Foot.L", (-0.30,0,0.18), (-0.30,0,0.40), "Root", False),
    ("IK.Foot.R", (0.30,0,0.18),  (0.30,0,0.40),  "Root", False),
    ("IK.Hand.R", (0.96,0,1.04),  (0.96,0,1.34),  "Root", False),
]

def make_robot(tag, style, mats, loc):
    """Returns a dict with rig, controls, face shape keys, and mesh parts."""
    arm = bpy.data.armatures.new(f"{tag}RigData")
    rig = bpy.data.objects.new(f"{tag}Rig", arm)
    bpy.context.collection.objects.link(rig)
    arm.display_type = "OCTAHEDRAL"
    rig.show_in_front = True
    rig.location = (0, 0, 0)   # all motion comes from animated object transform
    BONE_RIG[0] = rig
    bpy.context.view_layer.objects.active = rig
    rig.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    for n, h, t, p, d in BONES:
        eb = arm.edit_bones.new(n)
        eb.head, eb.tail, eb.use_deform = h, t, d
        if p:
            eb.parent = arm.edit_bones[p]
            eb.use_connect = False
    bpy.ops.object.mode_set(mode="OBJECT")
    for pb in rig.pose.bones:
        pb.rotation_mode = "XYZ"

    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode="POSE")
    for side in ("L", "R"):
        c = rig.pose.bones[f"Shin.{side}"].constraints.new("IK")
        c.name = f"IK foot {side}"
        c.target, c.subtarget, c.chain_count, c.use_stretch = rig, f"IK.Foot.{side}", 2, False
    c = rig.pose.bones["Forearm.R"].constraints.new("IK")
    c.name = "IK hand R"
    c.target, c.subtarget, c.chain_count = rig, "IK.Hand.R", 2
    c.influence, c.use_stretch = 0.75, False
    bpy.ops.object.mode_set(mode="OBJECT")

    P = lambda s: f"{tag}_{s}"
    body, light, dark, glow = mats["body"], mats["light"], mats["dark"], mats["glow"]

    # Torso / head — different silhouettes for the two friends
    if style == "red":
        cube(P("Body"), (0,0,1.38), (1.02,0.86,1.02), body, "Spine", 0.16)
        cube(P("Head"), (0,0,2.14), (0.92,0.82,0.84), light, "Head", 0.18)
        cube(P("Belly"), (0,-0.44,1.36), (0.56,0.05,0.56), light, "Spine", 0.07)
        cylinder(P("Antenna"), (0,0,2.48), (0,0,2.90), 0.045, dark, "Antenna")
        sphere(P("AntennaTip"), (0,0,2.94), 0.13, glow, "Antenna")
        # round eyes
        eyes = []
        for s, x in (("L",-0.22),("R",0.22)):
            e = sphere(P(f"Eye{s}"), (x,-0.43,2.20), 0.145, M["white"], "Head")
            eyes.append(e)
            sphere(P(f"Pupil{s}"), (x,-0.545,2.20), 0.065, M["ink"], f"Pupil.{s}")
            cube(P(f"Brow{s}"), (x,-0.47,2.37), (0.24,0.07,0.06), dark, f"Brow.{s}", 0.025)
        # chest heart LED
        heart = sphere(P("Heart"), (0,-0.45,1.52), 0.11, glow, "Spine", scale=(1.0,0.35,1.0))
        # smile mouth with shape keys
        mouth = sphere(P("Mouth"), (0,-0.44,1.98), 0.10, M["ink"], "Jaw", scale=(1.7,0.35,0.5))
        k_open = shape_key(mouth, "Open", (0,-0.44,1.98),
                           lambda d: Vector((d.x*0.75, d.y, d.z*2.6 - 0.02)))
        # eye blink + happy squint shape keys
        keys = {"blink": [], "happy": [], "open": [k_open]}
        for e in eyes:
            c = (x,-0.43,2.20)
            keys["blink"].append(shape_key(e, "Blink", c,
                lambda d: Vector((d.x, d.y, d.z*0.08))))
            keys["happy"].append(shape_key(e, "Happy", c,
                lambda d: Vector((d.x, d.y, d.z*0.42 + 0.02))))
    else:
        # BLUE: hexagonal head, wide visor, twin fins, completely different face
        cube(P("Body"), (0,0,1.38), (1.06,0.80,0.98), body, "Spine", 0.14)
        bpy.ops.mesh.primitive_cylinder_add(vertices=6, radius=0.56, depth=0.80,
                                            location=(0,0,2.14), rotation=(math.pi/2,0,0))
        finish(bpy.context.object, P("Head"), light, "Head", 0.10)
        cube(P("Visor"), (0,-0.44,2.18), (0.78,0.12,0.34), dark, "Head", 0.06)
        eyes = []
        for s, x in (("L",-0.20),("R",0.20)):
            e = sphere(P(f"Eye{s}"), (x,-0.512,2.18), 0.105, glow, "Pupil."+s, scale=(1,0.5,1))
            eyes.append(e)
        for s, x in (("L",-0.30),("R",0.30)):
            cone(P(f"Fin{s}"), (x,0,2.62), 0.10, 0.0, 0.42, light, verts=4,
                 rotation=(0,0,0), bone="Head")
        cube(P("Mouth"), (0,-0.50,1.98), (0.38,0.05,0.045), glow, "Jaw", 0.02)
        k_open = shape_key(bpy.data.objects[P("Mouth")], "Open", (0,-0.50,1.98),
                           lambda d: Vector((d.x, d.y, d.z*3.2 - 0.03)))
        keys = {"blink": [], "happy": [], "open": [k_open]}
        for e in eyes:
            c = (x,-0.512,2.18)
            keys["blink"].append(shape_key(e, "Blink", c,
                lambda d: Vector((d.x, d.y, d.z*0.12))))
            keys["happy"].append(shape_key(e, "Happy", c,
                lambda d: Vector((d.x, d.y, d.z*0.5))))

    # limbs (shared)
    for s, sign in (("L",-1),("R",1)):
        cylinder(P(f"Arm{s}"), (sign*0.60,0,1.70), (sign*0.84,0,1.34), 0.115, body, f"Arm.{s}")
        cylinder(P(f"Forearm{s}"), (sign*0.84,0,1.34), (sign*0.96,0,1.04), 0.095, light, f"Forearm.{s}")
        sphere(P(f"Hand{s}"), (sign*0.96,0,1.02), 0.145, glow, f"Forearm.{s}")
        cylinder(P(f"Thigh{s}"), (sign*0.30,0,0.88), (sign*0.30,0,0.54), 0.145, body, f"Thigh.{s}")
        cylinder(P(f"Shin{s}"), (sign*0.30,0,0.54), (sign*0.30,0,0.18), 0.115, light, f"Shin.{s}")
        cube(P(f"Foot{s}"), (sign*0.30,-0.12,0.12), (0.36,0.44,0.20), dark, f"Foot.{s}", 0.07)
        sphere(P(f"Knee{s}"), (sign*0.30,-0.02,0.54), 0.105, M["gold"], f"Thigh.{s}")
        sphere(P(f"Elbow{s}"), (sign*0.84,0,1.34), 0.095, M["gold"], f"Arm.{s}")

    # bone visualizers for the screenshot proof
    for n, h, t, p, d in BONES:
        if not d:
            continue
        cylinder(f"BONEVIZ_{tag}_{n}", h, t, 0.045, M["glow_cyan"], n, viz=True)

    # Standard skinning: the mesh must be parented to the armature object,
    # otherwise moving the armature object does NOT move the skinned mesh.
    # Both share the same world matrix, so the Armature modifier stays a pure
    # relative bone deformation and the whole robot follows rig.location/yaw.
    from mathutils import Matrix
    parts_here = [o for o in SKINNED
                  if o.name.startswith(tag+"_") or o.name.startswith("BONEVIZ_"+tag+"_")]
    for o in parts_here:
        o.parent = rig
        o.matrix_parent_inverse = Matrix.Identity(4)
    BONE_RIG[0] = None
    return {"tag": tag, "rig": rig, "keys": keys, "style": style,
            "parts": [o for o in parts_here if o.name.startswith(tag+"_")]}

RED = make_robot("Red", "red", {"body":M["red_body"],"light":M["red_light"],
                                "dark":M["red_dark"],"glow":M["glow_red"]}, (-7.2,0,0))
BLUE = make_robot("Blue", "blue", {"body":M["blue_body"],"light":M["blue_light"],
                                   "dark":M["blue_dark"],"glow":M["glow_cyan"]}, (7.4,0,0))

# ---------------------------------------------------------------------------
# HOUSES — two completely different buildings
# ---------------------------------------------------------------------------
def hinged_door(name, hinge, width, height, thickness, mat, open_angle, direction=1):
    """Door whose ORIGIN is the hinge edge; rotation_z opens it outward."""
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0,0,0))
    o = bpy.context.object
    o.name = name
    o.scale = (thickness, width, height)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    for v in o.data.vertices:
        v.co += Vector((thickness/2, direction*width/2, height/2))
    o.location = hinge
    o.data.materials.append(mat)
    b = o.modifiers.new("Bevel", "BEVEL")
    b.width, b.segments = 0.035, 3
    o.modifiers.new("WeightedNormal", "WEIGHTED_NORMAL")
    o["open_angle"] = open_angle
    return o

def cut_hole(target, cutter):
    """Real opening in a wall (Boolean), so windows/doors are not painted on."""
    bpy.ops.object.select_all(action="DESELECT")
    target.select_set(True)
    bpy.context.view_layer.objects.active = target
    mod = target.modifiers.new("BooleanHole", "BOOLEAN")
    mod.operation = "DIFFERENCE"
    mod.object = cutter
    try:
        bpy.ops.object.modifier_apply(modifier=mod.name)
    except Exception as e:
        print("boolean apply failed:", e)
    cutter.hide_render = True
    cutter.hide_set(True)
    return target

def boolean_box(name, loc, dims):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    o = bpy.context.object
    o.name = name
    o.scale = dims
    return o

def boolean_cylinder(name, loc, radius, depth, rotation):
    bpy.ops.mesh.primitive_cylinder_add(vertices=32, radius=radius,
                                        depth=depth, location=loc, rotation=rotation)
    o = bpy.context.object
    o.name = name
    return o

def window_frame(name, center, w, h, frame_mat, glow=False):
    cx, cy, cz = center
    t = 0.10
    cube(name+"_top", (cx,cy,cz+h/2), (t*2,w+t*2,t*2), frame_mat, bevel=0.03)
    cube(name+"_bot", (cx,cy,cz-h/2), (t*2,w+t*2,t*2), frame_mat, bevel=0.03)
    cube(name+"_l", (cx,cy-w/2,cz), (t*2,t*2,h), frame_mat, bevel=0.03)
    cube(name+"_r", (cx,cy+w/2,cz), (t*2,t*2,h), frame_mat, bevel=0.03)
    cube(name+"_mull", (cx,cy,cz), (t*2,t,h), frame_mat, bevel=0.02)
    if glow:
        cube(name+"_glow", (cx,cy+t*0.2,cz), (0.02,w*0.96,h*0.96), M["glow_warm"], bevel=0.01)

# --- RED HOUSE: warm rounded brick cottage, REAL hollow walls ---------------
RH = (-8.0, 0.0)
RW, RD, RH_H, WT = 3.2, 3.0, 3.3, 0.22
FX = RH[0] + RW/2
cube("RedHouse_Back",   (RH[0]-RW/2, 0, RH_H/2), (WT,RD,RH_H), M["brick"], bevel=0.08)
cube("RedHouse_SideL",  (RH[0], -RD/2, RH_H/2), (RW,WT,RH_H), M["brick"], bevel=0.08)
cube("RedHouse_SideR",  (RH[0],  RD/2, RH_H/2), (RW,WT,RH_H), M["brick"], bevel=0.08)
cube("RedHouse_PillarL",(FX,-1.05,RH_H/2), (WT,0.90,RH_H), M["brick"], bevel=0.08)
cube("RedHouse_PillarR",(FX, 1.05,RH_H/2), (WT,0.90,RH_H), M["brick"], bevel=0.08)
cube("RedHouse_Lintel", (FX, 0, 2.75), (WT,1.20,1.10), M["brick"], bevel=0.08)
cone("RedHouse_Roof", (RH[0],RH[1],3.85), 2.55, 0.0, 1.75, M["roof_red"], verts=4,
     rotation=(0,0,math.pi/4))
cube("RedHouse_Chimney", (RH[0]-0.9,RH[1]+0.8,4.15), (0.5,0.5,1.1), M["brick"], bevel=0.07)
cube("RedHouse_Foundation", (RH[0],RH[1],0.12), (3.5,3.3,0.24), M["stone"], bevel=0.06)
cube("RedHouse_Floor", (RH[0],0,-0.02), (RW,RD,0.1), M["wood"], bevel=0.03)

DOOR_RX = FX + 0.02
cube("RedHouse_DoorFrameL", (DOOR_RX, -0.66, 1.05), (0.22,0.14,2.2), M["wood"], bevel=0.05)
cube("RedHouse_DoorFrameR", (DOOR_RX,  0.66, 1.05), (0.22,0.14,2.2), M["wood"], bevel=0.05)
cube("RedHouse_DoorFrameT", (DOOR_RX, 0.0, 2.14), (0.22,1.46,0.16), M["wood"], bevel=0.05)
RED_DOOR = hinged_door("RedHouse_Door", (DOOR_RX, -0.60, 0.02), 1.2, 2.05, 0.12, M["wood"], -1.35)
sphere("RedHouse_DoorKnob", (DOOR_RX+0.10, 0.42, 1.05), 0.075, M["gold"])

def frame_y(name, center, w, h, mat, glow=False):
    """Window frame in the XZ plane (wall normal = Y)."""
    cx,cy,cz = center; t=0.09
    cube(name+"_top", (cx,cy,cz+h/2), (w+t*2,t*2,t*2), mat, bevel=0.03)
    cube(name+"_bot", (cx,cy,cz-h/2), (w+t*2,t*2,t*2), mat, bevel=0.03)
    cube(name+"_l",   (cx-w/2,cy,cz), (t*2,t*2,h), mat, bevel=0.03)
    cube(name+"_r",   (cx+w/2,cy,cz), (t*2,t*2,h), mat, bevel=0.03)
    cube(name+"_mul", (cx,cy,cz), (t,t,h), mat, bevel=0.02)
    if glow:
        cube(name+"_glow", (cx,cy+0.02,cz), (w*0.94,0.02,h*0.94), M["glow_warm"], bevel=0.01)
frame_y("RedHouse_WinL", (RH[0]-0.75,-RD/2-0.02,2.05), 0.85,0.85, M["wood"], True)
frame_y("RedHouse_WinR", (RH[0]+0.75,-RD/2-0.02,2.05), 0.85,0.85, M["wood"], True)
cube("RedHouse_FlowerBox", (RH[0], -RD/2-0.20, 1.45), (1.7,0.30,0.26), M["wood"], bevel=0.05)
for i in range(7):
    sphere(f"RedFlower_{i}", (RH[0]-0.7+i*0.23, -RD/2-0.34, 1.64), 0.09,
           STREAMER_COLS[i%5], scale=(1,1,0.7))

# --- BLUE HOUSE: tall cool tower, completely different silhouette -----------
BH = (8.0, 0.0)
BW, BD, BH_H = 3.5, 3.5, 4.4
BX = BH[0] - BW/2
cube("BlueHouse_Back",  (BH[0]+BW/2, 0, BH_H/2), (WT,BD,BH_H), M["blue_wall"], bevel=0.10)
cube("BlueHouse_SideL", (BH[0], -BD/2, BH_H/2), (BW,WT,BH_H), M["blue_wall"], bevel=0.10)
cube("BlueHouse_SideR", (BH[0],  BD/2, BH_H/2), (BW,WT,BH_H), M["blue_wall"], bevel=0.10)
cube("BlueHouse_PillarL",(BX,-1.32,BH_H/2), (WT,0.86,BH_H), M["blue_wall"], bevel=0.10)
cube("BlueHouse_PillarR",(BX, 1.32,BH_H/2), (WT,0.86,BH_H), M["blue_wall"], bevel=0.10)
cube("BlueHouse_Lintel", (BX, 0, 3.80), (WT,1.78,1.20), M["blue_wall"], bevel=0.10)
cube("BlueHouse_Mullion",(BX, 0, 3.15), (WT,1.78,0.08), M["gold"], bevel=0.03)
sphere("BlueHouse_Dome", (BH[0],BH[1],4.55), 1.80, M["blue_roof"], scale=(1,1,0.55))
cube("BlueHouse_Band", (BH[0],BH[1],3.42), (3.7,3.7,0.18), M["gold"], bevel=0.05)
cube("BlueHouse_Foundation", (BH[0],BH[1],0.12), (3.7,3.7,0.24), M["stone"], bevel=0.06)

DOOR_BX = BX - 0.02
cube("BlueHouse_DoorFrameL", (DOOR_BX, -0.72, 1.12), (0.22,0.14,2.35), M["blue_light"], bevel=0.05)
cube("BlueHouse_DoorFrameR", (DOOR_BX,  0.72, 1.12), (0.22,0.14,2.35), M["blue_light"], bevel=0.05)
cube("BlueHouse_DoorFrameT", (DOOR_BX, 0.0, 2.26), (0.22,1.58,0.16), M["blue_light"], bevel=0.05)
BLUE_DOOR = hinged_door("BlueHouse_Door", (DOOR_BX, 0.64, 0.02), 1.28, 2.2, 0.12,
                        M["blue_light"], 1.45, direction=-1)
sphere("BlueHouse_DoorKnob", (DOOR_BX-0.10, -0.46, 1.1), 0.075, M["gold"])
# big OPEN round window in the upper part of the front opening
bpy.ops.mesh.primitive_torus_add(major_segments=48, minor_segments=12,
    major_radius=0.80, minor_radius=0.10, location=(DOOR_BX-0.03, 0, 2.95),
    rotation=(0, math.pi/2, 0))
finish(bpy.context.object, "BlueHouse_RoundWindow", M["gold"], None, 0.01, True)
frame_y("BlueHouse_WinSide", (BH[0]+0.6, -BD/2-0.02, 2.2), 0.9,1.1, M["blue_light"], True)
# interior
cube("BlueHouse_Floor", (BH[0], 0, -0.02), (BW,BD,0.10), M["wood"], bevel=0.03)
cube("BlueHouse_InnerWall", (BH[0]+1.45, 0, 2.2), (0.10,BD,4.4), M["blue_wall"], bevel=0.05)
sphere("BlueHouse_Rug", (BH[0]-0.2, 0, 0.04), 1.05, M["gift"], scale=(1.3,1.0,0.02))
cylinder("BlueHouse_LampStand", (BH[0]+0.9, 1.1, 0), (BH[0]+0.9, 1.1, 1.5), 0.05, M["gold"])
sphere("BlueHouse_Lamp", (BH[0]+0.9, 1.1, 1.55), 0.26, M["glow_warm"])
# a little window stool: Blue stands on it to peek through the round window
cube("BlueHouse_WindowStool", (7.10,0.15,0.22), (0.78,0.78,0.44), M["blue_light"], bevel=0.07)
bpy.context.view_layer.update()
for knob_name, door in (("RedHouse_DoorKnob", RED_DOOR),
                        ("BlueHouse_DoorKnob", BLUE_DOOR)):
    knob = bpy.data.objects[knob_name]
    knob.parent = door
    knob.matrix_parent_inverse = door.matrix_world.inverted()


# ---------------------------------------------------------------------------
# ENVIRONMENT: grass, winding stone path, arch (CORRECTLY ORIENTED), trees
# ---------------------------------------------------------------------------
cube("Ground", (0,0,-0.18), (40,34,0.3), M["grass"], bevel=0.0)
cube("SkyBackdrop", (0,14,7), (44,0.2,16), M["blue_roof"], bevel=0.0)

PATH_X0, PATH_X1 = -5.4, 6.0
def path_y(x):
    t = (x - PATH_X0) / (PATH_X1 - PATH_X0)
    return 1.30 * math.sin(math.pi * t)

# visible path ribbon
pc = bpy.data.curves.new("PathRibbonData", "CURVE")
pc.dimensions, pc.bevel_depth, pc.bevel_resolution = "3D", 0.9, 2
sp = pc.splines.new("POLY")
N = 60
sp.points.add(N-1)
for i in range(N):
    x = PATH_X0 + (PATH_X1-PATH_X0)*i/(N-1)
    sp.points[i].co = (x, path_y(x), -0.005, 1)
path_obj = bpy.data.objects.new("PathRibbon", pc)
bpy.context.collection.objects.link(path_obj)
pc.materials.append(M["soil"])

# stepping stones
STONES = []
for i in range(26):
    x = PATH_X0 + 0.15 + (PATH_X1-PATH_X0-0.3)*i/25
    y = path_y(x)
    o = cube(f"Stone_{i:02d}", (x,y,0.02), (0.62,0.52,0.10), M["stone"], bevel=0.07)
    o.rotation_euler.z = 0.12*math.sin(i*1.7)
    STONES.append(o)

# Garden arch: hole axis = +X, so the robot walking +X passes THROUGH it.
ARCH_X, ARCH_Y, ARCH_Z = 0.3, path_y(0.3), 1.60
ARCH_MAJOR, ARCH_MINOR = 2.0, 0.15
bpy.ops.mesh.primitive_torus_add(major_segments=64, minor_segments=16,
    major_radius=ARCH_MAJOR, minor_radius=ARCH_MINOR,
    location=(ARCH_X, ARCH_Y, ARCH_Z), rotation=(0, math.pi/2, 0))
ARCH = finish(bpy.context.object, "GardenArch_Hoop", M["gold"], None, 0.01, True)
cylinder("GardenArch_PostL", (ARCH_X, ARCH_Y-2.05, 0), (ARCH_X, ARCH_Y-2.05, 1.0), 0.10, M["wood"])
cylinder("GardenArch_PostR", (ARCH_X, ARCH_Y+2.05, 0), (ARCH_X, ARCH_Y+2.05, 1.0), 0.10, M["wood"])
for i in range(12):
    a = 2*math.pi*i/12
    sphere(f"ArchBead_{i}", (ARCH_X, ARCH_Y+ARCH_MAJOR*math.cos(a),
                             ARCH_Z+ARCH_MAJOR*math.sin(a)), 0.09, STREAMER_COLS[i%5])

TREES, FLOWERS = [], []
for i, (x,y,s) in enumerate([(-4.6,-3.2,1.0),(-2.2,3.4,0.8),(1.8,-3.6,1.15),
                              (4.4,3.2,0.9),(-1.0,-4.6,0.75),(3.0,-4.4,0.85),
                              (-5.6,2.6,0.7),(6.2,-2.8,0.8)]):
    cylinder(f"Tree{i}_Trunk", (x,y,0), (x,y,1.2*s), 0.16*s, M["bark"])
    cone(f"Tree{i}_Crown1", (x,y,1.7*s), 0.95*s, 0.0, 1.5*s, M["leaf"], verts=8)
    cone(f"Tree{i}_Crown2", (x,y,2.4*s), 0.70*s, 0.0, 1.2*s, M["leaf"], verts=8)
    TREES.append(x)
for i in range(30):
    x = random.uniform(-6, 6.5); y = random.choice([-1,1])*random.uniform(2.2,5.5)
    sphere(f"Flower{i}", (x,y,0.16), 0.075, STREAMER_COLS[i%5], scale=(1,1,0.7))
    FLOWERS.append(x)

# clouds
for i,(x,y,z,s) in enumerate([(-6,8,7,1.2),(0,10,8,1.6),(6,9,7.5,1.1)]):
    for j in range(3):
        sphere(f"Cloud{i}_{j}", (x+(j-1)*0.8*s, y, z+0.15*s*math.sin(j)), 0.65*s,
               M["white"], scale=(1.3,0.8,0.7))

# ---------------------------------------------------------------------------
# LIGHTS / WORLD
# ---------------------------------------------------------------------------
def area(name, loc, energy, size, color, target=(0,0,1.5)):
    bpy.ops.object.light_add(type="AREA", location=loc)
    l = bpy.context.object; l.name = name
    l.data.energy, l.data.size, l.data.color = energy, size, color
    l.rotation_euler = (Vector(target)-Vector(loc)).to_track_quat("-Z","Y").to_euler()
    return l
area("Sun_Key", (-4,-7,12), 2600, 8.0, (1.0,0.90,0.76))
area("Sky_Fill", (7,-5,8), 1500, 9.0, (0.62,0.80,1.0))
area("Rim", (2,8,9), 1800, 7.0, (1.0,0.62,0.72))
area("Interior_Warm", (8.0,0.4,3.0), 700, 3.0, (1.0,0.72,0.42), (8,0,1.4))
area("Red_Porch", (-6.2,-1.2,3.0), 500, 2.5, (1.0,0.70,0.40), (-6.2,0,1.4))
world = scene.world or bpy.data.worlds.new("Sky")
scene.world = world
world.use_nodes = True
bg = world.node_tree.nodes["Background"]
bg.inputs["Color"].default_value = (0.30,0.52,0.85,1)
bg.inputs["Strength"].default_value = 0.55

# ---------------------------------------------------------------------------
# CAMERAS: 5 shots bound to timeline markers -> real cuts with moving cameras
# ---------------------------------------------------------------------------
def camera(name, loc, target, lens=42):
    bpy.ops.object.camera_add(location=loc)
    c = bpy.context.object; c.name = name; c.data.lens = lens
    bpy.ops.object.empty_add(type="PLAIN_AXES", location=target)
    t = bpy.context.object; t.name = name+"_Target"
    con = c.constraints.new("TRACK_TO")
    con.target, con.track_axis, con.up_axis = t, "TRACK_NEGATIVE_Z", "UP_Y"
    return c, t

CAMS = {}
CAMS["A"] = camera("CamA_Follow", (-13,-12,7), (-7,0,1.5), 40)
CAMS["B"] = camera("CamB_Window", (2.0,-2.5,3.2), (6.2,0.2,2.0), 28)
CAMS["C"] = camera("CamC_Door", (2.0,-2.4,2.6), (6.35,0,1.55), 38)
CAMS["D"] = camera("CamD_Inside", (10.2,-3.8,3.3), (7.1,0,1.5), 30)
CAMS["E"] = camera("CamE_Gift", (10.5,-4.0,3.4), (7.3,0,1.8), 28)
scene.camera = CAMS["A"][0]
CUTAWAY = [bpy.data.objects[n] for n in (
    "BlueHouse_SideL", "BlueHouse_Door", "BlueHouse_DoorKnob",
    "BlueHouse_DoorFrameL", "BlueHouse_DoorFrameR", "BlueHouse_DoorFrameT",
    "BlueHouse_WinSide_top", "BlueHouse_WinSide_bot", "BlueHouse_WinSide_l",
    "BlueHouse_WinSide_r", "BlueHouse_WinSide_mul", "BlueHouse_WinSide_glow",
    "BlueHouse_PillarL", "BlueHouse_PillarR", "BlueHouse_Lintel",
    "BlueHouse_Mullion", "BlueHouse_Band")]
for o in CUTAWAY:
    for f, hidden in [(1,False),(168,False),(169,True),(240,True)]:
        o.hide_render = hidden
        o.keyframe_insert(data_path="hide_render", frame=f)
for f, key in [(1,"A"),(89,"B"),(129,"C"),(169,"D"),(205,"E")]:
    mk = scene.timeline_markers.new(f"SHOT_{key}", frame=f)
    mk.camera = CAMS[key][0]

# ---------------------------------------------------------------------------
# ANIMATION HELPERS
# ---------------------------------------------------------------------------
def k_obj(o, path, value, frame):
    setattr(o, path, value)
    o.keyframe_insert(data_path=path, frame=frame)

def k_pose(pb, path, value, frame):
    setattr(pb, path, value)
    pb.keyframe_insert(data_path=path, frame=frame, group=pb.name)

def k_world(pb, armature_vec, frame):
    """Convert an armature-space displacement into PoseBone.location space."""
    local = pb.bone.matrix_local.to_3x3().inverted() @ Vector(armature_vec)
    k_pose(pb, "location", tuple(local), frame)

def emotion(R, frame, blink=0.0, happy=0.0, open_mouth=0.0, brow=0.0,
            look=(0.0,0.0), antenna=0.0):
    for k in R["keys"]["blink"]:
        k.value = blink; k.keyframe_insert(data_path="value", frame=frame)
    for k in R["keys"]["happy"]:
        k.value = happy; k.keyframe_insert(data_path="value", frame=frame)
    for k in R["keys"]["open"]:
        k.value = open_mouth; k.keyframe_insert(data_path="value", frame=frame)
    rig = R["rig"]
    for s in ("L","R"):
        k_world(rig.pose.bones[f"Brow.{s}"], (0,0,brow), frame)
        k_world(rig.pose.bones[f"Pupil.{s}"], (look[0],0,look[1]), frame)
    k_world(rig.pose.bones["Jaw"], (0,0,-0.07*open_mouth), frame)
    k_pose(rig.pose.bones["Antenna"], "rotation_euler", (antenna,0,0), frame)

# --- RED path ---------------------------------------------------------------
RED_X = {1:-7.20, 12:-7.20, 20:-6.00, 28:-5.40, 40:-3.60, 54:0.30,
         70:2.80, 88:4.60, 110:5.60, 129:6.00, 140:6.00, 168:6.00,
         186:7.35, 204:7.35, 240:7.35}
def red_x(f):
    ks = sorted(RED_X)
    if f <= ks[0]: return RED_X[ks[0]]
    if f >= ks[-1]: return RED_X[ks[-1]]
    for a,b in zip(ks,ks[1:]):
        if a <= f <= b:
            t = (f-a)/(b-a); t = t*t*(3-2*t)
            return RED_X[a] + (RED_X[b]-RED_X[a])*t
    return RED_X[ks[-1]]

red_rig, blue_rig = RED["rig"], BLUE["rig"]
# rig objects carry the world translation + yaw; Root bone only bobs/squashes
def smooth01(t):
    t = max(0.0, min(1.0, t)); return t*t*(3-2*t)
def red_yaw(f):
    # -X at the red doorway (face the camera), +X along the path,
    # then a friendly turn to -X so both faces are visible in the finale.
    if f <= 12: return -math.pi/2
    if f < 22:  return -math.pi/2 + math.pi*smooth01((f-12)/10)
    if f < 205: return math.pi/2
    return math.pi/2 + 0.06*math.sin((f-205)*0.10)
for f in range(F0, F1+1, 4):
    x = red_x(f)
    y = path_y(x) if x > PATH_X0 else 0.0
    k_obj(red_rig, "location", (x,y,0), f)
    k_obj(red_rig, "rotation_euler", (0,0,red_yaw(f)), f)
# finer keys at story beats
for f in RED_X:
    x = RED_X[f]; y = path_y(x) if x > PATH_X0 else 0.0
    k_obj(red_rig, "location", (x,y,0), f)
    k_obj(red_rig, "rotation_euler", (0,0,red_yaw(f)), f)

# walk cycle (frames 20..140 and 169..190)
for f in range(20, 141, 2):
    x = red_x(f)
    phase = (x + 5.4) / 1.05 * 2*math.pi
    moving = x < 6.05
    bob = 0.055*math.sin(2*phase) if moving else 0.0
    k_world(red_rig.pose.bones["Root"], (0,0,bob), f)
    stride = 0.40*math.cos(phase) if moving else 0.0
    lift_l = 0.24*max(0.0, math.sin(phase)) if moving else 0.0
    lift_r = 0.24*max(0.0,-math.sin(phase)) if moving else 0.0
    k_world(red_rig.pose.bones["IK.Foot.L"], (0,-stride,lift_l), f)
    k_world(red_rig.pose.bones["IK.Foot.R"], (0, stride,lift_r), f)
    swing = 0.50*math.sin(phase) if moving else 0.0
    k_pose(red_rig.pose.bones["Arm.L"], "rotation_euler", (swing,0,0), f)
    k_pose(red_rig.pose.bones["Arm.R"], "rotation_euler", (-swing,0,0), f)
    k_pose(red_rig.pose.bones["Spine"], "rotation_euler", (0,0,0.05*math.sin(phase)), f)
    k_pose(red_rig.pose.bones["Antenna"], "rotation_euler", (0.22*math.sin(phase+0.8),0,0), f)
    k_pose(red_rig.pose.bones["Hips"], "rotation_euler", (0,0,0.045*math.sin(phase)), f)

# anticipation / squash when leaving and when knocking
for f, sz in {1:1.0, 8:0.86, 16:1.06, 22:1.0, 60:1.0, 129:0.90, 138:1.05,
              146:1.0, 205:1.0, 214:1.10, 224:1.0, 240:1.0}.items():
    sxy = 1/math.sqrt(sz)
    k_pose(red_rig.pose.bones["Spine"], "scale", (sxy,sxy,sz), f)

# RED emotions: curious -> happy walking -> surprised at gift -> delighted
for f, kw in {
    1:dict(), 12:dict(blink=1), 20:dict(blink=0, happy=0.15),
    30:dict(look=(-0.03,0.02), brow=-0.02), 36:dict(look=(0,0), brow=0),
    54:dict(happy=0.35), 88:dict(happy=0.45),
    129:dict(happy=0.2, brow=0.02), 142:dict(blink=1),
    150:dict(blink=0, happy=0.5, open_mouth=0.35),
    169:dict(happy=0.5, open_mouth=0.2),
    205:dict(happy=0.1, brow=0.09, open_mouth=0.75, look=(0,0.03)),
    216:dict(happy=0.85, open_mouth=0.9, antenna=-0.35),
    228:dict(happy=0.95, open_mouth=0.5, antenna=0.25),
    240:dict(happy=0.9, open_mouth=0.35),
}.items():
    emotion(RED, f, **kw)

# --- BLUE: at window, then to the door -------------------------------------
def blue_x(f):
    ks = sorted(BLUE_X)
    if f <= ks[0]: return BLUE_X[ks[0]]
    if f >= ks[-1]: return BLUE_X[ks[-1]]
    for a,b in zip(ks,ks[1:]):
        if a <= f <= b:
            t=(f-a)/(b-a); t=t*t*(3-2*t)
            return BLUE_X[a]+(BLUE_X[b]-BLUE_X[a])*t
    return BLUE_X[ks[-1]]
BLUE_X = {1:7.40, 88:7.10, 110:7.10, 128:6.95, 168:6.95, 204:7.80, 240:7.80}
def blue_z(f):
    if f < 88: return 0.0
    if f < 110: return 0.45
    if f < 128: return 0.45*(1-smooth01((f-110)/18))
    return 0.0
def blue_yaw(f):
    if f < 169: return -math.pi/2
    if f < 190: return -math.pi/2 + math.pi*smooth01((f-169)/21)
    return math.pi/2
for f in range(F0,F1+1,4):
    k_obj(blue_rig, "location", (blue_x(f),0.15,blue_z(f)), f)
    k_obj(blue_rig, "rotation_euler", (0,0,blue_yaw(f)), f)
for f in BLUE_X:
    k_obj(blue_rig, "location", (blue_x(f),0.15,blue_z(f)), f)
    k_obj(blue_rig, "rotation_euler", (0,0,blue_yaw(f)), f)
for f in range(88, 129, 3):
    t = (f-88)/40
    k_pose(blue_rig.pose.bones["Head"], "rotation_euler", (0,0,-0.20*t), f)
    k_world(blue_rig.pose.bones["IK.Hand.R"], (0,0,0.10*math.sin(t*math.pi)), f)
for f, sz in {1:1.0, 96:1.06, 104:0.94, 112:1.0, 205:1.0, 214:1.12, 226:1.0, 240:1.0}.items():
    sxy=1/math.sqrt(sz)
    k_pose(blue_rig.pose.bones["Spine"], "scale", (sxy,sxy,sz), f)
for f, kw in {
    1:dict(), 89:dict(look=(-0.04,0)), 96:dict(brow=0.10, open_mouth=0.55, look=(-0.05,0.02)),
    104:dict(brow=0.06, open_mouth=0.3), 112:dict(happy=0.6, brow=0.03, open_mouth=0.1),
    128:dict(happy=0.55), 150:dict(happy=0.8, open_mouth=0.3),
    169:dict(happy=0.85, open_mouth=0.4),
    205:dict(happy=0.9, open_mouth=0.6, antenna=0.3),
    216:dict(happy=1.0, open_mouth=0.85, antenna=-0.3),
    228:dict(happy=1.0, open_mouth=0.5), 240:dict(happy=0.95, open_mouth=0.3),
}.items():
    emotion(BLUE, f, **kw)

# --- DOORS -----------------------------------------------------------------
# Red forgets to close it: opens by frame 18 and STAYS open to the end.
for f,a in {1:0.0, 6:0.0, 18:-1.35, 28:-1.35, 240:-1.35}.items():
    k_obj(RED_DOOR, "rotation_euler", (0,0,a), f)
# Blue opens only after the knock
for f,a in {1:0.0, 129:0.0, 150:0.0, 162:1.45, 168:1.45, 240:1.45}.items():
    k_obj(BLUE_DOOR, "rotation_euler", (0,0,a), f)

# --- KNOCK: red right hand taps three times --------------------------------
for f,z in {140:0, 143:0.34, 146:0, 149:0.34, 152:0, 155:0.30, 158:0, 168:0}.items():
    k_world(red_rig.pose.bones["IK.Hand.R"], (0,0,z), f)
# waving greeting after the door opens
for f,z in {162:0.10, 168:0.45, 176:0.15, 186:0}.items():
    k_world(blue_rig.pose.bones["IK.Hand.R"], (0,0,z), f)

# --- GIFT BOX + lid (prepass: follow Blue's right hand) ---------------------
# create the box first, then key it from sampled hand positions
GIFT = cube("GiftBox_Base", (7.4,0,1.2), (0.62,0.62,0.55), M["gift"], bevel=0.05)
GIFT_LID = cube("GiftBox_Lid", (7.4,0,1.52), (0.70,0.70,0.14), M["gift"], bevel=0.045)
RIB_X = cube("GiftBox_RibbonX", (7.4,0,1.2), (0.66,0.12,0.57), M["ribbon"], bevel=0.02)
RIB_Y = cube("GiftBox_RibbonY", (7.4,0,1.2), (0.12,0.66,0.57), M["ribbon"], bevel=0.02)
BOW_L = sphere("GiftBox_BowL", (7.28,0,1.56), 0.13, M["ribbon"], scale=(1,0.6,0.7))
BOW_R = sphere("GiftBox_BowR", (7.52,0,1.56), 0.13, M["ribbon"], scale=(1,0.6,0.7))
GIFT_DECOR = [(RIB_X,(0,0,0)), (RIB_Y,(0,0,0)),
              (BOW_L,(-0.12,0,0.34)), (BOW_R,(0.12,0,0.34))]

prep = []
for f in range(F0,F1+1):
    scene.frame_set(f)
    pb = blue_rig.pose.bones["Forearm.R"]
    prep.append(tuple(blue_rig.matrix_world @ pb.tail))
for f in range(F0,F1+1,2):
    h = Vector(prep[f-1])
    bx = 7.55 if f < 205 else 7.55 - 0.10*min(1,(f-205)/20)
    cy = 0.0 if f >= 169 else h.y-0.10
    cz = h.z+0.22
    k_obj(GIFT, "location", (bx,cy,cz), f)
    k_obj(GIFT_LID, "location", (bx,cy,cz+0.34), f)
    for o,off in GIFT_DECOR:
        k_obj(o, "location", (bx+off[0],cy+off[1],cz+off[2]), f)
for f,ang in {1:0,204:0,210:-1.15,216:-1.35,240:-1.25}.items():
    k_obj(GIFT_LID, "rotation_euler", (0,ang,0), f)

# --- STREAMERS + CONFETTI burst --------------------------------------------
BURST = []
for i in range(54):
    col = STREAMER_COLS[i%5]
    bpy.ops.mesh.primitive_cube_add(size=1, location=(7.55,0,1.7))
    o = bpy.context.object
    o.name = f"Streamer_{i:02d}"
    o.scale = (0.035, 0.035, 0.42)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    o.data.materials.append(col)
    BURST.append(o)
for i in range(36):
    bpy.ops.mesh.primitive_cube_add(size=0.10, location=(7.55,0,1.7))
    o = bpy.context.object
    o.name = f"Confetti_{i:02d}"
    o.data.materials.append(STREAMER_COLS[i%5])
    BURST.append(o)

random.seed(991)
for i,o in enumerate(BURST):
    a = random.uniform(0,2*math.pi)
    r = random.uniform(0.35,2.3)
    dx, dy = math.cos(a)*r, math.sin(a)*r
    top = random.uniform(1.0,1.8)
    rot = tuple(random.uniform(0,6.28) for _ in range(3))
    for f, p, s in [
        (1,(7.55,0,1.60),0.001), (204,(7.55,0,1.60),0.001),
        (211,(7.55+dx*0.25, dy*0.25, 1.7+top*0.18), 0.7),
        (224,(7.55+dx*0.8, dy*0.8, 1.7+top*0.65), 1.0),
        (240,(7.55+dx, dy, 1.10+random.random()*0.85), 0.85),
    ]:
        k_obj(o, "location", p, f)
        k_obj(o, "scale", (s,s,s), f)
    k_obj(o, "rotation_euler", rot, 240)

# --- CAMERA MOVES -----------------------------------------------------------
for f, loc, tgt in [
    (1, (-13,-12,7.2), (-7.0,0,1.6)), (48, (-6.5,-11,6.2), (-3.0,1.0,1.6)),
    (88, (1.0,-10,5.2), (4.4,0.8,1.6)),
]:
    k_obj(CAMS["A"][0], "location", loc, f)
    k_obj(CAMS["A"][1], "location", tgt, f)
# Shot B: straight through the OPEN front window — Blue sees Red approaching.
for f, loc, tgt in [
    (89,(2.0,-2.5,3.2),(6.2,0.2,2.0)), (110,(2.3,-2.4,3.1),(6.3,0.1,2.0)),
    (128,(2.6,-2.2,3.0),(6.5,0.0,2.0)),
]:
    k_obj(CAMS["B"][0], "location", loc, f); k_obj(CAMS["B"][1], "location", tgt, f)
# Shot C: door and knock, both robots unobstructed in the front opening.
for f, loc, tgt in [
    (129,(2.0,-2.4,2.6),(6.35,0,1.55)), (150,(2.4,-2.3,2.55),(6.4,0,1.58)),
    (168,(2.8,-2.1,2.5),(6.5,0,1.60)),
]:
    k_obj(CAMS["C"][0], "location", loc, f); k_obj(CAMS["C"][1], "location", tgt, f)
# Shots D/E: wide doll-house cutaway of the blue interior (near wall is hidden).
for f, loc, tgt in [
    (169,(10.2,-3.8,3.3),(7.1,0,1.5)), (190,(10.3,-3.9,3.4),(7.25,0,1.6)),
    (204,(10.4,-4.0,3.4),(7.35,0,1.7)),
]:
    k_obj(CAMS["D"][0], "location", loc, f); k_obj(CAMS["D"][1], "location", tgt, f)
for f, loc, tgt in [
    (205,(10.5,-4.0,3.4),(7.3,0,1.8)), (224,(10.7,-4.3,3.6),(7.4,0,1.9)),
    (240,(10.9,-4.6,3.8),(7.4,0,2.0)),
]:
    k_obj(CAMS["E"][0], "location", loc, f); k_obj(CAMS["E"][1], "location", tgt, f)

# ---------------------------------------------------------------------------
# Graph Editor smoothing (Blender 5.3 slotted actions)
# ---------------------------------------------------------------------------
def channelbags(idb):
    ad = getattr(idb,"animation_data",None)
    if not ad or not ad.action: return []
    slot = getattr(ad,"action_slot",None)
    if slot is not None:
        cb = anim_utils.action_get_channelbag_for_slot(ad.action, slot)
        return [cb] if cb else []
    out=[]
    for layer in getattr(ad.action,"layers",[]):
        for strip in getattr(layer,"strips",[]):
            out += list(getattr(strip,"channelbags",[]))
    return out
FC=[]
ids = list(bpy.data.objects) + [o.data.shape_keys for o in bpy.data.objects
                                if o.type=="MESH" and o.data.shape_keys]
for idb in ids:
    for cb in channelbags(idb):
        for fc in cb.fcurves:
            if fc.data_path == "hide_render":
                for k in fc.keyframe_points: k.interpolation = "CONSTANT"
            else:
                for k in fc.keyframe_points:
                    k.interpolation = "BEZIER"
                    k.handle_left_type = k.handle_right_type = "AUTO_CLAMPED"
            FC.append({"id":getattr(idb,"name","shapekeys"),"path":fc.data_path,
                       "index":fc.array_index,"keys":len(fc.keyframe_points)})

# Motion paths from Blender itself
MP = {}
try:
    bpy.ops.object.select_all(action="DESELECT")
    for o in (red_rig, blue_rig, GIFT): o.select_set(True)
    bpy.context.view_layer.objects.active = red_rig
    bpy.ops.object.paths_calculate(display_type="RANGE", range="SCENE")
    MP["object_paths"]="ok"
except Exception as e: MP["object_paths"]=f"failed: {e}"
try:
    bpy.context.view_layer.objects.active = red_rig
    bpy.ops.object.mode_set(mode="POSE")
    bpy.ops.pose.paths_calculate(display_type="RANGE", range="SCENE", bake_location="HEADS")
    MP["red_pose_paths"]="ok"
    bpy.ops.object.mode_set(mode="OBJECT")
except Exception as e:
    MP["red_pose_paths"]=f"failed: {e}"
    try: bpy.ops.object.mode_set(mode="OBJECT")
    except Exception: pass

# ---------------------------------------------------------------------------
# SAMPLE EVERY FRAME — objects, bones, deformed centres, cameras
# ---------------------------------------------------------------------------
scene.frame_set(F0)
TRACKED = [o for o in bpy.data.objects if o.type in {"MESH","CURVE","CAMERA","EMPTY","LIGHT","ARMATURE"}]
DEFORM = [f"{t}_Body" for t in ("Red","Blue")] + ["GiftBox_Base","GiftBox_Lid",
          "RedHouse_Door","BlueHouse_Door"]
TRAJ = {"red":[], "blue":[], "gift":[], "red_door":[], "blue_door":[]}
FRAMES=[]

def deformed_center(o, dg):
    ev = o.evaluated_get(dg); mesh = ev.to_mesh()
    if not mesh or not mesh.vertices:
        if mesh: ev.to_mesh_clear()
        return list(o.matrix_world.translation)
    c=Vector((0,0,0))
    for v in mesh.vertices: c += ev.matrix_world @ v.co
    c/=len(mesh.vertices); ev.to_mesh_clear()
    return [c.x,c.y,c.z]

for f in range(F0,F1+1):
    scene.frame_set(f)
    dg = bpy.context.evaluated_depsgraph_get()
    objs={}
    for o in TRACKED:
        objs[o.name]={"location":[round(v,4) for v in o.matrix_world.translation],
                      "rotation":[round(v,4) for v in o.rotation_euler],
                      "scale":[round(v,4) for v in o.scale]}
    bones={}
    for R in (RED,BLUE):
        rig=R["rig"]
        for pb in rig.pose.bones:
            bones[f"{R['tag']}.{pb.name}"]={
                "head":[round(v,4) for v in rig.matrix_world@pb.head],
                "tail":[round(v,4) for v in rig.matrix_world@pb.tail],
                "scale":[round(v,4) for v in pb.scale]}
    centers={n:[round(v,4) for v in deformed_center(bpy.data.objects[n],dg)]
             for n in DEFORM if n in bpy.data.objects}
    TRAJ["red"].append([f]+centers.get("Red_Body",[0,0,0]))
    TRAJ["blue"].append([f]+centers.get("Blue_Body",[0,0,0]))
    TRAJ["gift"].append([f]+centers.get("GiftBox_Base",[0,0,0]))
    TRAJ["red_door"].append([f]+centers.get("RedHouse_Door",[0,0,0]))
    TRAJ["blue_door"].append([f]+centers.get("BlueHouse_Door",[0,0,0]))
    FRAMES.append({"frame":f,"camera":scene.camera.name if scene.camera else None,
                   "objects":objs,"bones":bones,"deformed_centers":centers})
    if f%40==0: print("sampled",f,flush=True)

with open(os.path.join(LAB,"animation.json"),"w") as fh:
    json.dump({"fps":FPS,"start":F0,"end":F1,"frames":FRAMES},fh)
with open(os.path.join(LAB,"trajectories.json"),"w") as fh: json.dump(TRAJ,fh)

# visible trajectory ribbons for Red and Blue
def ribbon(name, pts, col):
    cu=bpy.data.curves.new(name+"Data","CURVE"); cu.dimensions="3D"
    cu.bevel_depth,cu.bevel_resolution=0.028,2
    sp=cu.splines.new("POLY"); sp.points.add(len(pts)-1)
    for i,p in enumerate(pts): sp.points[i].co=(p[1],p[2],p[3],1)
    o=bpy.data.objects.new(name,cu); bpy.context.collection.objects.link(o)
    cu.materials.append(base_material(name+" glow",col,0.4,emission=col,strength=1.0))
    o.hide_render=True
    return o
ribbon("Path_Red",TRAJ["red"],(1.0,0.35,0.25))
ribbon("Path_Blue",TRAJ["blue"],(0.25,0.7,1.0))

# ---------------------------------------------------------------------------
# QA — includes the explicit "the arch is rotated, Red passes THROUGH it" check
# ---------------------------------------------------------------------------
def dist(a,b): return math.sqrt(sum((x-y)**2 for x,y in zip(a,b)))
qa={"checks":[],"max_speed":{},"max_accel":{},"cameras":{}}
finite=all(math.isfinite(v) for fr in FRAMES for g in ("objects","bones")
           for rec in fr[g].values() for key in ("location","rotation","scale","head","tail")
           if key in rec for v in rec[key])
qa["checks"].append({"name":"Все координаты конечные","pass":finite,"detail":f"{len(FRAMES)} кадров"})
qa["checks"].append({"name":"Покрытие всеми кадрами","pass":len(FRAMES)==F1-F0+1,
                     "detail":f"{len(FRAMES)}/{F1-F0+1}"})
for label in ("red","blue","gift"):
    pts=[p[1:] for p in TRAJ[label]]
    sp=[dist(pts[i],pts[i-1])*FPS for i in range(1,len(pts))]
    ac=[abs(sp[i]-sp[i-1])*FPS for i in range(1,len(sp))]
    qa["max_speed"][label]=round(max(sp),3); qa["max_accel"][label]=round(max(ac),3) if ac else 0
    qa["checks"].append({"name":f"Непрерывность траектории: {label}","pass":max(sp)<25,
                         "detail":f"max {max(sp):.2f} u/s"})
for fr in FRAMES:
    qa["cameras"][fr["camera"]]=qa["cameras"].get(fr["camera"],0)+1
qa["checks"].append({"name":"5 камерных планов через маркеры","pass":len(qa["cameras"])==5,
                     "detail":str(qa["cameras"])})

# ARCH: correct orientation + real pass-through (the v1 mistake)
inner = ARCH_MAJOR-ARCH_MINOR
cross = min(range(F0,F1+1), key=lambda f: abs(TRAJ["red"][f-1][1]-ARCH_X))
scene.frame_set(cross)
dg=bpy.context.evaluated_depsgraph_get()
ys,zs=[],[]
for n in [o.name for o in RED["parts"]]+["Red_AntennaTip"]:
    o=bpy.data.objects.get(n)
    if not o: continue
    ev=o.evaluated_get(dg); me=ev.to_mesh()
    if me:
        for v in me.vertices:
            w=ev.matrix_world@v.co; ys.append(w.y); zs.append(w.z)
        ev.to_mesh_clear()
worst=max(math.hypot(y-ARCH_Y,z-ARCH_Z) for y,z in zip(ys,zs)) if ys else 999
qa["checks"].append({"name":"Кольцо РАЗВЁРНУТО по оси X: красный проходит СКВОЗЬ арку",
                     "pass":worst<inner,
                     "detail":f"кадр {cross}, макс. радиус робота {worst:.3f} < inner {inner:.3f}, "
                              f"orientation=(0, 90°, 0), hole axis=+X"})
qa["checks"].append({"name":"Дверь красного открыта и НЕ закрыта (забыл)",
                     "pass":abs(RED_DOOR.rotation_euler.z)>1.0,
                     "detail":f"угол {RED_DOOR.rotation_euler.z:.2f} рад на кадре {F1}"})
# blue door was closed at 129 and open by 168
qa["checks"].append({"name":"Дверь синего открывается после стука",
                     "pass":abs(FRAMES[128]["objects"]["BlueHouse_Door"]["rotation"][2])<0.1
                            and abs(FRAMES[167]["objects"]["BlueHouse_Door"]["rotation"][2])>1.0,
                     "detail":"кадр 129 закрыта → кадр 168 открыта"})
# Red passes the blue doorway plane (x = DOOR_BX) moving +X
entered=any(TRAJ["red"][f-1][1]>DOOR_BX+0.25 for f in range(169,205))
qa["checks"].append({"name":"Красный заходит В дверь, а не сквозь стену",
                     "pass":entered,"detail":f"порог x={DOOR_BX:.2f}, внутри x>{DOOR_BX+0.25:.2f}"})
# Gift burst: streamers actually leave the box
burst_max=max(max(fr["objects"][f"Streamer_{i:02d}"]["location"][2] for i in range(54))
              for fr in FRAMES[210:])
qa["checks"].append({"name":"Хлопушка: ленточки вылетают из коробки",
                     "pass":burst_max>2.4 and len(BURST)==90,
                     "detail":f"{len(BURST)} элементов, макс. высота {burst_max:.2f}"})
# IK reach
leg=0.34+0.36
worst_ik=0
for fr in FRAMES:
    for t in ("Red","Blue"):
        for s in ("L","R"):
            worst_ik=max(worst_ik,dist(fr["bones"][f"{t}.Thigh.{s}"]["head"],
                                       fr["bones"][f"{t}.IK.Foot.{s}"]["head"]))
qa["checks"].append({"name":"IK-цели стоп достижимы","pass":worst_ik<=leg+0.25,
                     "detail":f"макс {worst_ik:.3f}, цепь {leg:.2f}"})
# volume preservation
vol=max(abs(math.prod(fr["bones"]["Red.Spine"]["scale"])-1) for fr in FRAMES)
qa["checks"].append({"name":"Squash & stretch сохраняет объём","pass":vol<0.03,
                     "detail":f"макс. ошибка {vol:.4f}"})
# framing of subjects per active camera
SHOT_SUBJECTS = {
 "CamA_Follow": ["Red_Body"],
 "CamB_Window": ["Blue_Body", "Red_Body"],
 "CamC_Door":   ["Red_Body", "Blue_Body"],
 "CamD_Inside": ["Red_Body", "Blue_Body", "GiftBox_Base"],
 "CamE_Gift":   ["Red_Body", "Blue_Body", "GiftBox_Base"],
}
framing=True; worst_ndc=0
for fr in FRAMES:
    scene.frame_set(fr["frame"]); cam=scene.camera
    for n in SHOT_SUBJECTS.get(cam.name, []):
        c=fr["deformed_centers"].get(n)
        if not c: continue
        uv=world_to_camera_view(scene,cam,Vector(c))
        worst_ndc=max(worst_ndc,max(-uv.x,uv.x-1,-uv.y,uv.y-1))
        if not(-0.18<=uv.x<=1.18 and -0.18<=uv.y<=1.18): framing=False
qa["checks"].append({"name":"Герои в кадре на всех планах","pass":framing,
                     "detail":f"макс. выход {worst_ndc:.3f}"})
qa["checks"].append({"name":"Скелеты: кости, IK, веса, визуализаторы",
                     "pass":len(RED["parts"])>=20 and len(BLUE["parts"])>=18 and len(BONEVIZ)>=40,
                     "detail":f"{len(BONES)} костей × 2, {len(SKINNED)} мешей, {len(BONEVIZ)} визуализаторов"})
qa["checks"].append({"name":"Motion Paths рассчитаны в Blender",
                     "pass":any(v=="ok" for v in MP.values()),"detail":str(MP)})

scene.frame_set(F0)

# ---------------------------------------------------------------------------
# Save .blend + meta
# ---------------------------------------------------------------------------
scene.render.engine="CYCLES"; scene.cycles.device="CPU"; scene.cycles.samples=SAMPLES
scene.cycles.use_denoising=True
for a,v in (("use_adaptive_sampling",True),("adaptive_threshold",0.04),("max_bounces",5)):
    if hasattr(scene.cycles,a): setattr(scene.cycles,a,v)
scene.render.resolution_x,scene.render.resolution_y=RES_X,RES_Y
scene.render.resolution_percentage=100
scene.render.threads_mode="FIXED"; scene.render.threads=2
if hasattr(scene.render,"use_motion_blur"):
    scene.render.use_motion_blur=True
    if hasattr(scene.render,"motion_blur_shutter"): scene.render.motion_blur_shutter=0.5
try:
    scene.view_settings.view_transform="AgX"; scene.view_settings.look="AgX - Medium High Contrast"
except Exception: pass
scene.render.image_settings.media_type="VIDEO"
scene.render.image_settings.file_format="FFMPEG"
scene.render.ffmpeg.format="MPEG4"; scene.render.ffmpeg.codec="H264"
scene.render.ffmpeg.constant_rate_factor="HIGH"; scene.render.ffmpeg.ffmpeg_preset="GOOD"
scene.render.filepath="//geo_story_v2.mp4"

SHOTS=[{"frame":f,"camera":k,"name":n} for f,k,n in
       [(1,"A","Красный выходит, забывает дверь"),(89,"B","Синий смотрит в окно"),
        (129,"C","Стук и открытие двери"),(169,"D","Красный заходит внутрь"),
        (205,"E","Подарок и хлопушка")]]
SOURCES=[
 {"title":"12 principles of animation","url":"https://oboe.com/learn/mastering-3d-worlds-with-blender-nwhftu/character-animation-mechanics-ntnkb6","takeaway":"squash/stretch, anticipation, follow-through, arcs, slow in/out, exaggeration"},
 {"title":"Character rigging & IK","url":"https://www.bevelfish.com/blog/blender-character-animation-tutorial","takeaway":"apply transforms, origin at feet, IK for planted feet, key controls, Motion Paths"},
 {"title":"Blender Python animation","url":"https://terminalskills.io/skills/blender-animation","takeaway":"keyframe_insert, BEZIER easing, edit_bones, IK constraints"},
 {"title":"Blender 5.x F-curve API","url":"https://blenderartists.org/t/how-to-access-fcurves-in-blender-5-0/1623022","takeaway":"action_get_channelbag_for_slot instead of Action.fcurves"},
 {"title":"Object Operators / Motion Paths","url":"https://docs.blender.org/api/current/bpy.ops.object.html","takeaway":"paths_calculate(display_type='RANGE', range='SCENE')"},
 {"title":"Blender Render Automation","url":"https://terminalskills.io/skills/blender-render-automation","takeaway":"Cycles CPU reliable headless, media_type='VIDEO' before FFMPEG"},
 {"title":"Procedural shading / bump","url":"https://docs.blender.org/manual/en/latest/render/shader_nodes/textures/index.html","takeaway":"Noise/Brick/Voronoi/Wave + Bump for detailed textures without image files"},
 {"title":"Camera cuts with markers","url":"https://docs.blender.org/manual/en/latest/animation/markers.html","takeaway":"timeline marker .camera binds a shot; scene.camera switches on frame_set"},
]
PRINCIPLES=[
 {"name":"Squash & Stretch","where":"Spine scale, объём сохранён"},
 {"name":"Anticipation","where":"приседание перед выходом и перед стуком"},
 {"name":"Staging","where":"5 камерных планов, маркеры, свет"},
 {"name":"Pose to Pose","where":"ключевые позы походки и эмоций"},
 {"name":"Follow Through","where":"антенна, руки, брови с задержкой"},
 {"name":"Slow In / Slow Out","where":"все F-кривые BEZIER + AUTO_CLAMPED"},
 {"name":"Arcs","where":"изогнутая дорожка, арка, полёт лент"},
 {"name":"Secondary Action","where":"взгляд в окно, жест приветствия, облака"},
 {"name":"Timing","where":"24 fps, 240 кадров, 10 с"},
 {"name":"Exaggeration","where":"хлопушка, удивление, радость"},
 {"name":"Solid Drawing","where":"bevel 4 сегмента + weighted normals, процедурные текстуры"},
 {"name":"Appeal","where":"два разных лица, сердечко, подарок"},
]
meta={
 "blender":bpy.app.version_string,"version":"v2",
 "installer":{"url":"https://github.com/maksummatatov10-spec1231/blender1231/releases/download/install/blender-5.3.0-linux-x64.tar.xz",
              "size":406944100,"sha256":"dacb8264197a3f7fda6001285a5a506fc97ee943881261c2c3bd63c882f22e05"},
 "scene":{"name":scene.name,"fps":FPS,"start":F0,"end":F1,"resolution":[RES_X,RES_Y],
          "engine":"CYCLES","samples":SAMPLES,"denoising":True,"device":"CPU",
          "duration_seconds":round((F1-F0+1)/FPS,2)},
 "output":{"mp4":"geo_story_v2.mp4","blend":"geo_story_v2.blend",
           "frames":"renders/v2/frames/frame_%04d.png",
           "preview":"renders/v2/frames_preview/frame_%04d.jpg",
           "frame_archive":"renders_v2_frames.zip"},
 "story":SHOTS,
 "rigs":{t:{"bones":[{"name":n,"parent":p,"deform":d,"head":list(h),"tail":list(t2)}
                     for n,h,t2,p,d in BONES],
           "skinned_meshes":[o.name for o in R["parts"]]}
         for t,R in (("Red",RED),("Blue",BLUE))},
 "constraints":[{"rig":t,"bone":pb.name,"constraint":c.name,"type":c.type,
                 "subtarget":getattr(c,"subtarget",None),"chain_count":getattr(c,"chain_count",None)}
                for t,R in (("Red",RED),("Blue",BLUE)) for pb in R["rig"].pose.bones for c in pb.constraints],
 "bone_visualizers":[o.name for o in BONEVIZ],
 "arch":{"center":[ARCH_X,ARCH_Y,ARCH_Z],"major":ARCH_MAJOR,"minor":ARCH_MINOR,
         "inner":inner,"rotation":[0,90,0],"hole_axis":"+X",
         "cross_frame":cross,"robot_max_radius":round(worst,3),"passes_through":worst<inner},
 "fcurves":FC,"motion_paths":MP,"principles":PRINCIPLES,"sources":SOURCES,
 "objects_count":len(bpy.data.objects),"qa":qa,
}
with open(os.path.join(LAB,"meta.json"),"w") as fh: json.dump(meta,fh,ensure_ascii=False,indent=1)
with open(os.path.join(LAB,"qa.json"),"w") as fh: json.dump(qa,fh,ensure_ascii=False,indent=1)

# tidy collections
for cname, names in {
 "01 Red robot + rig":[o.name for o in RED["parts"]]+[RED["rig"].name],
 "02 Blue robot + rig":[o.name for o in BLUE["parts"]]+[BLUE["rig"].name],
 "03 Red house":[o.name for o in bpy.data.objects if o.name.startswith("RedHouse") or o.name.startswith("RedFlower")],
 "04 Blue house":[o.name for o in bpy.data.objects if o.name.startswith("BlueHouse")],
 "05 Garden + arch":[o.name for o in bpy.data.objects if o.name.startswith(("Stone_","Tree","Flower","GardenArch","ArchBead","Cloud","Ground","SkyBackdrop","Path"))],
 "06 Gift + burst":[o.name for o in bpy.data.objects if o.name.startswith(("GiftBox","Streamer","Confetti"))],
 "07 Cameras + lights":[o.name for o in bpy.data.objects if o.type in {"CAMERA","LIGHT","EMPTY"}],
 "08 Bone visualizers (hidden)":[o.name for o in BONEVIZ],
}.items():
    col=bpy.data.collections.new(cname); scene.collection.children.link(col)
    for n in names:
        o=bpy.data.objects.get(n)
        if o:
            for old in list(o.users_collection): old.objects.unlink(o)
            col.objects.link(o)

bpy.ops.wm.save_as_mainfile(filepath=os.path.join(ROOT,"geo_story_v2.blend"))
print("BUILD_V2_OK", bpy.app.version_string, "objects", len(bpy.data.objects),
      "fcurves", len(FC), "QA", sum(1 for c in qa["checks"] if c["pass"]),
      "/", len(qa["checks"]), "ARCH", round(worst,3), "<", inner, flush=True)
