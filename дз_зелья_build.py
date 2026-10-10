# -*- coding: utf-8 -*-
# Домашнее задание №1: три зелья.
# Сосуд и пробка — поверхности вращения из кривых (профиль + Screw),
# жидкость — отдельное тело вращения по внутренней полости сосуда.
import bpy, math, os
from mathutils import Vector

OUT = os.path.dirname(os.path.abspath(__file__))

def smooth(a, b, t):
    t = max(0.0, min(1.0, (t - a) / (b - a)))
    return t * t * (3 - 2 * t)

def mix(a, b, t):
    return a + (b - a) * t

# ---------------------------------------------------------------- радиусы тел
def radius_A(z):
    """Круглая колба с длинным горлом."""
    R, cz = 0.95, 0.95
    if z <= 0.0:
        return 0.0
    if z < 1.55:
        d = z - cz
        r = math.sqrt(max(0.0, R * R - d * d))
        return max(r, 0.001)
    # плавный переход в горло
    t = smooth(1.55, 1.85, z)
    neck = mix(0.30, 0.24, smooth(1.85, 2.6, z))
    base = 0.30
    r = mix(base, neck, t)
    # раструб устья
    r += 0.06 * smooth(2.45, 2.6, z)
    return r

def radius_B(z):
    """Коническая колба (Эрленмейер)."""
    if z < 0.12:
        return mix(0.55, 0.85, smooth(0.0, 0.12, z))
    if z < 1.5:
        return mix(0.85, 0.24, smooth(0.12, 1.5, z))
    if z < 2.1:
        return 0.24 - 0.02 * smooth(1.5, 2.1, z)
    return 0.22 + 0.06 * smooth(2.0, 2.15, z)

def radius_C(z):
    """Высокая бутыль с плечиками."""
    if z < 0.1:
        return mix(0.4, 0.62, smooth(0.0, 0.1, z))
    if z < 1.7:
        return 0.62 - 0.04 * smooth(0.1, 1.7, z)
    if z < 2.3:
        return mix(0.58, 0.20, smooth(1.7, 2.3, z))
    if z < 2.95:
        return 0.20
    return 0.20 + 0.05 * smooth(2.85, 3.0, z)

POTIONS = [
    dict(name="zelye_green",  rf=radius_A, top=2.6,  fill=1.35, glass_t=0.05,
         liquid=(0.13, 0.75, 0.38), x=-2.6),
    dict(name="zelye_pink",   rf=radius_B, top=2.15, fill=0.75, glass_t=0.05,
         liquid=(0.88, 0.22, 0.34), x=0.0),
    dict(name="zelye_amber",  rf=radius_C, top=3.0,  fill=1.55, glass_t=0.05,
         liquid=(0.93, 0.62, 0.13), x=2.6),
]

# ---------------------------------------------------------------- материалы
def _refr(m):
    # чтобы стекло/жидкость преломлялись и в EEVEE-превью, не только в Cycles
    for attr in ("use_raytrace_refraction", "use_screen_refraction"):
        try:
            setattr(m, attr, True)
        except Exception:
            pass

def mat_glass():
    m = bpy.data.materials.new("Glass")
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (0.9, 0.95, 0.95, 1)
    b.inputs["Roughness"].default_value = 0.03
    b.inputs["Transmission Weight"].default_value = 1.0
    b.inputs["IOR"].default_value = 1.45
    _refr(m)
    return m

def mat_liquid(col):
    m = bpy.data.materials.new("Liquid")
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*col, 1)
    b.inputs["Roughness"].default_value = 0.05
    b.inputs["Transmission Weight"].default_value = 1.0
    b.inputs["IOR"].default_value = 1.34
    # лёгкое свечение — зелье «светится» в любом превью
    b.inputs["Emission Color"].default_value = (*col, 1)
    b.inputs["Emission Strength"].default_value = 0.15
    _refr(m)
    return m

def mat_cork():
    m = bpy.data.materials.new("Cork")
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (0.45, 0.26, 0.11, 1)
    b.inputs["Roughness"].default_value = 0.6
    return m

