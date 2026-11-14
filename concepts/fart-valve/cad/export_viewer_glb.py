# Exports the Fart Valve only (no desk, console, headphones, props, lights or cameras) for the site's 3D viewer.
# Front (the ring face) faces +X in the GLB. Cartridge installed, cheeks open (the state saved in the .blend).
# Run: Blender -b blender/fart_valve.blend -P cad/export_viewer_glb.py
# (build_fart_valve.py writes the same file at the end of a full build; this script re-exports from the saved .blend.)
import bpy, os
here = os.path.dirname(bpy.data.filepath)
skip = ("desk", "bench", "kcaps", "fader", "cut_mat", "studio", "console", "headphone", "hp_", "mould", "spare", "hexkey", "screw", "c_", "pp_tmp", "plane", "camera")
keep_empties = ("cartridge", "cheek_L", "cheek_R")
def flat(src):
    n = bpy.data.materials.new("viewer_" + src.name); n.use_nodes = True
    b0 = src.node_tree.nodes["Principled BSDF"]; b = n.node_tree.nodes["Principled BSDF"]
    for k in ("Base Color", "Roughness", "Metallic"):
        b.inputs[k].default_value = b0.inputs[k].default_value
    if b0.inputs["Emission Strength"].default_value > 0:
        b.inputs["Emission Color"].default_value = b0.inputs["Emission Color"].default_value
        b.inputs["Emission Strength"].default_value = min(1.0, b0.inputs["Emission Strength"].default_value)
    if "Tray_clear" in src.name:
        b.inputs["Alpha"].default_value = 0.28; b.inputs["Base Color"].default_value = (0.8, 0.9, 0.95, 1)
        for a, v in (("surface_render_method", "BLENDED"), ("blend_method", "BLEND")):
            try: setattr(n, a, v)
            except Exception: pass
    return n
cache = {}
bpy.ops.object.select_all(action="DESELECT")
names = []
for o in bpy.context.scene.objects:
    n = o.name.lower()
    if o.type == "MESH" and not any(k in n for k in skip) and not n.startswith("viewer_"):
        for i, m in enumerate(o.data.materials):
            if m and not m.name.startswith("viewer_"):
                cache.setdefault(m.name, flat(m)); o.data.materials[i] = cache[m.name]
        o.select_set(True); names.append(o.name)
    elif o.type == "EMPTY" and o.name in keep_empties:
        o.select_set(True)
assert not any("kcaps" in n.lower() or "console" in n.lower() or "desk" in n.lower() or "hp_" in n.lower() for n in names), "set dressing in export"
assert not any("mast" in n.lower() for n in names), "mast object in export"
print("EXPORT", len(names), sorted(names))
out = os.path.join(os.path.dirname(here), "render", "model.glb") if os.path.basename(here) == "blender" else os.path.join(here, "model.glb")
bpy.ops.export_scene.gltf(filepath=out, use_selection=True, export_apply=True, export_format="GLB",
                          export_draco_mesh_compression_enable=False, export_yup=True)
print("GLB %.2f MB" % (os.path.getsize(out) / 1e6))
