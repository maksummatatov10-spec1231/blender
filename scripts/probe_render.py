import bpy, os, sys, traceback
print("VERSION", bpy.app.version_string)
print("BUILD_CYCLES", getattr(bpy.app.build_options, "cycles", None))
try:
    import addon_utils
    print("cycles enabled before:", addon_utils.check("cycles"))
    bpy.ops.preferences.addon_enable(module="cycles")
    print("cycles enabled after:", addon_utils.check("cycles"))
except Exception as e:
    print("cycles enable failed:", e)
try:
    ids = [e.identifier for e in bpy.context.scene.render.bl_rna.properties["engine"].enum_items]
    print("ENGINES", ids)
except Exception as e:
    print("engine enum failed:", e)

# minimal scene
bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
bpy.ops.mesh.primitive_cube_add(size=1.4, location=(0, 0, 0))
cube = bpy.context.object
mat = bpy.data.materials.new("probe_mat")
mat.diffuse_color = (0.9, 0.35, 0.2, 1)
mat.use_nodes = True
mat.node_tree.nodes.get("Principled BSDF").inputs["Base Color"].default_value = (0.9, 0.35, 0.2, 1)
cube.data.materials.append(mat)
bpy.ops.object.camera_add(location=(3.2, -4.2, 2.8))
cam = bpy.context.object
cam.rotation_euler = (1.05, 0.0, 0.62)
bpy.context.scene.camera = cam
bpy.ops.object.light_add(type="AREA", location=(1, -2, 4))
bpy.context.object.data.energy = 350
bpy.context.object.data.size = 3
world = bpy.context.scene.world
world.use_nodes = True
world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.05, 0.07, 0.12, 1)
world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.8

scene = bpy.context.scene
scene.render.resolution_x = 320
scene.render.resolution_y = 180
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
os.makedirs("renders/probe", exist_ok=True)

for engine in ("BLENDER_EEVEE", "CYCLES", "BLENDER_WORKBENCH"):
    try:
        scene.render.engine = engine
        if engine == "BLENDER_EEVEE":
            try:
                scene.eevee.taa_render_samples = 16
            except Exception as e:
                print("eevee samples attr:", e)
        if engine == "CYCLES":
            scene.cycles.samples = 8
            scene.cycles.use_denoising = True
            scene.cycles.device = "CPU"
        scene.render.filepath = os.path.abspath(f"renders/probe/probe_{engine}.png")
        print("RENDERING", engine)
        bpy.ops.render.render(write_still=True)
        print("OK", engine, os.path.getsize(scene.render.filepath))
    except Exception as e:
        print("FAIL", engine, repr(e))
        traceback.print_exc()
