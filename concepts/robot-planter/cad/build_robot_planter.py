"""Robot planter (Concept) - parametric printed parts + assembly + renders.

Run headless:
  /Applications/Blender.app/Contents/MacOS/Blender -b -P build_robot_planter.py -- [--engine cycles|eevee] [--samples 128] [--no-render]

All lengths are metres (Blender units). STLs are exported scaled x1000, so they open in
millimetres in a slicer. Outputs go next to this folder: ../cad, ../blender, ../render.
"""
import bpy, bmesh, math, os, sys, time, random
from mathutils import Vector

# ----------------------------------------------------------------------------------------
# Dimensions (metres). Change here and re-run.
# ----------------------------------------------------------------------------------------
D = dict(
    # bought parts (stand-ins)
    chassis=(0.200, 0.150, 0.070), chassis_corner_r=0.030, chassis_ground_gap=0.020,
    wheel_d=0.065, wheel_w=0.026, wheel_x=0.070,
    pi=(0.085, 0.056, 0.020), pi_y=-0.045,
    battery=(0.155, 0.048, 0.040), battery_y=0.040,
    pot_bottom_d=0.110, pot_top_d=0.150, pot_h=0.130, pot_wall=0.003, pot_base=0.004,
    # shell ring + cradle (printed)
    shell_od=0.240, shell_wall=0.003, shell_h=0.110, shell_z0=0.030,   # wall bottom in world z
    deck_t=0.006, pot_clear=0.0015, collar_h=0.040, collar_t=0.004,
    wheel_arch_extra=0.010, post_r=0.006, post_hole_r=0.00125,
    # sensor mast (printed)
    mast_od=0.020, mast_wall=0.002, mast_h=0.180, hood_d=0.050, hood_h=0.020,
    mast_flange_d=0.040, mast_flange_t=0.004, mast_x=0.095,
    # dock ramp (printed)
    ramp_w=0.220, ramp_l=0.120, ramp_rise=0.025,
    holder=(0.020, 0.016, 0.012), holder_hole_d=0.008, holder_y=0.030, holder_x=0.088,
    # battery tray (printed)
    tray_wall=0.003, tray_floor=0.003, tray_wall_h=0.022, tray_clear=0.001,
    strap_slot=(0.004, 0.036), strap_x=0.045,
)
OUT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CAD, BLEND, RENDER = (os.path.join(OUT, n) for n in ("cad", "blender", "render"))

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
def arg(name, default):
    return argv[argv.index(name) + 1] if name in argv else default
ENGINE = arg("--engine", "cycles")
SAMPLES = int(arg("--samples", "128"))
DO_RENDER = "--no-render" not in argv

# ----------------------------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------------------------
def active(o):
    bpy.ops.object.select_all(action="DESELECT")
    o.select_set(True)
    bpy.context.view_layer.objects.active = o

def apply_xf(o):
    active(o)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

def cyl(name, r, h, x=0, y=0, z0=0, verts=96, rot=None):
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=r, depth=h, location=(x, y, z0 + h / 2))
    o = bpy.context.active_object; o.name = name
    if rot: o.rotation_euler = rot
    apply_xf(o); return o

def cone(name, r1, r2, h, x=0, y=0, z0=0, verts=96):
    bpy.ops.mesh.primitive_cone_add(vertices=verts, radius1=r1, radius2=r2, depth=h, location=(x, y, z0 + h / 2))
    o = bpy.context.active_object; o.name = name; apply_xf(o); return o

def box(name, sx, sy, sz, x=0, y=0, z0=0, rot=None):
    bpy.ops.mesh.primitive_cube_add(size=1, location=(x, y, z0 + sz / 2))
    o = bpy.context.active_object; o.name = name; o.scale = (sx, sy, sz)
    if rot: o.rotation_euler = rot
    apply_xf(o); return o

def boolean(target, tool, op="DIFFERENCE", delete=True):
    m = target.modifiers.new("bool", "BOOLEAN")
    m.object = tool; m.operation = op; m.solver = "EXACT"
    active(target)
    bpy.ops.object.modifier_apply(modifier=m.name)
    if delete:
        bpy.data.objects.remove(tool, do_unlink=True)
    return target

