"""Render any P1S .glb from one fixed camera and light rig, closed and open.

  Blender -b --factory-startup -P render_same.py -- model.glb out_prefix
writes out_prefix-closed.png and out_prefix-open.png
"""
import bpy, os, sys, math
from mathutils import Vector

glb, prefix = sys.argv[sys.argv.index("--") + 1:][:2]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=glb)
scn = bpy.context.scene

# same frame for both: fit the model's bounds to the origin, floor at z = 0
objs = [o for o in scn.objects if o.type == "MESH"]
pts = [o.matrix_world @ Vector(c) for o in objs for c in o.bound_box]
lo = Vector([min(p[i] for p in pts) for i in range(3)]); hi = Vector([max(p[i] for p in pts) for i in range(3)])
print("BOUNDS_MM", [round(v * 1000) for v in lo], [round(v * 1000) for v in hi])
ctr = Vector((0, 0, 0.23))

bpy.ops.mesh.primitive_plane_add(size=8, location=(0, 0, lo.z))
fm = bpy.data.materials.new("floor"); fm.use_nodes = True
fm.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.6, 0.6, 0.62, 1)
bpy.context.active_object.data.materials.append(fm)

cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); scn.collection.objects.link(cam); scn.camera = cam
cam.data.lens = 45
cam.location = Vector((0.75, -1.15, 0.78))
cam.rotation_euler = (ctr - cam.location).to_track_quat("-Z", "Y").to_euler()
for name, loc, e, s in (("key", (1.2, -1.0, 1.6), 380, 1.5), ("fill", (-1.4, -0.6, 0.9), 140, 2.0), ("rim", (-0.4, 1.4, 1.3), 220, 1.2)):
    L = bpy.data.objects.new(name, bpy.data.lights.new(name, "AREA")); scn.collection.objects.link(L)
    L.data.energy = e; L.data.size = s; L.location = loc
    L.rotation_euler = (ctr - L.location).to_track_quat("-Z", "Y").to_euler()
scn.world = bpy.data.worlds.new("w"); scn.world.use_nodes = True
scn.world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.32, 0.33, 0.35, 1)
engines = [e.identifier for e in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items]
scn.render.engine = "BLENDER_EEVEE_NEXT" if "BLENDER_EEVEE_NEXT" in engines else "BLENDER_EEVEE"
scn.render.resolution_x, scn.render.resolution_y = 1200, 1200

# Blender's glTF importer makes one glTF animation active and stashes the rest in NLA: play them all
for o in scn.objects:
    ad = o.animation_data
    if ad and not ad.action:
        strips = [s for t in ad.nla_tracks for s in t.strips]
        if strips:
            ad.action = strips[0].action
            for t in list(ad.nla_tracks): ad.nla_tracks.remove(t)
ends = [o.animation_data.action.frame_range[1] for o in scn.objects if o.animation_data and o.animation_data.action]
starts = [o.animation_data.action.frame_range[0] for o in scn.objects if o.animation_data and o.animation_data.action]
print("ANIM", len(ends), "actions", (min(starts) if starts else None), (max(ends) if ends else None))
for label, fr in (("closed", int(min(starts)) if starts else 1), ("open", int(max(ends)) if ends else 1)):
    scn.frame_set(fr)
    scn.render.filepath = os.path.abspath(prefix + "-" + label + ".png")
    bpy.ops.render.render(write_still=True)
    print("WROTE", scn.render.filepath)
