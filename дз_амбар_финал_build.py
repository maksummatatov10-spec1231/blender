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
            add_box(bm, Vector((0, 4.485, z + 0.14)), (w, 0.05, 0.26))
        z += 0.30
    z = 0.25
    while z < 2.3:
        add_box(bm, Vector((-3.24, 2.22, z + 0.14)), (0.05, 4.35, 0.26))
        add_box(bm, Vector(( 3.24, 2.22, z + 0.14)), (0.05, 4.35, 0.26))
        z += 0.30
    new_obj("Обшивка_доски", bm, mat)

FRONT_CUTTERS = ["Резак_ворот", "Резак_окна", "Резак_двери"]
BACK_CUTTERS = ["Резак_ворот_сзади", "Резак_окна_сзади"]

def cut_openings():
    # Обшивка закрыла сквозные проёмы базовой сцены — прорезаем её теми же
    # Boolean-резаками, что и фасадную стену (окно, ворота, дверь).
    # ЗАДНЯЯ стена остаётся целой: задние «резаки» из части 2 были нужны
    # только чтобы видеть небо сквозь передние дыры, теперь они не нужны.
    siding = bpy.data.objects.get("Обшивка_доски")
    names = FRONT_CUTTERS
    # у резаков базовой сцены вывернуты нормали — чиним, иначе
    # EXACT-булеан режет криво
    for n in names:
        c = bpy.data.objects.get(n)
        if not c:
            continue
        bm = bmesh.new()
        bm.from_mesh(c.data)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        if bm.calc_volume(signed=True) < 0:
            for f in bm.faces:
                f.normal_flip()
        bm.to_mesh(c.data)
        bm.free()
        c.data.update()
    if siding:
        for n in names:
            c = bpy.data.objects.get(n)
            if c:
                m = siding.modifiers.new("cut_" + n, 'BOOLEAN')
                m.operation = 'DIFFERENCE'
                m.object = c
                m.solver = 'EXACT'
    for n in names:
        c = bpy.data.objects.get(n)
        if c:
            # не hide_render (иначе булеан теряет операнд в рендере),
            # а невидимость для всех лучей
            for attr in ("visible_camera", "visible_diffuse", "visible_glossy",
                         "visible_transmission", "visible_volume_scatter",
                         "visible_shadow"):
                if hasattr(c, attr):
                    setattr(c, attr, False)

def close_back_wall():
    # Задняя стена: убираем два огромных проёма части 2 (Boolean-модификаторы)
    # и удаляем их резаки — стена снова сплошная. Наружная грань — красная,
    # как у фасада и боковых стен.
    wall = bpy.data.objects.get("Стена_задняя")
    if wall:
        wall.modifiers.clear()
        red = bpy.data.materials["Красная_обшивка"]
        wall.data.materials[0] = red
    for n in BACK_CUTTERS:
        c = bpy.data.objects.get(n)
        if c:
            me = c.data
            bpy.data.objects.remove(c, do_unlink=True)
            if me.users == 0:
                bpy.data.meshes.remove(me)

def bake_openings():
    # Запекаем булевы проёмы в меши (стена + обшивка), чтобы рендер
    # гарантированно видел отверстия независимо от депсграфа рендера.
    dg = bpy.context.evaluated_depsgraph_get()
    for n in ["Стена_фасада", "Обшивка_доски"]:
        ob = bpy.data.objects.get(n)
        if not ob or not ob.modifiers:
            continue
        ev = ob.evaluated_get(dg)
        me = bpy.data.meshes.new_from_object(ev)
        old = ob.data
        ob.data = me
        ob.modifiers.clear()
        if old.users == 0:
            bpy.data.meshes.remove(old)
    for n in FRONT_CUTTERS:
        c = bpy.data.objects.get(n)
        if c:
            c.hide_render = True
            c.hide_set(True)

def mirror_to_back(src_name, new_name, a):
    """Копия детали фасада на задний торец: y -> a - y (зеркало), нормали перевёрнуты."""
    src = bpy.data.objects.get(src_name)
    if not src:
        return None
    me = bpy.data.meshes.new(new_name)
    bm = bmesh.new()
    bm.from_mesh(src.data)
    mw = src.matrix_world
    for v in bm.verts:
        w = mw @ v.co
        v.co = Vector((w.x, a - w.y, w.z))
    bmesh.ops.reverse_faces(bm, faces=bm.faces)
    bm.to_mesh(me)
    bm.free()
    for mat in src.data.materials:
        me.materials.append(mat)
    for p in me.polygons:
        p.use_smooth = False
    ob = bpy.data.objects.new(new_name, me)
    for c in src.users_collection:
        c.objects.link(ob)
    ob.parent = src.parent
    return ob