# ---------------------------------------------------------------- построение
def make_profile_curve(name, pts):
    cu = bpy.data.curves.new(name, 'CURVE')
    cu.dimensions = '3D'
    sp = cu.splines.new('POLY')
    sp.points.add(len(pts) - 1)
    for i, (r, z) in enumerate(pts):
        sp.points[i].co = (r, 0.0, z, 1.0)
    ob = bpy.data.objects.new(name, cu)
    bpy.context.collection.objects.link(ob)
    return ob

def screw_to_mesh(ob, steps=96):
    mod = ob.modifiers.new("Screw", 'SCREW')
    mod.axis = 'Z'
    mod.angle = math.tau
    mod.steps = steps
    mod.render_steps = steps
    mod.use_merge_vertices = True
    mod.merge_threshold = 1e-4
    mod.use_normal_calculate = True
    mod.use_smooth_shade = True
    bpy.context.view_layer.objects.active = ob
    for o in bpy.context.selected_objects:
        o.select_set(False)
    ob.select_set(True)
    bpy.ops.object.convert(target='MESH')
    ob = bpy.context.view_layer.objects.active
    import bmesh
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(ob.data)
    bm.free()
    return ob

def smooth_obj(ob, angle=40):
    for o in bpy.context.selected_objects:
        o.select_set(False)
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.shade_smooth()
    try:
        bpy.ops.object.shade_auto_smooth(angle=math.radians(angle))
    except Exception:
        pass

def build_vessel(P, glass):
    rf, top, t = P["rf"], P["top"], P["glass_t"]
    n = 110
    outer = [(0.0, 0.0)]
    zs = [top * i / n for i in range(1, n + 1)]
    for z in zs:
        outer.append((rf(z), z))
    inner = []
    zi = top
    while zi > 0.14:
        r = max(rf(zi) - t, 0.001)
        inner.append((r, zi))
        zi -= top / (n * 1.1)
    inner.append((max(rf(0.14) - t, 0.001), 0.14))
    inner.append((0.0, 0.14))
    pts = outer + inner
    ob = make_profile_curve(P["name"] + "_vessel", pts)
    ob = screw_to_mesh(ob)
    ob.data.materials.append(glass)
    smooth_obj(ob)
    return ob

def build_liquid(P, lm):
    rf, top, t = P["rf"], P["top"], P["glass_t"]
    fill = P["fill"]
    floor = 0.16
    n = 80
    pts = [(0.0, floor)]
    z = floor
    while z < fill:
        pts.append((max(rf(z) - t * 0.5, 0.001), z))  # чуть врезается в стекло
        z += (fill - floor) / n
    pts.append((max(rf(fill) - t * 0.5, 0.001), fill))
    pts.append((0.0, fill))
    ob = make_profile_curve(P["name"] + "_liquid", pts)
    ob = screw_to_mesh(ob)
    ob.data.materials.append(lm)
    smooth_obj(ob)
    return ob

def build_cork(P, cm):
    rf, top = P["rf"], P["top"]
    neck_r = rf(top - 0.05) - 0.05
    # пробка: ножка в горло + шляпка-головка
    pts = [(0.0, top - 0.5)]
    pts.append((neck_r + 0.01, top - 0.5))
    pts.append((neck_r + 0.01, top - 0.02))
    pts.append((neck_r + 0.12, top + 0.02))   # буртик
    pts.append((neck_r + 0.14, top + 0.10))
    # головка
    h = 0.55
    for i in range(1, 25):
        a = i / 24.0
        r = (neck_r + 0.14) * math.sqrt(max(0.0, 1 - a * a)) * 1.05
        pts.append((max(r, 0.001), top + 0.10 + h * a))
    pts.append((0.0, top + 0.10 + h))
    ob = make_profile_curve(P["name"] + "_cork", pts)
    ob = screw_to_mesh(ob)
    ob.data.materials.append(cm)
    smooth_obj(ob)
    return ob

