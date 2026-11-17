import bpy, sys
from bpy_extras import anim_utils
print("VERSION", bpy.app.version_string)
print("anim_utils has action_get_channelbag_for_slot:", hasattr(anim_utils, "action_get_channelbag_for_slot"))
print("image_settings.media_type:", hasattr(bpy.context.scene.render.image_settings, "media_type"))
try:
    print("media_type items:", [i.identifier for i in bpy.context.scene.render.image_settings.bl_rna.properties["media_type"].enum_items])
except Exception as e:
    print("media_type enum err:", e)
print("eevee attrs:", [a for a in ("taa_render_samples", "taa_samples", "use_raytracing", "motion_blur_shutter", "motion_blur_steps") if hasattr(bpy.context.scene.eevee, a)])
print("paths_calculate doc:", bpy.ops.object.paths_calculate.get_rna_type().description)
print("paths_calculate props:", [(p.identifier, getattr(p, "default", None)) for p in bpy.ops.object.paths_calculate.get_rna_type().properties])
try:
    print("pose.paths_calculate props:", [p.identifier for p in bpy.ops.pose.paths_calculate.get_rna_type().properties])
except Exception as e:
    print("pose paths err:", e)
# action slot test
bpy.ops.mesh.primitive_cube_add()
o = bpy.context.object
o.location = (1, 2, 3)
o.keyframe_insert(data_path="location", frame=1)
o.location = (4, 5, 6)
o.keyframe_insert(data_path="location", frame=10)
ad = o.animation_data
print("action:", ad.action.name, "slot:", getattr(ad, "action_slot", "NO SLOT"))
try:
    cb = anim_utils.action_get_channelbag_for_slot(ad.action, ad.action_slot)
    print("channelbag:", cb, "fcurves:", len(cb.fcurves) if cb else None)
    for fc in cb.fcurves[:4]:
        print("  fc", fc.data_path, fc.array_index, len(fc.keyframe_points))
except Exception as e:
    print("channelbag err:", repr(e))
try:
    print("action.layers:", len(ad.action.layers))
    for layer in ad.action.layers:
        for strip in layer.strips:
            print(" strip type", strip.type, "channelbags", len(strip.channelbags))
except Exception as e:
    print("layers err:", repr(e))
print("ffmpeg preset items:", [i.identifier for i in bpy.context.scene.render.ffmpeg.bl_rna.properties["ffmpeg_preset"].enum_items])
print("crf items:", [i.identifier for i in bpy.context.scene.render.ffmpeg.bl_rna.properties["constant_rate_factor"].enum_items])