def add_back_trims():
    # Тот же декор, что на фасаде: ветровые доски, колени, заглушка конька,
    # угловые наличники — зеркально на задний торец.
    for n in ["Ветровая_верх_лево", "Ветровая_верх_право",
              "Ветровая_низ_лево", "Ветровая_низ_право",
              "Колено_фасад_лево", "Колено_фасад_право", "Заглушка_конька"]:
        mirror_to_back(n, n.replace("Ветровая", "Ветровая_зад").replace("Колено_фасад", "Колено_зад")
                          .replace("Заглушка_конька", "Заглушка_конька_зад"), 4.33)
    for n in ["Угол_лево", "Угол_право"]:
        mirror_to_back(n, n + "_зад", 4.45)

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
    # задняя стена теперь сплошная — внутри нужен свой свет, иначе сквозь
    # проёмы видна чёрная коробка
    low = bpy.data.objects.get("Свет_внутри")
    if low:
        low.data.energy = 260
        low.data.shadow_soft_size = 0.3
        low.visible_camera = False
    if not bpy.data.objects.get("Свет_сеновал"):
        ld = bpy.data.lights.new("Свет_сеновал", 'POINT')
        ld.energy = 160
        ld.color = (1.0, 0.80, 0.55)
        ld.shadow_soft_size = 0.3
        lo = bpy.data.objects.new("Свет_сеновал", ld)
        bpy.context.scene.collection.objects.link(lo)
        lo.location = (0.0, 2.3, 3.5)
        lo.visible_camera = False
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
    # Небо — стандартное для Blender 5.x («многократное рассеяние»), солнце
    # низко (15°) позади амбара. Именно такой свет был на всех принятых
    # кадрах, поэтому параметры не меняем, а лишь фиксируем явно.
    sky.sky_type = 'MULTIPLE_SCATTERING'
    sky.sun_disc = True
    sky.sun_elevation = math.radians(15)
    sky.sun_rotation = 0.0
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

def check_back_wall():
    """Лучи с тыла по всей ширине: должны упираться в заднюю стену/обшивку,
    а не уходить внутрь амбара."""
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    ok = True
    pts = [(-2.6, 0.5), (-1.0, 0.5), (0.0, 0.5), (1.0, 0.5), (2.6, 0.5),
           (-2.6, 1.6), (0.0, 1.6), (2.6, 1.6),
           (-1.6, 3.0), (0.0, 3.0), (1.6, 3.0),
           (-1.0, 4.3), (0.0, 4.3), (1.0, 4.3),
           (0.0, 4.9)]
    for x, z in pts:
        hit, loc, nrm, idx, ob, mw = bpy.context.scene.ray_cast(
            dg, Vector((x, 9.0, z)), Vector((0, -1, 0)), distance=20)
        name = ob.name if ob else None
        good = bool(ob) and ob.name in ("Обшивка_доски", "Стена_задняя") and loc.y > 4.2
        ok = ok and good
        print("  back ray x=%5.2f z=%4.2f -> %-16s y=%.3f %s" % (x, z, name, loc.y if hit else -99, "ok" if good else "!!!"))
    print("BACK_WALL_CLOSED" if ok else "BACK_WALL_HAS_HOLES")
    # а передние проёмы по-прежнему сквозные
    for label, (x, z) in {"ворота": (0.0, 1.1), "окно": (0.0, 3.1), "дверь": (-2.08, 0.9)}.items():
        hit, loc, nrm, idx, ob, mw = bpy.context.scene.ray_cast(
            dg, Vector((x, -3.5, z)), Vector((0, 1, 0)), distance=20)
        print("  front", label, "->", ob.name if ob else None, "y=%.2f" % (loc.y if hit else -99),
              "OPEN" if (ob and loc.y > 0.5) else "BLOCKED")
    return ok

def main():
    import os
    mode = os.environ.get("BARN_MODE", "final")
    open_scene()
    paint_all()
    add_roof_boards()
    add_wall_siding()
    cut_openings()
    close_back_wall()
    bake_openings()
    add_back_trims()
    add_fence()
    setup_render()
    check_back_wall()
    sc = bpy.context.scene
    sc["версия"] = "v3: задняя стена на месте (сплошная, с обшивкой); проёмы фасада сквозные"
    EXP = -0.3
    shots = [
        # имя, камера, цель, фокус, экспозиция
        ("амбар_финал_фасад",     (-8.5, -11.5, 3.4), (0, 0, 2.2),      45, EXP),
        ("амбар_финал_бок",       ( 11.5, -7.0, 3.0), (0, 1.5, 2.2),    45, EXP),
        ("амбар_финал_общий",     (-13.0, -13.0, 5.5), (0, 0.5, 2.0),   40, EXP),
        ("амбар_финал_забор",     ( 3.0, -9.5, 1.8), (-1.0, 0, 1.6),    40, EXP),
        # задние кадры: низкое солнце стоит сзади и бьёт в заднюю стену —
        # экспозицию на кадр убавляем, чтобы стена не пересвечивалась
        ("амбар_финал_зад",       ( 5.0, 11.2, 3.0), (-0.4, 4.0, 2.5),  30, -0.9),
        ("амбар_финал_зад_слева", (-7.5, 10.5, 5.5), (0.0, 3.0, 2.6),   32, -0.9),
    ]
    only = [x for x in os.environ.get("BARN_ONLY", "").split(",") if x]
    cams = {}
    for name, loc, tgt, lens, ex in shots:
        shot(name, loc, tgt, lens)
        cams[name] = sc.camera
    if mode == "preview":
        sc.render.resolution_x, sc.render.resolution_y = 800, 500
        sc.cycles.samples = 24
        outdir = "/tmp/prev"
    else:
        outdir = OUT + "/картинки"
    os.makedirs(outdir, exist_ok=True)
    for name, loc, tgt, lens, ex in shots:
        if only and name not in only:
            continue
        sc.camera = cams[name]
        sc.view_settings.exposure = ex
        sc.render.filepath = outdir + "/" + name + ".png"
        bpy.ops.render.render(write_still=True)
        print("RENDERED", name, flush=True)
    sc.view_settings.exposure = EXP
    sc.camera = cams["амбар_финал_общий"]
    if mode != "preview":
        bpy.ops.wm.save_as_mainfile(filepath=OUT + "/дз_амбар_финал.blend")
    else:
        bpy.ops.wm.save_as_mainfile(filepath="/tmp/prev/preview.blend")
    print("BARN_DONE")

main()
