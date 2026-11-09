"""Bambu Lab P1S, built by hand in Blender (the 'hand' half of ../BRIEF.md).

  /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup -P build_p1s.py

Writes p1s-hand.blend and p1s-hand.glb beside this file. Blender frame: Z up, front -Y, millimetres
converted at the end (MM). Outer size, build volume from the brief; every other size is estimated.
Frame 1 is closed; frame 60 has the door and lid open.
"""
import bpy, math, os
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
MM = 0.001
W, D, H = 389.0, 389.0, 458.0          # outer, from the brief
BUILD = 256.0                          # build volume edge, from the brief
POST = 22.0                            # corner post section (estimate)
BASE_Z = 90.0                          # top of the base (estimate)
RIM = 22.0                             # top frame depth (estimate)
GLASS = 4.0

bpy.ops.wm.read_factory_settings(use_empty=True)
scn = bpy.context.scene

def mat(name, rgb, rough=0.5, metal=0.0, trans=0.0):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*rgb, 1); b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    if trans:
        b.inputs["Transmission Weight"].default_value = trans; b.inputs["IOR"].default_value = 1.5
    if name in ("glass", "PTFE"):                      # see-through in Eevee and in the glTF (alpha blend)
        b.inputs["Alpha"].default_value = 0.18 if name == "glass" else 0.6
        if hasattr(m, "surface_render_method"): m.surface_render_method = "BLENDED"
        else: m.blend_method = "BLEND"
    return m

M = dict(
    frame=mat("frame dark grey", (0.03, 0.03, 0.035), 0.45),
    base=mat("base grey", (0.06, 0.06, 0.065), 0.55),
    glass=mat("glass", (0.85, 0.9, 0.92), 0.05, trans=1.0),
    screen=mat("screen", (0.01, 0.015, 0.02), 0.15),
    button=mat("button", (0.5, 0.5, 0.52), 0.4),
    bed=mat("PEI plate", (0.55, 0.45, 0.25), 0.6, 0.3),
    rail=mat("rail steel", (0.7, 0.7, 0.72), 0.25, 1.0),
    head=mat("toolhead", (0.8, 0.8, 0.8), 0.4),
    brass=mat("nozzle brass", (0.75, 0.55, 0.2), 0.3, 1.0),
    rubber=mat("rubber", (0.02, 0.02, 0.02), 0.9),
    filament=mat("filament orange", (0.9, 0.35, 0.05), 0.35),
    spool=mat("spool cardboard", (0.55, 0.42, 0.28), 0.8),
    ptfe=mat("PTFE", (0.95, 0.95, 0.95), 0.3, trans=0.3),
)

def box(name, sx, sy, sz, cx, cy, z0, m, parent=None):
    bpy.ops.mesh.primitive_cube_add(size=1, location=(cx * MM, cy * MM, (z0 + sz / 2) * MM))
    o = bpy.context.active_object; o.name = name; o.scale = (sx * MM, sy * MM, sz * MM)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    o.data.materials.append(m)
    if parent: reparent(o, parent)
    return o

def cyl(name, r, h, loc, m, axis="z", verts=32, parent=None):
    rot = {"z": (0, 0, 0), "x": (0, math.pi / 2, 0), "y": (math.pi / 2, 0, 0)}[axis]
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=r * MM, depth=h * MM, location=[v * MM for v in loc], rotation=rot)
    o = bpy.context.active_object; o.name = name
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)
    o.data.materials.append(m); bpy.ops.object.shade_smooth()
    if parent: reparent(o, parent)
    return o

def reparent(o, parent):
    mw = o.matrix_world.copy(); o.parent = parent; o.matrix_world = mw

def empty(name, loc):
    e = bpy.data.objects.new(name, None); scn.collection.objects.link(e); e.location = [v * MM for v in loc]; return e

hx, hy = W / 2, D / 2

# ---- feet and base ----
for sx in (-1, 1):
    for sy in (-1, 1):
        cyl("foot", 16, 10, (sx * (hx - 35), sy * (hy - 35), 5), M["rubber"])
box("base", W, D, BASE_Z - 10, 0, 0, 10, M["base"])
# front screen and five buttons, bottom left of the front
box("screen", 62, 1.5, 34, -hx + 75, -hy - 0.5, 35, M["screen"])
for i in range(5):
    cyl("button", 4.5, 3, (-hx + 125 + i * 13, -hy - 1.5, 52), M["button"], axis="y", verts=20)

# ---- frame: posts and top rim ----
for sx in (-1, 1):
    for sy in (-1, 1):
        box("post", POST, POST, H - BASE_Z, sx * (hx - POST / 2), sy * (hy - POST / 2), BASE_Z, M["frame"])
box("rim-front", W, POST, RIM, 0, -hy + POST / 2, H - RIM, M["frame"])
box("rim-back", W, POST, RIM, 0, hy - POST / 2, H - RIM, M["frame"])
for sx in (-1, 1):
    box("rim-side", POST, D, RIM, sx * (hx - POST / 2), 0, H - RIM, M["frame"])