def union(target, *tools):
    for t in tools: boolean(target, t, "UNION")
    return target

def cut(target, *tools):
    for t in tools: boolean(target, t, "DIFFERENCE")
    return target

def bevel(o, width, segments=2, angle=35):
    m = o.modifiers.new("bev", "BEVEL")
    m.width = width; m.segments = segments; m.limit_method = "ANGLE"; m.angle_limit = math.radians(angle)
    active(o); bpy.ops.object.modifier_apply(modifier=m.name)

def smooth(o, angle=35):
    active(o)
    for op in ("shade_smooth_by_angle", "shade_auto_smooth"):
        try:
            getattr(bpy.ops.object, op)(angle=math.radians(angle)); return
        except Exception:
            pass
    bpy.ops.object.shade_smooth()

def cyl_between(name, p0, p1, r, verts=16):
    p0, p1 = Vector(p0), Vector(p1)
    d = p1 - p0
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=r, depth=d.length, location=(p0 + p1) / 2)
    o = bpy.context.active_object; o.name = name
    o.rotation_mode = "QUATERNION"; o.rotation_quaternion = Vector((0, 0, 1)).rotation_difference(d)
    o.rotation_mode = "XYZ"; apply_xf(o); return o

def make_mat(name, rgb, rough=0.5, metal=0.0, spec=0.5):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*rgb, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    for k in ("Specular IOR Level", "Specular"):
        if k in b.inputs: b.inputs[k].default_value = spec; break
    return m

def assign(o, m):
    o.data.materials.clear(); o.data.materials.append(m)

