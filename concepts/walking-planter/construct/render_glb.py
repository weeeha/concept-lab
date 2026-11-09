"""Studio render of Construct's GLB export, for a side-by-side with render/assembly-hero.png.

  /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup -P render_glb.py
"""
import bpy, math, os
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=os.path.join(HERE, "out", "walking-planter.glb"))

# glTF is Y-up, front +Z; Blender's importer turns that into Z-up, front -Y.
objs = [o for o in bpy.context.scene.objects if o.type == "MESH"]
lo = Vector((min(v[i] for o in objs for v in (o.matrix_world @ Vector(c) for c in o.bound_box)) for i in range(3)))
hi = Vector((max(v[i] for o in objs for v in (o.matrix_world @ Vector(c) for c in o.bound_box)) for i in range(3)))
ctr = (lo + hi) / 2
print("BOUNDS", lo, hi)

clay = bpy.data.materials.new("clay"); clay.use_nodes = True
clay.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.78, 0.78, 0.8, 1)
clay.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.55
for o in objs:
    o.data.materials.clear(); o.data.materials.append(clay)

bpy.ops.mesh.primitive_plane_add(size=6, location=(ctr.x, ctr.y, lo.z))
floor = bpy.context.active_object
fm = bpy.data.materials.new("floor"); fm.use_nodes = True
fm.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.85, 0.85, 0.86, 1)
floor.data.materials.append(fm)

scn = bpy.context.scene
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); scn.collection.objects.link(cam); scn.camera = cam
cam.data.lens = 50
# three-quarter from the front-right and above, like assembly-hero.png; front is -Y after import
d = 1.05
cam.location = ctr + Vector((0.55 * d, -0.75 * d, 0.62 * d))
cam.rotation_euler = (ctr - cam.location).to_track_quat("-Z", "Y").to_euler()

sun = bpy.data.objects.new("key", bpy.data.lights.new("key", "AREA")); scn.collection.objects.link(sun)
sun.data.energy = 220; sun.data.size = 1.2; sun.location = ctr + Vector((0.6, -0.6, 1.2))
sun.rotation_euler = (ctr - sun.location).to_track_quat("-Z", "Y").to_euler()
fill = bpy.data.objects.new("fill", bpy.data.lights.new("fill", "AREA")); scn.collection.objects.link(fill)
fill.data.energy = 80; fill.data.size = 1.5; fill.location = ctr + Vector((-0.8, -0.2, 0.6))
fill.rotation_euler = (ctr - fill.location).to_track_quat("-Z", "Y").to_euler()
scn.world = bpy.data.worlds.new("w"); scn.world.use_nodes = True
scn.world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.35, 0.36, 0.38, 1)

scn.render.engine = "BLENDER_EEVEE_NEXT" if "BLENDER_EEVEE_NEXT" in [e.identifier for e in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items] else "BLENDER_EEVEE"
scn.render.resolution_x, scn.render.resolution_y = 1600, 1200
scn.render.filepath = os.path.join(HERE, "out", "glb-in-blender.png")
bpy.ops.render.render(write_still=True)
print("WROTE", scn.render.filepath)