# ---- side glass and back panel ----
ph = H - RIM - BASE_Z
for sx in (-1, 1):
    box("side-glass", GLASS, D - 2 * POST, ph, sx * (hx - POST / 2), 0, BASE_Z, M["glass"])
box("back-panel", W - 2 * POST, 3, ph, 0, hy - 3, BASE_Z, M["frame"])

# ---- front door, hinged on its left edge ----
door_w, door_h = W - 2 * POST + 10, ph + 10
hinge_d = empty("door-hinge", (-hx + POST - 5, -hy - GLASS / 2 - 1, 0))
box("door-glass", door_w, GLASS, door_h, -hx + POST - 5 + door_w / 2, -hy - GLASS / 2 - 1, BASE_Z - 5, M["glass"], hinge_d)
box("door-handle", 10, 14, 120, -hx + POST - 5 + door_w - 22, -hy - GLASS - 8, BASE_Z + ph / 2 - 60, M["frame"], hinge_d)

# ---- top lid, hinged at the back ----
lid_w, lid_d = W - 2 * POST + 6, D - 2 * POST + 6
hinge_l = empty("lid-hinge", (0, hy - POST + 3, H))
box("lid-glass", lid_w, lid_d, GLASS, 0, 0, H - GLASS / 2, M["glass"], hinge_l)

# ---- bed on two Z lead screws at the back corners ----
bed_z = 260.0
box("bed-plate", BUILD + 10, BUILD + 10, 6, 0, -8, bed_z, M["bed"])
box("bed-frame", BUILD + 30, 24, 14, 0, BUILD / 2 + 10, bed_z - 14, M["frame"])   # rear crossbar carrying the bed
for sx in (-1, 1):
    cyl("z-screw", 4, H - RIM - BASE_Z - 10, (sx * 140, 150, BASE_Z + (H - RIM - BASE_Z - 10) / 2), M["rail"], verts=16)
    box("bed-arm", 20, BUILD - 20, 10, sx * 120, 20, bed_z - 12, M["frame"])

# ---- CoreXY gantry at the top: two Y rails, one X rail, toolhead ----
gz = H - RIM - 40
for sx in (-1, 1):
    box("y-rail", 14, D - 2 * POST, 14, sx * (hx - POST - 12), 0, gz, M["rail"])
tx, ty = 40.0, -30.0
box("x-rail", W - 2 * POST - 24, 16, 18, 0, ty, gz - 2, M["rail"])
box("toolhead", 58, 52, 72, tx, ty - 26, gz - 52, M["head"])
box("toolhead-fan", 40, 4, 40, tx, ty - 52, gz - 40, M["frame"])
bpy.ops.mesh.primitive_cone_add(vertices=16, radius1=3 * MM, radius2=0.6 * MM, depth=8 * MM, location=(tx * MM, (ty - 26) * MM, (gz - 56) * MM), rotation=(math.pi, 0, 0))
noz = bpy.context.active_object; noz.name = "nozzle"; noz.data.materials.append(M["brass"])

# ---- spool holder on the back, spool, PTFE tube to the top ----
sz_ = 300.0
cyl("spool-arm", 8, 80, (60, hy + 40, sz_), M["frame"], axis="y", verts=20)
cyl("spool", 100, 66, (60, hy + 50, sz_), M["spool"], axis="y", verts=64)
cyl("filament", 92, 58, (60, hy + 50, sz_), M["filament"], axis="y", verts=64)
cu = bpy.data.curves.new("ptfe", "CURVE"); cu.dimensions = "3D"
sp = cu.splines.new("BEZIER"); sp.bezier_points.add(1)
p0, p1 = Vector((60, hy + 50, sz_ + 100)), Vector((60, hy - 10, H + 2))
for bp, p, hnd in ((sp.bezier_points[0], p0, Vector((0, 0, 90))), (sp.bezier_points[1], p1, Vector((0, 60, 40)))):
    bp.co = p * MM; bp.handle_left = (p - hnd) * MM; bp.handle_right = (p + hnd) * MM
cu.bevel_depth = 2.0 * MM; cu.bevel_resolution = 4
tube = bpy.data.objects.new("ptfe-tube", cu); scn.collection.objects.link(tube); tube.data.materials.append(M["ptfe"])

# ---- open animation: frame 1 closed, frame 60 open ----
for e, axis, ang in ((hinge_d, 2, -100), (hinge_l, 0, -60)):   # lid swings up and back
    e.rotation_euler = (0, 0, 0); e.keyframe_insert("rotation_euler", frame=1)
    r = [0, 0, 0]; r[axis] = math.radians(ang); e.rotation_euler = r; e.keyframe_insert("rotation_euler", frame=60)
scn.frame_start, scn.frame_end = 1, 60
scn.frame_set(1)

parts = [o for o in scn.objects if o.type in ("MESH", "CURVE")]
print("PARTS", len(parts))
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, "p1s-hand.blend"))
bpy.ops.export_scene.gltf(filepath=os.path.join(HERE, "p1s-hand.glb"), export_animations=True, export_apply=True)
print("WROTE")