def srgb(h):
    c = [int(h[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    lin = lambda v: v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4
    return tuple(lin(v) for v in c)

# ----------------------------------------------------------------------------------------
# Reset scene
# ----------------------------------------------------------------------------------------
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.unit_settings.system = "METRIC"; scene.unit_settings.scale_length = 1.0

def pot_r(h):  # outer pot radius at height h above pot bottom
    return D["pot_bottom_d"] / 2 + (D["pot_top_d"] - D["pot_bottom_d"]) / 2 * h / D["pot_h"]

# ----------------------------------------------------------------------------------------
# Printed part 1: shell ring + pot cradle  (local z=0 is wall bottom)
# ----------------------------------------------------------------------------------------
def build_shell():
    R = D["shell_od"] / 2; wall = D["shell_wall"]; H = D["shell_h"]; dt = D["deck_t"]
    shell = cyl("shell_ring_cradle", R, H)
    cut(shell, cyl("_in", R - wall, H + 0.02, z0=-0.01))
    # deck plate (top of ring)
    deck_top = H + 0.002
    union(shell, cyl("_deck", R, dt, z0=deck_top - dt))
    # tapered collar that grips the pot
    ph = D["collar_h"]; ct = D["collar_t"]
    r_in0 = pot_r(0) + D["pot_clear"]; r_in1 = pot_r(ph) + D["pot_clear"]
    collar = cone("_collar", r_in0 + ct, r_in1 + ct, ph, z0=deck_top)
    union(shell, collar)
    cut(shell, cone("_cbore", r_in0, r_in1, ph + 0.004, z0=deck_top - 0.002 + 0.002) )
    # drain / cable openings through deck inside the collar
    cut(shell, cyl("_drain", 0.028, 0.05, z0=deck_top - 0.03))
    # screw posts down to the chassis top (2.5 mm pilot holes)
    chassis_top_local = D["chassis_ground_gap"] + D["chassis"][2] - D["shell_z0"]
    for px, py in ((0.09, -0.05), (-0.09, -0.05), (-0.09, 0.0), (0.0, 0.0)):
        post = cyl("_post", D["post_r"], deck_top - dt / 2 - chassis_top_local, x=px, y=py, z0=chassis_top_local)
        union(shell, post)
        cut(shell, cyl("_ph", D["post_hole_r"], 0.02, x=px, y=py, z0=chassis_top_local - 0.002, verts=16))
    # wheel arches
    wr = D["wheel_d"] / 2 + D["wheel_arch_extra"] / 2 + 0.002
    az = D["wheel_d"] / 2 - D["shell_z0"]
    for sx in (1, -1):
        for sy in (1, -1):
            cut(shell, cyl("_arch", wr, 0.07, x=sx * D["wheel_x"], y=sy * 0.115, z0=az - 0.035,
                           rot=(math.pi / 2, 0, 0), verts=64))
    # hole for the mast cable
    cut(shell, cyl("_mh", 0.007, 0.04, x=D["mast_x"], y=0, z0=deck_top - 0.03, verts=32))
    # four mast flange screw holes
    for a in range(4):
        ang = math.pi / 4 + a * math.pi / 2
        cut(shell, cyl("_sh", 0.0016, 0.02, x=D["mast_x"] + 0.0145 * math.cos(ang), y=0.0145 * math.sin(ang),
                       z0=deck_top - 0.012, verts=16))
    # slots around the rim of the deck for rain run-off / lifting
    for ang in [math.radians(v) for v in (60, 120, 240, 300)]:
        rr = 0.098
        cut(shell, box("_sl", 0.026, 0.006, 0.03, x=rr * math.cos(ang), y=rr * math.sin(ang), z0=deck_top - 0.02,
                       rot=(0, 0, ang + math.pi / 2)))
    bevel(shell, 0.0012); smooth(shell)
    return shell

# ----------------------------------------------------------------------------------------
# Printed part 2: sensor mast with rain hood (local z=0 is flange bottom)
# ----------------------------------------------------------------------------------------
def build_mast():
    ro = D["mast_od"] / 2; ri = ro - D["mast_wall"]; h = D["mast_h"]; ft = D["mast_flange_t"]
    mast = cyl("sensor_mast", ro, h, verts=64)
    union(mast, cyl("_fl", D["mast_flange_d"] / 2, ft, verts=64))
    # fillet-ish cone at base
    union(mast, cone("_fc", D["mast_flange_d"] / 2 - 0.004, ro, 0.012, z0=ft, verts=64))
    # rain hood: hollow cone cap
    hr = D["hood_d"] / 2; hh = D["hood_h"]
    hood = cone("_hood", hr, ro * 0.6, hh, z0=h - 0.006, verts=64)
    union(mast, hood)
    cut(mast, cone("_hc", hr - 0.0025, 0.002, hh - 0.003, z0=h - 0.006 - 0.0001, verts=64))
    # hollow bore for wiring
    cut(mast, cyl("_bore", ri, h - 0.014, z0=-0.001, verts=64))
    # ultrasonic head: block with two 16 mm eyes facing +x (forward)
    zc = 0.060
    union(mast, box("_hs", 0.024, 0.050, 0.024, x=ro + 0.004, z0=zc - 0.012))
    for sy in (1, -1):
        cut(mast, cyl("_eye", 0.0082, 0.04, x=ro + 0.006, y=sy * 0.013, z0=zc - 0.02, rot=(0, math.pi / 2, 0), verts=48))
    # light sensor window facing +x higher up the tube
    cut(mast, box("_win", 0.04, 0.010, 0.010, x=ro, z0=0.130))
    bevel(mast, 0.0008); smooth(mast)
    return mast

# ----------------------------------------------------------------------------------------
# Printed part 3: dock ramp with two contact holders (local origin at low-end centre on ground)
# ----------------------------------------------------------------------------------------
def hull_obj(name, pts):
    bm = bmesh.new()
    vs = [bm.verts.new(p) for p in pts]
    bmesh.ops.convex_hull(bm, input=vs)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); bpy.context.collection.objects.link(o); return o

def build_ramp():
    w = D["ramp_w"] / 2; L = D["ramp_l"]; rise = D["ramp_rise"]
    ramp = hull_obj("dock_ramp", [(0, -w, 0), (L, -w, 0), (L, -w, rise), (0, -w, 0.003),
                                  (0, w, 0), (L, w, 0), (L, w, rise), (0, w, 0.003)])
    slope = math.atan2(rise - 0.003, L)
    # side rails
    for s in (1, -1):
        y0, y1 = (s * (w - 0.007), s * w)
        union(ramp, hull_obj("_rail", [(0, y0, 0.003), (L, y0, rise), (0, y1, 0.003), (L, y1, rise),
                                       (0, y0, 0.012), (L, y0, rise + 0.012), (0, y1, 0.012), (L, y1, rise + 0.012)]))
    # backstop wall
    union(ramp, box("_bs", 0.006, D["ramp_w"], 0.014, x=L - 0.003, z0=rise))
    # contact holders (blocks aligned to the slope)
    hx, hy, hz = D["holder"]
    for s in (1, -1):
        x = D["holder_x"]; zsurf = 0.003 + (rise - 0.003) * x / L
        blk = box("_h", hx, hy, hz + 0.004, x=x, y=s * D["holder_y"], z0=zsurf - 0.004, rot=(0, -slope, 0))
        union(ramp, blk)
        # spring-contact bore, perpendicular to the slope
        axis = Vector((math.sin(slope), 0, math.cos(slope)))
        base = Vector((x, s * D["holder_y"], zsurf)) + axis * 0.004
        cut(ramp, cyl_between("_hole", base - axis * 0.012, base + axis * 0.022, D["holder_hole_d"] / 2, verts=32))
        # M3 clamp screw holes from the front face
        cut(ramp, cyl("_cs", 0.0016, 0.05, x=x - 0.012, y=s * D["holder_y"], z0=zsurf + 0.004 - 0.025, verts=16,
                      rot=(0, math.pi / 2 - slope, 0)))
    bevel(ramp, 0.0015); smooth(ramp)
    return ramp

# ----------------------------------------------------------------------------------------
# Printed part 4: battery tray (local z=0 is underside)
# ----------------------------------------------------------------------------------------
def build_tray():
    bx, by, bz = D["battery"]; c = D["tray_clear"]; w = D["tray_wall"]; f = D["tray_floor"]; wh = D["tray_wall_h"]
    cx, cy = bx + 2 * c, by + 2 * c
    ox, oy = cx + 2 * w, cy + 2 * w
    tray = box("battery_tray", ox, oy, f + wh)
    cut(tray, box("_cav", cx, cy, wh + 0.01, z0=f))
    # finger scoops in both long walls
    for s in (1, -1):
        cut(tray, cyl("_sc", 0.013, 0.02, x=0, y=s * (cy / 2 + w / 2), z0=f + wh - 0.012,
                      rot=(math.pi / 2, 0, 0), verts=48))
    # strap slots through the floor + channels on the underside
    sw, sl = D["strap_slot"]
    for s in (1, -1):
        sx = s * D["strap_x"]
        cut(tray, box("_ss", sw, sl, 0.02, x=sx, z0=-0.005))
        cut(tray, box("_ch", sw + 0.006, oy + 0.02, 0.002, x=sx, z0=-0.0005))
    # mounting ears with M3 holes
    for sx in (1, -1):
        ear = box("_ear", 0.012, 0.030, f, x=sx * (ox / 2 + 0.004), y=0)
        union(tray, ear)
        cut(tray, cyl("_eh", 0.0017, 0.02, x=sx * (ox / 2 + 0.005), y=0, z0=-0.005, verts=24))
    bevel(tray, 0.001); smooth(tray)
    return tray

# ----------------------------------------------------------------------------------------
# Build + export printed parts (each at its local origin)
# ----------------------------------------------------------------------------------------
t0 = time.time()
parts = {"shell_ring_cradle": build_shell(), "sensor_mast": build_mast(),
         "dock_ramp": build_ramp(), "battery_tray": build_tray()}

def export_stl(o, fname):
    active(o)
    path = os.path.join(CAD, fname)
    try:
        bpy.ops.wm.stl_export(filepath=path, export_selected_objects=True, global_scale=1000.0,
                              apply_modifiers=True)
    except AttributeError:
        bpy.ops.export_mesh.stl(filepath=path, use_selection=True, global_scale=1000.0)
    return path

stats = {}
for name, o in parts.items():
    export_stl(o, name.replace("_", "-") + ".stl")
    bb = [Vector(c) for c in o.bound_box]
    dims = [max(v[i] for v in bb) - min(v[i] for v in bb) for i in range(3)]
    stats[name] = (len(o.data.polygons), [round(d * 1000, 1) for d in dims])
print("PARTS", stats, "t=%.1fs" % (time.time() - t0))

# ----------------------------------------------------------------------------------------
# Materials
# ----------------------------------------------------------------------------------------
M = dict(
    shell=make_mat("PETG_white", srgb("#D4D4CE"), 0.5, 0.0, 0.4),
    chassis=make_mat("Chassis_grey", srgb("#3A3C40"), 0.55, 0.3),
    rubber=make_mat("Rubber_black", srgb("#121212"), 0.85, 0.0, 0.2),
    hub=make_mat("Hub_alu", srgb("#8C8F94"), 0.35, 0.8),
    pot=make_mat("Terracotta", srgb("#B8613E"), 0.75, 0.0, 0.3),
    soil=make_mat("Soil", srgb("#3A2A1E"), 0.95, 0.0, 0.1),
    leaf=make_mat("Leaf_green", srgb("#3F8F3A"), 0.55, 0.0, 0.4),
    leaf2=make_mat("Leaf_green_light", srgb("#6FB546"), 0.55, 0.0, 0.4),
    stem=make_mat("Stem", srgb("#4C7A33"), 0.6),
    pi=make_mat("Pi_board", srgb("#1F6B3A"), 0.5, 0.0),
    batt=make_mat("Battery_blue", srgb("#24408A"), 0.5),
    ground=make_mat("Ground", srgb("#605F5B"), 0.9, 0.0, 0.0),
)
for o in parts.values(): assign(o, M["shell"])

# ----------------------------------------------------------------------------------------
# Assembly: stand-ins and placement
# ----------------------------------------------------------------------------------------
bought = []
cx, cy, cz = D["chassis"]; gap = D["chassis_ground_gap"]
# chassis: box with rounded vertical corners
bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0)
for v in bm.verts: v.co.x *= cx; v.co.y *= cy; v.co.z *= cz
vedges = [e for e in bm.edges if abs(e.verts[0].co.z - e.verts[1].co.z) > 1e-6]
bmesh.ops.bevel(bm, geom=vedges, offset=D["chassis_corner_r"], segments=8, affect="EDGES", profile=0.5)
me = bpy.data.meshes.new("chassis"); bm.to_mesh(me); bm.free()
chassis = bpy.data.objects.new("chassis_standin", me); bpy.context.collection.objects.link(chassis)
chassis.location = (0, 0, gap + cz / 2); apply_xf(chassis); bevel(chassis, 0.002, 2, 40); smooth(chassis)
assign(chassis, M["chassis"]); bought.append(chassis)
# wheels
wr = D["wheel_d"] / 2
for sx in (1, -1):
    for sy in (1, -1):
        y = sy * (cy / 2 + D["wheel_w"] / 2 - 0.0015)
        bpy.ops.mesh.primitive_cylinder_add(vertices=64, radius=wr, depth=D["wheel_w"],
                                            location=(sx * D["wheel_x"], y, wr), rotation=(math.pi / 2, 0, 0))
        w = bpy.context.active_object; w.name = "wheel"; apply_xf(w); bevel(w, 0.003, 3, 40); smooth(w)
        assign(w, M["rubber"]); bought.append(w)
        bpy.ops.mesh.primitive_cylinder_add(vertices=32, radius=0.017, depth=D["wheel_w"] + 0.004,
                                            location=(sx * D["wheel_x"], y, wr), rotation=(math.pi / 2, 0, 0))
        hub = bpy.context.active_object; hub.name = "hub"; apply_xf(hub); smooth(hub)
        assign(hub, M["hub"]); bought.append(hub)
top = gap + cz
# Pi
px, py, pz = D["pi"]
pi = box("pi_standin", px, py, pz, x=0, y=D["pi_y"], z0=top); bevel(pi, 0.0015); smooth(pi)
assign(pi, M["pi"]); bought.append(pi)
# battery (sits in the tray)
bx, by, bz = D["battery"]
tray = parts["battery_tray"]
tray.location = (0, D["battery_y"], top)
batt = box("battery_standin", bx, by, bz, x=0, y=D["battery_y"], z0=top + D["tray_floor"] + 0.0005)
bevel(batt, 0.003, 3, 40); smooth(batt); assign(batt, M["batt"]); bought.append(batt)
# shell
shell = parts["shell_ring_cradle"]; shell.location = (0, 0, D["shell_z0"])
deck_top_world = D["shell_z0"] + D["shell_h"] + 0.002
# pot (hollow tapered) sits on the deck
pot_z0 = deck_top_world
pot = cone("pot", D["pot_bottom_d"] / 2, D["pot_top_d"] / 2, D["pot_h"], z0=pot_z0, verts=96)
inner = cone("_pi", D["pot_bottom_d"] / 2 - D["pot_wall"], D["pot_top_d"] / 2 - D["pot_wall"],
             D["pot_h"] - D["pot_base"] + 0.001, z0=pot_z0 + D["pot_base"], verts=96)
cut(pot, inner)
rim = bpy.ops.mesh.primitive_torus_add(major_radius=D["pot_top_d"] / 2 - 0.0005, minor_radius=0.0045,
                                       major_segments=96, minor_segments=16,
                                       location=(0, 0, pot_z0 + D["pot_h"] - 0.0045))
rim = bpy.context.active_object; rim.name = "_rim"; union(pot, rim); smooth(pot); assign(pot, M["pot"])
bought.append(pot)
# soil disc
soil_top = pot_z0 + D["pot_h"] - 0.020
soil = cyl("soil", pot_r(soil_top - pot_z0) - D["pot_wall"] - 0.0005, 0.012, z0=soil_top - 0.012, verts=64)
smooth(soil); assign(soil, M["soil"]); bought.append(soil)
# plant
random.seed(7)
stem_base = Vector((0, 0, soil_top - 0.001))
leaves = []
def add_leaf(pos, size, tilt_z, mat):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=3, radius=size, location=pos)
    o = bpy.context.active_object; o.name = "leaf"
    o.scale = (1.0, 0.55, 0.18); o.rotation_euler = (random.uniform(-0.5, 0.5), random.uniform(-0.6, 0.2), tilt_z)
    apply_xf(o); smooth(o); assign(o, mat); leaves.append(o)
