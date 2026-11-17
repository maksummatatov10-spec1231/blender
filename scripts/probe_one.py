import bpy, os, sys, addon_utils
engine = sys.argv[sys.argv.index("--") + 1] if "--" in sys.argv else "CYCLES"
print("PROBE_ENGINE", engine, bpy.app.version_string)
try:
    bpy.ops.preferences.addon_enable(module="cycles")
except Exception as e:
    print("cycles addon:", e)
bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
bpy.ops.mesh.primitive_cube_add(size=1.4, location=(0, 0, 0))
cube = bpy.context.object
mat = bpy.data.materials.new("probe_mat")
mat.use_nodes = True
bsdf = mat.node_tree.nodes.get("Principled BSDF")
bsdf.inputs["Base Color"].default_value = (0.9, 0.35, 0.2, 1)
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
scene.render.engine = engine
if engine == "BLENDER_EEVEE":
    scene.eevee.taa_render_samples = 16
elif engine == "CYCLES":
    scene.cycles.samples = 8
    scene.cycles.use_denoising = True
    scene.cycles.device = "CPU"
elif engine == "BLENDER_WORKBENCH":
    scene.display.shading.light = "STUDIO"
    scene.display.shading.color_type = "MATERIAL"
scene.render.resolution_x = 320
scene.render.resolution_y = 180
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
os.makedirs("renders/probe", exist_ok=True)
scene.render.filepath = os.path.abspath(f"renders/probe/probe_{engine}.png")
print("RENDER_START", engine, flush=True)
bpy.ops.render.render(write_still=True)
print("RENDER_OK", engine, os.path.getsize(scene.render.filepath), flush=True)
