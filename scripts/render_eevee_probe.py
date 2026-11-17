import bpy, os, time
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
scene = bpy.context.scene
scene.render.engine = "BLENDER_EEVEE"
scene.eevee.taa_render_samples = 32
if hasattr(scene.eevee, "use_raytracing"):
    scene.eevee.use_raytracing = False
scene.render.image_settings.media_type = "IMAGE"
scene.render.image_settings.file_format = "PNG"
scene.render.resolution_percentage = 100
scene.render.filepath = os.path.join(ROOT, "renders", "probe", "eevee_soft.png")
os.makedirs(os.path.dirname(scene.render.filepath), exist_ok=True)
scene.frame_set(44)
t = time.time()
bpy.ops.render.render(write_still=True)
print("EEVEE_OK", time.time() - t, flush=True)
