# -*- coding: utf-8 -*-
# Финал амбара: доски на крыше и фасаде, забор, покраска всей сцены.
import bpy, bmesh, math
from mathutils import Vector, Matrix

OUT = "/home/user/blender"

def open_scene():
    bpy.ops.wm.open_mainfile(filepath=OUT + "/дз_амбар_окно_ворота.blend")

# ---------------------------------------------------------------- материалы
def set_mat(name, color, rough=0.6, metal=0.0):
    m = bpy.data.materials.get(name)
    if m is None:
        m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    b = nt.nodes.new("ShaderNodeBsdfPrincipled")
    nt.links.new(b.outputs[0], out.inputs["Surface"])
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    return m

def paint_all():
    set_mat("Красная_обшивка", (0.360, 0.028, 0.026), 0.55)
    set_mat("Створки",        (0.300, 0.024, 0.022), 0.6)
    set_mat("Светлое_дерево", (0.830, 0.800, 0.720), 0.5)
    set_mat("Крыша_доски",    (0.110, 0.085, 0.065), 0.7)
    set_mat("Доски_крыши",    (0.085, 0.058, 0.038), 0.85)
    set_mat("Обшивка_доска",  (0.420, 0.040, 0.034), 0.55)
    set_mat("Забор",          (0.800, 0.770, 0.700), 0.55)
    set_mat("Внутри",         (0.160, 0.100, 0.060), 0.8)
    set_mat("Пол",            (0.280, 0.180, 0.100), 0.7)
    set_mat("Сено",           (0.580, 0.430, 0.130), 0.9)
    set_mat("Металл",         (0.080, 0.080, 0.090), 0.35, 1.0)
    zem = set_mat("Земля",    (0.100, 0.260, 0.060), 0.95)
    nt = zem.node_tree
    b = nt.nodes.get("Principled BSDF")
    noise = nt.nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 40.0
    noise.inputs["Detail"].default_value = 6.0
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.25
    nt.links.new(noise.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (0.08, 0.22, 0.05, 1)
    ramp.color_ramp.elements[1].color = (0.16, 0.33, 0.09, 1)
    nt.links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], b.inputs["Base Color"])

# ---------------------------------------------------------------- helpers
def new_obj(name, bm, mat):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    ob.data.materials.append(mat)
    bpy.context.collection.objects.link(ob)
    return ob

def add_box(bm, center, size, mat_rot=None):
    res = bmesh.ops.create_cube(bm, size=1.0)
    verts = res["verts"]
    S = Matrix.Diagonal(Vector((*size, 1.0)))
    M = Matrix.Translation(center) @ ((mat_rot or Matrix.Identity(4)) @ S)
    bmesh.ops.transform(bm, matrix=M, verts=verts)

def slope_frame(a2d, b2d, side):
    A = Vector((a2d[0], 0, a2d[1]))
    B = Vector((b2d[0], 0, b2d[1]))
    d = (B - A).normalized()
    n = Vector((-d.z, 0, d.x))
    if (n.x > 0 and side == "L") or (n.x < 0 and side == "R"):
        n = -n
    return A, B, d, n

def roof_planks(bm, a2d, b2d, side, y0, y1, rows, thick=0.045):
    A, B, d, n = slope_frame(a2d, b2d, side)
    length = y1 - y0
    cy = (y0 + y1) / 2
    for i in range(rows):
        t = (i + 0.5) / rows
        c = A.lerp(B, t) + n * (thick * 0.6)
        rot = Matrix((
            (d.x, 0, n.x, 0),
            (0,   1, 0,   0),
            (d.z, 0, n.z, 0),
            (0, 0, 0, 1)))
        w = (B - A).length / rows * 1.15
        add_box(bm, Vector((c.x, cy, c.z)), (w, length, thick), rot)

def add_roof_boards():
    bm = bmesh.new()
    mat = bpy.data.materials["Доски_крыши"]
    Y0, Y1 = -0.38, 4.73
    roof_planks(bm, (-3.45, 2.30), (-2.10, 4.10), "L", Y0, Y1, 7)
    roof_planks(bm, ( 3.45, 2.30), ( 2.10, 4.10), "R", Y0, Y1, 7)
    roof_planks(bm, (-2.20, 4.12), (-0.02, 5.42), "L", Y0, Y1, 6)
    roof_planks(bm, ( 2.20, 4.12), ( 0.02, 5.42), "R", Y0, Y1, 6)
    roof_planks(bm, (-4.68, 1.45), (-3.16, 2.45), "L", 0.15, 2.90, 5, thick=0.04)
    new_obj("Доски_крыши", bm, mat)

def facade_width(z):
    if z <= 2.37:
        return 6.30
    if z <= 4.14:
        return 6.30 + (4.30 - 6.30) * (z - 2.37) / (4.14 - 2.37)
    if z <= 5.30:
        return 4.30 + (0.30 - 4.30) * (z - 4.14) / (5.30 - 4.14)
    return 0.3