stems = [((0, 0, 0.095), 0.0022), ((0.018, 0.006, 0.075), 0.0018), ((-0.017, -0.008, 0.07), 0.0018),
         ((0.004, -0.02, 0.06), 0.0016), ((-0.005, 0.019, 0.055), 0.0016)]
for i, (tip, r) in enumerate(stems):
    p1 = stem_base + Vector(tip)
    s = cyl_between("stem", stem_base, p1, r, 12); assign(s, M["stem"]); bought.append(s)
    for k in range(3):
        t = 0.55 + 0.22 * k
        pos = stem_base + Vector(tip) * t
        ang = random.uniform(0, math.tau)
        add_leaf(pos + Vector((0.016 * math.cos(ang), 0.016 * math.sin(ang), 0.0)), 0.026 - 0.003 * k, ang,
                 M["leaf"] if (i + k) % 2 else M["leaf2"])
    add_leaf(p1 + Vector((0, 0, 0.006)), 0.022, random.uniform(0, math.tau), M["leaf2"])
bought += leaves
# mast
mast = parts["sensor_mast"]; mast.location = (D["mast_x"], 0, deck_top_world)
# ramp behind robot, low end towards the robot
ramp = parts["dock_ramp"]; ramp.rotation_euler = (0, 0, math.pi); ramp.location = (-0.185, 0, 0)

