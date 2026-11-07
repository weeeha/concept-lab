# Exports the robot only (no dock, cable, ground, lights or cameras) for the site's 3D viewer.
# Run: Blender -b blender/robot-planter.blend -P cad/export_viewer_glb.py
import bpy, os
here = os.path.dirname(bpy.data.filepath)
skip = ("dock", "spring", "battery_tray", "ramp", "cable", "contact", "led", "ground", "wall", "fence", "floor", "lawn", "patio", "tile", "window", "plane")
names = []
for o in bpy.context.scene.objects:
    o.select_set(False)
    n = o.name.lower()
    if o.type == "MESH" and not any(k in n for k in skip) and o.visible_get():
        o.select_set(True); names.append(o.name)
def flat(name, rgb, rough=0.6):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes.get("Principled BSDF")
    b.inputs["Base Color"].default_value = (*rgb, 1.0)
    b.inputs["Roughness"].default_value = rough
    return m
# Procedural node materials do not survive glTF export; give the viewer flat ones.
leaf = flat("viewer_leaf", (0.10, 0.32, 0.07), 0.45)
stem = flat("viewer_stem", (0.22, 0.42, 0.12))
eye = flat("viewer_eye", (0.03, 0.03, 0.03), 0.8)
dome = flat("viewer_dome", (0.87, 0.89, 0.90), 0.4)
chip = flat("viewer_chip", (0.08, 0.09, 0.10), 0.5)
for n in names:
    o = bpy.data.objects[n]
    k = o.name.lower()
    m = leaf if k.startswith("leaf") else stem if k.startswith(("petiole", "stem")) else eye if k.startswith("eye_face") else dome if k.startswith("sensor_dome") else chip if k.startswith("sensor_chip") else None
    if m:
        o.data.materials.clear(); o.data.materials.append(m)
assert not any("mast" in n.lower() or "light_head" in n.lower() for n in names), "mast object in export"
print("EXPORT", len(names), sorted(names))
bpy.ops.export_scene.gltf(filepath=os.path.join(here, "robot-planter-viewer.glb"), use_selection=True,
                          export_apply=True, export_format="GLB", export_yup=True)