def add_wall_siding():
    bm = bmesh.new()
    mat = bpy.data.materials["Обшивка_доска"]
    z = 0.25
    while z < 5.0:
        w = facade_width(z + 0.14) - 0.55
        if w > 0.5:
            add_box(bm, Vector((0, -0.035, z + 0.14)), (w, 0.05, 0.26))
            add_box(bm, Vector((-0.17, 4.48, z + 0.14)), (w, 0.05, 0.26))
        z += 0.30
    z = 0.25
    while z < 2.3:
        add_box(bm, Vector((-3.24, 2.22, z + 0.14)), (0.05, 4.35, 0.26))
        add_box(bm, Vector(( 3.24, 2.22, z + 0.14)), (0.05, 4.35, 0.26))
        z += 0.30
    new_obj("Обшивка_доски", bm, mat)

def add_fence():
    bm = bmesh.new()
    mat = bpy.data.materials["Забор"]
    H = 1.15
    segments = [
        ((-9.5, -4.6), (-1.8, -4.6)),
        (( 1.8, -4.6), ( 9.5, -4.6)),
        ((-9.5, -4.6), (-9.5, 0.2)),
        (( 9.5, -4.6), ( 9.5, 0.2)),
    ]
    for (ax, ay), (bx, by) in segments:
        A = Vector((ax, ay, 0)); B = Vector((bx, by, 0))
        L = (B - A).length
        dirv = (B - A).normalized()
        nposts = max(2, int(L / 1.9) + 1)
        for i in range(nposts):
            p = A.lerp(B, i / (nposts - 1))
            add_box(bm, p + Vector((0, 0, H / 2 + 0.08)), (0.13, 0.13, H + 0.16))
        for zz in (0.42, 0.86):
            c = (A + B) / 2 + Vector((0, 0, zz))
            ang = math.atan2(dirv.y, dirv.x)
            rot = Matrix.Rotation(ang, 4, 'Z')
            add_box(bm, c, (L, 0.06, 0.10), rot)
        n = int(L / 0.24)
        for i in range(n + 1):
            p = A.lerp(B, i / n)
            add_box(bm, p + Vector((0, 0, H / 2)), (0.035, 0.10, H))
    new_obj("Забор", bm, mat)

def shot(name, loc, target, lens=50):
    cd = bpy.data.cameras.new("cam_" + name)
    cd.lens = lens
    ob = bpy.data.objects.new("cam_" + name, cd)
    bpy.context.collection.objects.link(ob)
    ob.location = loc
    d = Vector(target) - Vector(loc)
    ob.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
    bpy.context.scene.camera = ob

def setup_render():
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    sc.cycles.device = 'CPU'
    sc.cycles.samples = 96
    sc.cycles.use_adaptive_sampling = True
    sc.cycles.adaptive_threshold = 0.03
    sc.cycles.use_denoising = True
    sc.render.resolution_x = 1600
    sc.render.resolution_y = 1000
    try:
        sc.view_settings.view_transform = 'Khronos PBR Neutral'
    except Exception:
        pass
    sc.view_settings.exposure = -0.3
    sun = bpy.data.objects.get("Солнце")
    if sun:
        sun.data.energy = 3.0
        sun.rotation_euler = (math.radians(50), 0, math.radians(-35))
    w = bpy.context.scene.world
    w.use_nodes = True
    nt = w.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputWorld")
    sky = nt.nodes.new("ShaderNodeTexSky")
    try:
        sky.sky_type = 'NISHITA'
        sky.sun_disc = False
        sky.sun_elevation = math.radians(40)
        sky.sun_rotation = math.radians(145)
    except Exception:
        pass
    bg_cam = nt.nodes.new("ShaderNodeBackground")
    bg_cam.inputs["Strength"].default_value = 1.0
    bg_light = nt.nodes.new("ShaderNodeBackground")
    bg_light.inputs["Strength"].default_value = 0.12
    lp = nt.nodes.new("ShaderNodeLightPath")
    mix = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(sky.outputs["Color"], bg_cam.inputs["Color"])
    nt.links.new(sky.outputs["Color"], bg_light.inputs["Color"])
    nt.links.new(lp.outputs["Is Camera Ray"], mix.inputs["Fac"])
    nt.links.new(bg_light.outputs["Background"], mix.inputs[1])
    nt.links.new(bg_cam.outputs["Background"], mix.inputs[2])
    nt.links.new(mix.outputs["Shader"], out.inputs["Surface"])

def main():
    open_scene()
    paint_all()
    add_roof_boards()
    add_wall_siding()
    add_fence()
    setup_render()
    import os
    os.makedirs(OUT + "/картинки", exist_ok=True)
    shots = [
        ("амбар_финал_фасад",  (-8.5, -11.5, 3.4), (0, 0, 2.2), 45),
        ("амбар_финал_бок",    ( 11.5, -7.0, 3.0), (0, 1.5, 2.2), 45),
        ("амбар_финал_общий",  (-13.0, -13.0, 5.5), (0, 0.5, 2.0), 40),
        ("амбар_финал_забор",  ( 3.0, -9.5, 1.8), (-1.0, 0, 1.6), 40),
    ]
    for name, loc, tgt, lens in shots:
        shot(name, loc, tgt, lens)
        bpy.context.scene.render.filepath = OUT + "/картинки/" + name + ".png"
        bpy.ops.render.render(write_still=True)
    bpy.ops.wm.save_as_mainfile(filepath=OUT + "/дз_амбар_финал.blend")
    print("BARN_DONE")

main()