# ground
bpy.ops.mesh.primitive_plane_add(size=40, location=(0, 0, 0))
ground = bpy.context.active_object; ground.name = "ground"; assign(ground, M["ground"])

# ----------------------------------------------------------------------------------------
# Lights, world, camera
# ----------------------------------------------------------------------------------------
def area(name, loc, target, energy, size, color=(1, 1, 1)):
    bpy.ops.object.light_add(type="AREA", location=loc)
    l = bpy.context.active_object; l.name = name; l.data.energy = energy; l.data.size = size; l.data.color = color
    d = Vector(target) - Vector(loc); l.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    return l
tgt = (0.0, 0.0, 0.15)
area("key", (0.35, -0.9, 1.1), tgt, 60, 0.6, (1.0, 0.96, 0.9))
area("fill", (-0.9, -0.6, 0.4), tgt, 14, 1.2, (0.88, 0.93, 1.0))
area("rim", (-0.5, 0.9, 0.7), tgt, 40, 0.5, (1, 1, 1))
w = bpy.data.worlds.new("World"); scene.world = w; w.use_nodes = True
bg = w.node_tree.nodes["Background"]; bg.inputs["Color"].default_value = (0.30, 0.32, 0.36, 1); bg.inputs["Strength"].default_value = 0.6

bpy.ops.object.camera_add()
cam = bpy.context.active_object; cam.name = "camera"; scene.camera = cam
cam.data.lens = 50; cam.data.sensor_width = 36; cam.data.clip_end = 20
def aim(loc, target):
    cam.location = loc
    cam.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
