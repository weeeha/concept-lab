"""Import the walking-planter construct with Construct's own Blender add-on (headless, nothing installed)
and save walking-planter-construct.blend plus two stills: the hologram and the finished model.

  /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup -P make_blend.py -- <dir holding construct_blender/>

<dir> is where the add-on zip (construct/dist/construct-blender-*.zip) was unpacked as `construct_blender`.
"""
import bpy, os, sys, importlib
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
ext_dir = sys.argv[sys.argv.index("--") + 1]
sys.path.insert(0, ext_dir)
cb = importlib.import_module("construct_blender")
bpy.ops.wm.read_factory_settings(use_empty=True)
cb.register()
root = cb.import_construct(os.path.join(HERE, "walking-planter.scene.json"), metal=1.0)
print("ROOT", root.name, {k: root[k] for k in root.keys() if k in ("build", "open", "metal", "finish", "lines")})

objs = [o for o in bpy.context.scene.objects if o.type == "MESH"]
pts = [o.matrix_world @ Vector(c) for o in objs for c in o.bound_box]
lo = Vector([min(p[i] for p in pts) for i in range(3)]); hi = Vector([max(p[i] for p in pts) for i in range(3)])
ctr = (lo + hi) / 2

scn = bpy.context.scene
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); scn.collection.objects.link(cam); scn.camera = cam
cam.data.lens = 50
cam.location = ctr + Vector((0.58, -0.79, 0.62))
cam.rotation_euler = (ctr - cam.location).to_track_quat("-Z", "Y").to_euler()
for name, off, e, s in (("key", (0.6, -0.6, 1.2), 160, 1.2), ("fill", (-0.8, -0.2, 0.6), 50, 1.5), ("rim", (-0.2, 0.9, 0.8), 90, 0.8)):
    L = bpy.data.objects.new(name, bpy.data.lights.new(name, "AREA")); scn.collection.objects.link(L)
    L.data.energy = e; L.data.size = s; L.location = ctr + Vector(off)
    L.rotation_euler = (ctr - L.location).to_track_quat("-Z", "Y").to_euler()
scn.world = bpy.data.worlds.new("w"); scn.world.use_nodes = True
bg = scn.world.node_tree.nodes["Background"]; bg.inputs["Color"].default_value = (0.05, 0.05, 0.06, 1); bg.inputs["Strength"].default_value = 1.0

engines = [e.identifier for e in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items]
scn.render.engine = "BLENDER_EEVEE_NEXT" if "BLENDER_EEVEE_NEXT" in engines else "BLENDER_EEVEE"
scn.render.resolution_x, scn.render.resolution_y = 1600, 1200
scn.view_settings.view_transform = "AgX" if "AgX" in [v.identifier for v in scn.view_settings.bl_rna.properties["view_transform"].enum_items] else "Filmic"

def still(fname, **props):
    for k, v in props.items():
        if k in root.keys(): root[k] = v
    bpy.context.view_layer.update()
    scn.render.filepath = os.path.join(HERE, "out", fname)
    bpy.ops.render.render(write_still=True)
    print("WROTE", scn.render.filepath)

keys = list(root.keys())
print("CONTROLS", keys)
still("blend-light.png", metal=0.0, finish=0.0)
still("blend-finished.png", metal=1.0, finish=1.0)

bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, "walking-planter-construct.blend"))
print("SAVED")