# ---------------------------------------------------------------- сцена
def build_scene():
    # очистка
    bpy.ops.wm.read_factory_settings(use_empty=True)
    glass = mat_glass()
    cork = mat_cork()

    for P in POTIONS:
        lm = mat_liquid(P["liquid"])
        v = build_vessel(P, glass)
        l = build_liquid(P, lm)
        c = build_cork(P, cork)
        for ob in (v, l, c):
            ob.location.x = P["x"]

    # пол
    bpy.ops.mesh.primitive_plane_add(size=40)
    floor = bpy.context.active_object
    fm = bpy.data.materials.new("Floor")
    fm.use_nodes = True
    b = fm.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (0.28, 0.28, 0.29, 1)
    b.inputs["Roughness"].default_value = 0.5
    floor.data.materials.append(fm)

    # свет
    def area(name, loc, rot, size, power, color=(1, 1, 1)):
        d = bpy.data.lights.new(name, 'AREA')
        d.size = size
        d.energy = power
        d.color = color
        o = bpy.data.objects.new(name, d)
        o.location = loc
        o.rotation_euler = rot
        bpy.context.collection.objects.link(o)
        return o
    area("key",  (-4, -5, 6), (math.radians(45), 0, math.radians(-35)), 6, 900)
    area("fill", (5, -6, 3),  (math.radians(70), 0, math.radians(40)), 5, 350, (1, 0.95, 0.9))
    area("rim",  (0, 6, 5),   (math.radians(-50), 0, 0), 4, 600, (0.9, 0.95, 1))

    w = bpy.data.worlds.new("World")
    w.use_nodes = True
    w.node_tree.nodes["Background"].inputs[0].default_value = (0.05, 0.05, 0.06, 1)
    bpy.context.scene.world = w

    # камера
    cam_d = bpy.data.cameras.new("Cam")
    cam_d.lens = 62
    cam = bpy.data.objects.new("Cam", cam_d)
    bpy.context.collection.objects.link(cam)
    bpy.context.scene.camera = cam

    # рендер
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    sc.cycles.device = 'CPU'
    # EEVEE-превью у пользователя тоже должно преломлять стекло
    for attr, val in (("use_raytracing", True), ("use_ssr", True), ("use_ssr_refraction", True)):
        try:
            setattr(sc.eevee, attr, val)
        except Exception:
            pass
    sc.cycles.samples = 64
    sc.cycles.use_adaptive_sampling = True
    sc.cycles.adaptive_threshold = 0.05
    sc.cycles.use_denoising = True
    sc.cycles.max_bounces = 12
    sc.cycles.transmission_bounces = 12
    sc.cycles.transparent_max_bounces = 12
    sc.render.resolution_x = 1280
    sc.render.resolution_y = 800
    try:
        sc.view_settings.view_transform = 'Khronos PBR Neutral'
    except Exception:
        sc.view_settings.view_transform = 'Standard'
    return cam

def aim(cam, loc, target):
    cam.location = loc
    d = Vector(target) - Vector(loc)
    cam.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()

def main():
    cam = build_scene()
    os.makedirs(os.path.join(OUT, "картинки"), exist_ok=True)
    sc = bpy.context.scene
    # общий план
    if not os.environ.get("SKIP_GROUP"):
        cam.data.lens = 50
        aim(cam, (0, -12.5, 3.1), (0, 0, 1.55))
        sc.render.filepath = os.path.join(OUT, "картинки", "зелья_все.png")
        bpy.ops.render.render(write_still=True)
    # крупные планы
    for P in POTIONS:
        cam.data.lens = 40
        aim(cam, (P["x"] + 1.2, -7.8, max(P["top"] * 0.62, 1.8)), (P["x"], 0, P["top"] * 0.52))
        sc.render.filepath = os.path.join(OUT, "картинки", P["name"] + ".png")
        bpy.ops.render.render(write_still=True)
    # в сохранённом файле камера — общий план
    cam.data.lens = 50
    aim(cam, (0, -12.5, 3.1), (0, 0, 1.55))
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "дз_зелья.blend"))
    print("POTIONS_DONE")

main()