aim((0.62, -0.74, 0.15), (-0.045, 0.0, 0.16))

scene.render.resolution_x, scene.render.resolution_y = 1600, 1200
scene.render.image_settings.file_format = "PNG"
scene.view_settings.exposure = -0.4
for vt in ("Khronos PBR Neutral", "AgX", "Standard"):
    try: scene.view_settings.view_transform = vt; break
    except TypeError: pass

# ----------------------------------------------------------------------------------------
# Save blend + GLB (assembly, stand-ins + printed parts, ground and lights excluded from GLB)
# ----------------------------------------------------------------------------------------
os.makedirs(BLEND, exist_ok=True); os.makedirs(RENDER, exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(BLEND, "robot-planter.blend"))
bpy.ops.object.select_all(action="DESELECT")
for o in list(parts.values()) + bought: o.select_set(True)
bpy.ops.export_scene.gltf(filepath=os.path.join(BLEND, "robot-planter.glb"), export_format="GLB",
                          use_selection=True, export_draco_mesh_compression_enable=False, export_apply=True)
print("SAVED blend+glb t=%.1fs" % (time.time() - t0))

# ----------------------------------------------------------------------------------------
# Render
# ----------------------------------------------------------------------------------------
def setup_engine():
    if ENGINE == "cycles":
        scene.render.engine = "CYCLES"
        c = scene.cycles; c.samples = SAMPLES; c.use_denoising = True; c.use_adaptive_sampling = True
        try:
            pr = bpy.context.preferences.addons["cycles"].preferences
            pr.compute_device_type = "METAL"; pr.get_devices()
            for d in pr.devices: d.use = True
            c.device = "GPU"
        except Exception as e:
            print("GPU setup failed, CPU:", e)
    else:
        for name in ("BLENDER_EEVEE", "BLENDER_EEVEE_NEXT"):
            try: scene.render.engine = name; break
            except TypeError: pass
        try: scene.eevee.taa_render_samples = SAMPLES
        except Exception: pass

if DO_RENDER:
    setup_engine()
    r0 = time.time()
    scene.render.filepath = os.path.join(RENDER, "assembly-hero.png")
    bpy.ops.render.render(write_still=True)
    print("HERO render %.1fs engine=%s" % (time.time() - r0, scene.render.engine))
    # exploded layout: printed parts only, spread on the ground
    for o in bought: o.hide_render = True; o.hide_viewport = True
    shell.location = (0.0, 0.0, 0.0)
    ramp.rotation_euler = (0, 0, 0); ramp.location = (-0.05, -0.30, 0.0)
    tray.location = (0.30, -0.14, 0.0)
    mast.location = (0.30, 0.10, 0.0)
    aim((0.80, -0.92, 0.52), (0.13, -0.06, 0.07))
    scene.render.filepath = os.path.join(RENDER, "parts-exploded.png")
    r1 = time.time(); bpy.ops.render.render(write_still=True)
    print("EXPLODED render %.1fs" % (time.time() - r1))
print("DONE total %.1fs" % (time.time() - t0))
