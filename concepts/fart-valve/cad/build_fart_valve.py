"""Fart Valve (Concept) - benchtop PETG instrument with a silicone ring valve and two cheek pads.

Run headless:
  /Applications/Blender.app/Contents/MacOS/Blender -b -P build_fart_valve.py -- [--samples 128] [--scale 1.0] [--no-render] [--only assembly,hero,detail,top,cartridge]

Single source of truth for the photo shots (render/shots/*-blender.png), the studio render, the .blend,
the printed-part STLs (cad/stl, millimetres) and the viewer GLB (render/model.glb).
Units: Blender metres; the parameter dict D and all builder helpers take millimetres.
Coordinates: instrument front (the ring face) = +X, left = +Y, up = +Z. glTF is Y-up: export_yup keeps +X as +X,
so the ring face looks along +X in the GLB. Body sits on 6 mm feet, so the body spans z 6..146.
"""
import bpy, bmesh, math, os, sys, time, random
from mathutils import Vector, Matrix

MM = 0.001
D = dict(
    body=(220.0, 300.0, 140.0), body_rad=12.0, z0=6.0, seam_z=14.0, seam_gap=1.4,
    face_x=110.0, ring_z=82.0,
    step_r=52.0, step_d=4.0, socket_r=45.5, socket_d=28.0,       # bezel recess, cartridge socket
    carrier_r=45.0, carrier_d=25.0, ring_r=35.0, ring_open_r=11.0, folds=10,
    pad=(24.0, 60.0, 88.0), pad_back_x=118.0, pad_gap_open=15.0, pad_gap_closed=-4.0, pad_toe=7.0,
    mic=(108.0, 34.0, 15.0),                                       # y, z, radius
    disp=(65.0, -60.0, 30.0, 80.0), btn=(-8.0, 0.0, 22.5), knobs=((64.0, 44.0), (64.0, 84.0)),
    tray=(96.0, 26.0, 10.0),
    shot_res=(1672, 941), asm_res=(1600, 1200),
)
OUT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CAD, BLEND, RENDER = (os.path.join(OUT, n) for n in ("cad", "blender", "render"))
SHOTS, STL = os.path.join(RENDER, "shots"), os.path.join(CAD, "stl")
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
def arg(name, default):
    return argv[argv.index(name) + 1] if name in argv else default
SAMPLES = int(arg("--samples", "128"))
RSCALE = float(arg("--scale", "1.0"))
DO_RENDER = "--no-render" not in argv
ONLY = set(arg("--only", "assembly,hero,detail,top,cartridge").split(","))
SUFFIX = arg("--suffix", "")
DO_EXPORT = "--no-export" not in argv

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.unit_settings.system = "METRIC"

# ----------------------------------------------------------------------------------------
# Helpers (structure copied from walking-planter/cad/build_walking_planter.py, mm in, metres out)
# ----------------------------------------------------------------------------------------
def V(x, y, z): return Vector((x * MM, y * MM, z * MM))

def active(o):
    bpy.ops.object.select_all(action="DESELECT")
    o.select_set(True)
    bpy.context.view_layer.objects.active = o

def apply_xf(o):
    active(o); bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

AXROT = {"z": (0, 0, 0), "x": (0, math.pi / 2, 0), "y": (math.pi / 2, 0, 0)}
def cyl(name, r, h, c, axis="z", verts=72):
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=r * MM, depth=h * MM, location=V(*c))
    o = bpy.context.active_object; o.name = name; o.rotation_euler = AXROT[axis]; apply_xf(o); return o

def box(name, size, c, rot=None):
    bpy.ops.mesh.primitive_cube_add(size=1, location=V(*c))
    o = bpy.context.active_object; o.name = name; o.scale = (size[0] * MM, size[1] * MM, size[2] * MM)
    if rot: o.rotation_euler = rot
    apply_xf(o); return o

def boolean(target, tool, op="DIFFERENCE", delete=True):
    m = target.modifiers.new("bool", "BOOLEAN")
    m.object = tool; m.operation = op; m.solver = "EXACT"
    active(target); bpy.ops.object.modifier_apply(modifier=m.name)
    if delete: bpy.data.objects.remove(tool, do_unlink=True)
    return target

def cut(t, *tools):
    for x in tools: boolean(t, x, "DIFFERENCE")
    return t

def union(t, *tools):
    for x in tools: boolean(t, x, "UNION")
    return t

def bevel(o, width, segments=2, angle=35):
    m = o.modifiers.new("bev", "BEVEL")
    m.width = width * MM; m.segments = segments; m.limit_method = "ANGLE"; m.angle_limit = math.radians(angle)
    active(o); bpy.ops.object.modifier_apply(modifier=m.name)

def bevel_all(o, width, segments=6):
    m = o.modifiers.new("bev", "BEVEL")
    m.width = width * MM; m.segments = segments; m.limit_method = "NONE"
    active(o); bpy.ops.object.modifier_apply(modifier=m.name)

def smooth(o, angle=40):
    active(o)
    for op in ("shade_smooth_by_angle", "shade_auto_smooth"):
        try:
            getattr(bpy.ops.object, op)(angle=math.radians(angle)); return
        except Exception:
            pass
    bpy.ops.object.shade_smooth()

def rbox(name, size, c, rad, seg=6):
    o = box(name, size, c); bevel_all(o, rad, seg); return o

def join(name, objs):
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs: o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.join()
    o = bpy.context.active_object; o.name = name; return o

def mesh_obj(name, bm):
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); bpy.context.collection.objects.link(o); return o

def rrect_pts(sx, sy, r, n=10):
    pts = []
    for (cx, cy, a0) in ((sx / 2 - r, sy / 2 - r, 0), (-sx / 2 + r, sy / 2 - r, 90), (-sx / 2 + r, -sy / 2 + r, 180), (sx / 2 - r, -sy / 2 + r, 270)):
        for k in range(n + 1):
            a = math.radians(a0 + 90 * k / n); pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts

def prism(name, pts, z0, z1):
    """Straight prism from a closed xy polygon (mm), z0..z1 (mm)."""
    bm = bmesh.new()
    lo = [bm.verts.new((x * MM, y * MM, z0 * MM)) for x, y in pts]
    hi = [bm.verts.new((x * MM, y * MM, z1 * MM)) for x, y in pts]
    n = len(pts)
    for i in range(n):
        j = (i + 1) % n; bm.faces.new((lo[i], lo[j], hi[j], hi[i]))
    bm.faces.new(lo[::-1]); bm.faces.new(hi)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return mesh_obj(name, bm)

def srgb(h):
    c = [int(h[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    lin = lambda v: v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4
    return tuple(lin(v) for v in c)

def setin(b, names, val):
    for k in names:
        if k in b.inputs:
            b.inputs[k].default_value = val; return True
    return False

def make_mat(name, rgb, rough=0.5, metal=0.0, spec=0.5, emit=None, emit_strength=0.0, **kw):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*rgb, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    setin(b, ("Specular IOR Level", "Specular"), spec)
    if emit is not None:
        b.inputs["Emission Color"].default_value = (*emit, 1); b.inputs["Emission Strength"].default_value = emit_strength
    for k, v in kw.items():
        setin(b, (k.replace("_", " "),), v)
    return m

def assign(o, *ms):
    o.data.materials.clear()
    for m in ms: o.data.materials.append(m)

PARTS = []        # product objects (exported to GLB, STL, assembly)
def part(o, m=None, sm=True):
    if m is not None: assign(o, m)
    if sm: smooth(o)
    PARTS.append(o); return o

def node_bump(m, tex_out_fn, strength=0.1, dist=0.001):
    nt = m.node_tree; b = nt.nodes["Principled BSDF"]
    bn = nt.nodes.new("ShaderNodeBump"); bn.inputs["Strength"].default_value = strength; bn.inputs["Distance"].default_value = dist
    nt.links.new(tex_out_fn(nt), bn.inputs["Height"]); nt.links.new(bn.outputs["Normal"], b.inputs["Normal"])

# ----------------------------------------------------------------------------------------
# Materials
# ----------------------------------------------------------------------------------------
M = {}
M["body"] = make_mat("PETG_warm_grey", srgb("#8f8a84"), 0.55, 0.0, 0.45)
def _layers(nt):
    tc = nt.nodes.new("ShaderNodeTexCoord"); w = nt.nodes.new("ShaderNodeTexWave")
    w.wave_type = "BANDS"; w.bands_direction = "Z"; w.wave_profile = "SAW"; w.inputs["Scale"].default_value = 2500
    w.inputs["Distortion"].default_value = 0.4
    nt.links.new(tc.outputs["Object"], w.inputs["Vector"]); return w.outputs["Fac"]
node_bump(M["body"], _layers, 0.08, 0.0003)
M["bezel"] = make_mat("PETG_bezel", srgb("#6e6964"), 0.5, 0.0, 0.45)
M["carrier"] = make_mat("PETG_carrier", srgb("#a8a39d"), 0.5, 0.0, 0.45)
M["dark"] = make_mat("Slit_dark", srgb("#262422"), 0.85, 0.0, 0.1)
M["seam"] = make_mat("Seam_dark", srgb("#171615"), 0.8, 0.0, 0.1)
M["skin"] = make_mat("Silicone_skin", srgb("#d9a48f"), 0.38, 0.0, 0.5,
                     Subsurface_Weight=0.35, Coat_Weight=0.12, Coat_Roughness=0.3, Sheen_Weight=0.1, Sheen_Roughness=0.5)
try:
    sb = M["skin"].node_tree.nodes["Principled BSDF"]
    sb.inputs["Subsurface Radius"].default_value = (1.0, 0.45, 0.3); sb.inputs["Subsurface Scale"].default_value = 0.004
except Exception: pass
M["pad"] = make_mat("Silicone_pad", srgb("#d9a48f"), 0.45, 0.0, 0.5, Subsurface_Weight=0.2, Sheen_Weight=0.1, Sheen_Roughness=0.5)
try:
    pb = M["pad"].node_tree.nodes["Principled BSDF"]
    pb.inputs["Subsurface Radius"].default_value = (1.0, 0.45, 0.3); pb.inputs["Subsurface Scale"].default_value = 0.005
except Exception: pass
M["throat"] = make_mat("Valve_throat", srgb("#2a1410"), 0.6, 0.0, 0.2)
M["alu"] = make_mat("Alu_satin", srgb("#c9cacc"), 0.38, 1.0, 0.5)
M["black"] = make_mat("Black_felt", srgb("#070707"), 0.9, 0.0, 0.05)
M["glass"] = make_mat("Display_glass", srgb("#0a0c10"), 0.05, 0.0, 0.8)
M["wave"] = make_mat("Display_wave", srgb("#ff8a4a"), 0.4, 0.0, 0.3, emit=srgb("#ff8a4a"), emit_strength=3.2)
M["led"] = make_mat("LED_green", srgb("#59ff9a"), 0.4, 0.0, 0.3, emit=srgb("#59ff9a"), emit_strength=6.0)
M["mic"] = make_mat("Mic_grille", srgb("#2d2e31"), 0.42, 0.9, 0.5)
M["button"] = make_mat("Play_orange", srgb("#e0703a"), 0.34, 0.0, 0.5, Coat_Weight=0.2, Coat_Roughness=0.2)
M["knob"] = make_mat("Knob_dark", srgb("#2c2c2f"), 0.4, 0.7, 0.5)
M["feet"] = make_mat("Feet_rubber", srgb("#141414"), 0.85, 0.0, 0.2)
M["tray"] = make_mat("Tray_clear", srgb("#e8f2f4"), 0.04, 0.0, 0.5, Transmission_Weight=1.0, IOR=1.46)
M["mould"] = make_mat("Mould_PETG", srgb("#d6d0c6"), 0.5, 0.0, 0.45)

# ----------------------------------------------------------------------------------------
# The silicone ring (a closed solid of revolution with 10 radial folds converging on a small dark throat)
# ----------------------------------------------------------------------------------------
def ring_mesh(name, r_out, folds, seg=240, puckered=True, seed=3):
    rnd = random.Random(seed)
    # (r, h) mm profile, outer wall at the cartridge face -> crest -> opening lip -> funnel -> throat; local +Z is outward
    base = [(35.0, -14.0), (35.0, -3.0), (35.0, 0.0), (34.2, 3.0), (32.0, 5.6), (29.0, 7.4), (25.5, 8.8), (22.0, 9.6), (18.5, 9.7),
            (15.5, 8.9), (13.0, 7.2), (11.4, 4.8), (10.8, 2.0), (10.2, -1.5), (9.0, -5.0), (7.0, -8.0), (4.5, -10.0), (2.0, -11.0), (0.0, -11.4)]
    prof = [(r * r_out / 35.0, h) for r, h in base]
    # densify (Catmull-Rom would be overkill: subdivide linearly twice, the folds supply the shape)
    for _ in range(2):
        nxt = []
        for a, b in zip(prof[:-1], prof[1:]):
            nxt += [a, ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)]
        nxt.append(prof[-1]); prof = nxt
    amps = [1.0 + 0.16 * math.sin(k * 2.3 + 0.7) + rnd.uniform(-0.05, 0.05) for k in range(folds)]
    def fold(th):
        u = th / (2 * math.pi) * folds; k = int(u) % folds
        return amps[k] * (abs(math.cos(math.pi * u)) ** 1.0 - 0.55)
    def sstep(a, b, x):
        t = max(0.0, min(1.0, (x - a) / (b - a))); return t * t * (3 - 2 * t)
    bm = bmesh.new(); rows = []
    for (r, h) in prof:
        if r < 1e-6 and False: pass
        row = []
        for k in range(seg):
            th = 2 * math.pi * k / seg
            rr, hh = r, h
            if puckered and r > 0.01 and h > -13.9:
                f = fold(th)
                w_h = sstep(33.0, 14.0, r) * (1 - sstep(11.0, 8.0, r))          # height folds across the shoulder
                w_r = sstep(13.0, 10.5, r) * (1 - sstep(4.0, 1.0, r)) + 0.35 * sstep(6.0, 1.5, r) * sstep(0.0, 3.0, r)   # radial pucker in the funnel
                hh = h + 1.5 * w_h * f
                rr = r * (1 + 0.16 * w_r * f)
                if r < 3.0: rr = r * (1 + 0.5 * f * sstep(0.0, 3.0, r))
            row.append(bm.verts.new((rr * math.cos(th) * MM, rr * math.sin(th) * MM, hh * MM)))
        rows.append(row)
    # the last profile point is the throat centre: collapse to one vertex
    centre = bm.verts.new((0, 0, prof[-1][1] * MM)); rows[-1] = [centre]
    for a, b in zip(rows[:-1], rows[1:]):
        for k in range(seg):
            k2 = (k + 1) % seg
            if len(b) == 1: bm.faces.new((a[k], a[k2], b[0]))
            else: bm.faces.new((a[k], a[k2], b[k2], b[k]))
    # underside disc closing the solid at h = -14
    bot = bm.verts.new((0, 0, -14.0 * MM))
    for k in range(seg):
        k2 = (k + 1) % seg; bm.faces.new((rows[0][k2], rows[0][k], bot))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    for f in bm.faces:
        c = f.calc_center_median(); rr = math.hypot(c.x, c.y) / MM
        f.material_index = 1 if (c.z / MM < -7.0 and rr < 6.0) else 0
        f.smooth = True
    return mesh_obj(name, bm)

# ----------------------------------------------------------------------------------------
# Build the instrument
# ----------------------------------------------------------------------------------------
FX, RZ = D["face_x"], D["ring_z"]
bx, by, bz = D["body"]; z0 = D["z0"]; ztop = z0 + bz
body = rbox("body", (bx, by, bz), (0, 0, z0 + bz / 2), D["body_rad"], 8)
# front: bezel step and cartridge socket, bayonet entry slots
cut(body, cyl("c_step", D["step_r"], 2 * D["step_d"], (FX, 0, RZ), "x", 96))
cut(body, cyl("c_sock", D["socket_r"], D["socket_d"] + 4, (FX - D["socket_d"] / 2 + 2, 0, RZ), "x", 96))
for s in (1, -1):
    cut(body, box("c_bay", (19, 6.5, 9), (FX - 7.5, s * (D["socket_r"] + 0.8), RZ)))
# arm slits (two per side)
ARM_Z = (RZ + 2 - 26, RZ + 2 + 26)
for s in (1, -1):
    for az in ARM_Z:
        cut(body, box("c_slit", (14, 76, 8.0), (FX - 3, s * 86, az)))
# mic pocket
my, mz, mr = D["mic"]
cut(body, cyl("c_mic", mr + 0.2, 6, (FX, my, mz), "x", 64))
# top: display pocket, button pocket
dx, dy, dsx, dsy = D["disp"]
cut(body, box("c_disp", (dsx, dsy, 3.2), (dx, dy, ztop)))
bxp, byp, br = D["btn"]
cut(body, cyl("c_btn", br + 1.7, 6, (bxp, byp, ztop), "z", 96))
# back: DC jack, USB, vent slots
cut(body, cyl("c_dc", 5.6, 16, (-FX, 62, 52), "x", 40))
cut(body, box("c_usb", (16, 14.2, 7.2), (-FX, 20, 52)))
slots = [box("c_vs", (12, 46, 2.4), (-FX, -64, 120 - 6 * i)) for i in range(9)]
cut(body, join("c_vents", slots))
# split into base and top shell with a 1.4 mm seam
SEAM0, SEAM1 = D["seam_z"], D["seam_z"] + D["seam_gap"]
def dup(o, name):
    n = bpy.data.objects.new(name, o.data.copy()); bpy.context.collection.objects.link(n); return n
top = dup(body, "body_top"); base = dup(body, "body_base")
bpy.data.objects.remove(body, do_unlink=True)
boolean(top, box("k_top", (600, 600, 200), (0, 0, SEAM1 + 100)), "INTERSECT")
boolean(base, box("k_base", (600, 600, 200), (0, 0, SEAM0 - 100)), "INTERSECT")
for o in (top, base): bevel(o, 0.6, 2, 40)
part(top, M["body"]); part(base, M["body"])
core = prism("seam_core", rrect_pts(bx - 5, by - 5, D["body_rad"] - 2.5), SEAM0 - 0.2, SEAM1 + 0.2); part(core, M["seam"], False)
for sx_ in (-1, 1):
    for sy_ in (-1, 1):
        part(cyl("foot", 9, z0, (sx_ * 82, sy_ * 124, z0 / 2), "z", 40), M["feet"])

# bezel trim ring (printed, in the step)
bezel = cyl("bezel", D["step_r"] - 0.4, 2.6, (FX - D["step_d"] + 1.3, 0, RZ), "x", 96)
cut(bezel, cyl("bezel_in", D["socket_r"] + 0.9, 8, (FX - D["step_d"] + 1.3, 0, RZ), "x", 96))
bevel(bezel, 0.7, 2); part(bezel, M["bezel"])
# socket floor nozzle (visible only with the cartridge out) + black o-ring
noz = cyl("nozzle", 12, 8, (FX - D["socket_d"] + 4, 0, RZ), "x", 48); part(noz, M["alu"])
noz_hole = cyl("nozzle_hole", 5.5, 1, (FX - D["socket_d"] + 8.05, 0, RZ), "x", 32); part(noz_hole, M["black"], False)
oring = cyl("oring", 17, 2, (FX - D["socket_d"] + 1.2, 0, RZ), "x", 64); cut(oring, cyl("oring_in", 13.5, 6, (FX - D["socket_d"] + 1.2, 0, RZ), "x", 64)); part(oring, M["black"])
# slit liners (dark floor so the slits read as slots)
for s in (1, -1):
    for az in ARM_Z:
        part(box("slit_liner", (0.3, 75, 7.9), (FX - 8.2, s * 86, az)), M["dark"], False)

# --- ring cartridge: carrier (printed) + cast silicone ring, built in a local frame, +Z = out of the face
cart = bpy.data.objects.new("cartridge", None); bpy.context.collection.objects.link(cart)
carrier = cyl("carrier", D["carrier_r"], D["carrier_d"], (0, 0, -D["carrier_d"] / 2), "z", 96)
cut(carrier, cyl("car_bore", D["ring_r"] + 0.15, 16, (0, 0, -6), "z", 96))
cut(carrier, cyl("car_back", 13.2, 12, (0, 0, -D["carrier_d"] + 4), "z", 64))
for s in (1, -1):
    lug = box("lug", (10, 6.5, 5.5), (0, s * (D["carrier_r"] + 2.0), -8.0))
    # lugs face +/-Y in world once the cartridge is rotated onto the face (local y stays world y)
    union(carrier, lug)
bevel(carrier, 0.8, 2)
for s in (1, -1):   # index dots on the carrier face
    part(cyl("dot", 1.5, 0.4, (s * 40.5, 0, 0.1), "z", 20), M["bezel"], False).parent = cart
part(carrier, M["carrier"]); carrier.parent = cart
ring = ring_mesh("ring", D["ring_r"], D["folds"])
part(ring); assign(ring, M["skin"], M["throat"]); ring.parent = cart
for _p in ring.data.polygons:      # slot indices are reset by assign(); mark the dark throat faces again
    _c = _p.center; _p.material_index = 1 if (_c.z / MM < -7.0 and math.hypot(_c.x, _c.y) / MM < 6.0) else 0
for o in cart.children: o.matrix_parent_inverse = Matrix.Identity(4)
def cart_install():
    cart.location = V(FX - 4.0, 0, RZ); cart.rotation_euler = (0, math.pi / 2, 0)
def cart_lying(loc):
    cart.location = Vector(loc) + V(0, 0, D["carrier_d"]); cart.rotation_euler = (0, 0, math.radians(-20))

# --- cheek pads on satin aluminium arms
pw, ph = D["pad"][1], D["pad"][2]
pad_proto = rbox("pad_proto", (D["pad"][0], pw, ph), (0, 0, 0), 11.0, 8)
CHEEKS = {}
for s, nm in ((1, "L"), (-1, "R")):
    g = bpy.data.objects.new("cheek_" + nm, None); bpy.context.collection.objects.link(g)
    pad = bpy.data.objects.new("pad_" + nm, pad_proto.data.copy()); bpy.context.collection.objects.link(pad)
    pad.parent = g; pad.location = (D["pad"][0] / 2 * MM + 0.0, 0, 0)
    pad.rotation_euler = (0, 0, math.radians(-s * D["pad_toe"]))
    part(pad, M["pad"]); CHEEKS[nm] = (g, s)
    # pad dimple (soft hollow where it presses the ring): shallow concave via a sphere cut on the inner side is skipped; the toe-in carries it
    for az in ARM_Z:
        arm = box("arm", (7, 56, 7), (FX + 0.5, s * 10, az))        # sits in the slit, 3.5 mm proud of the face
        arm.parent = g
        post = rbox("post", (D["pad_back_x"] - FX - 3.0, 16, 14), (0, 0, 0), 2.0, 3)
        post.location = V(FX + 3.0 + (D["pad_back_x"] - FX - 3.0) / 2, 0, az)
        post.parent = g
        for o_, m_ in ((arm, M["alu"]), (post, M["alu"])):
            part(o_, m_)
    g.location = (0, 0, 0)
    for ch in g.children:
        pass
bpy.data.objects.remove(pad_proto, do_unlink=True)

def pose_cheeks(state):
    gap = D["pad_gap_open"] if state == "open" else D["pad_gap_closed"]
    cy = D["ring_r"] + gap + pw / 2
    for nm, (g, s) in CHEEKS.items():
        g.location = (0, s * cy * MM, 0)
        # children were authored at x=FX-relative positions with y=0, z in world; pad needs its own z and x
    update_cheek_children()
def update_cheek_children():
    pass
# fix child placement once: pad at (pad_back_x + depth/2, 0, RZ+2); arms/posts keep their authored z and share group y
for nm, (g, s) in CHEEKS.items():
    for ch in g.children:
        if ch.name.startswith("pad_"):
            ch.location = V(D["pad_back_x"] + D["pad"][0] / 2, 0, RZ + 2)

# --- mic grille: perforated dark metal disc in its pocket
mgr = cyl("mic_plate", mr - 0.3, 2.2, (FX - 1.1, my, mz), "x", 64)
holes = []
pitch = 3.0
for i in range(-5, 6):
    for j in range(-5, 6):
        yy = j * pitch + (pitch / 2 if i % 2 else 0); zz = i * pitch * 0.866
        if math.hypot(yy, zz) <= mr - 3.2:
            holes.append(cyl("h", 0.95, 4, (FX - 1.1, my + yy, mz + zz), "x", 10))
cut(mgr, join("mic_holes", holes)); part(mgr, M["mic"])
part(cyl("mic_felt", mr - 0.3, 0.6, (FX - 2.5, my, mz), "x", 64), M["black"], False)

# --- top: display, play button, knobs, status LED
dglass = box("display_glass", (dsx - 1.6, dsy - 1.6, 1.4), (dx, dy, ztop - 1.2)); part(dglass, M["glass"], False)
part(box("display_floor", (dsx - 0.6, dsy - 0.6, 0.3), (dx, dy, ztop - 1.65)), M["black"], False)
wv = []
rnd = random.Random(11)
for i in range(27):
    y_ = dy - 31.5 + i * 2.4
    h_ = 1.6 + 8.5 * (abs(math.sin(i * 0.52)) * (0.4 + 0.6 * rnd.random()))
    wv.append(box("wb", (h_, 1.0, 0.06), (dx, y_, ztop - 0.5 + 0.03)))
wv.append(box("wl", (0.5, 66, 0.06), (dx, dy, ztop - 0.5 + 0.03)))
part(join("display_wave", wv), M["wave"], False)
part(cyl("status_led", 1.6, 0.4, (dx + 2, dy + 49, ztop - 0.2), "z", 20), M["led"], False)
# play button
part(cyl("btn_liner", br + 1.5, 0.3, (bxp, byp, ztop - 2.9), "z", 64), M["black"], False)
prof = [(0, 3.2), (6, 3.05), (12, 2.6), (17, 1.9), (20.5, 1.1), (22.0, 0.5), (22.5, -0.2), (22.5, -2.6), (0, -2.6)]
bm = bmesh.new(); seg_ = 96; rws = []
for (r, h) in prof:
    rws.append([bm.verts.new(((bxp + r * math.cos(2 * math.pi * k / seg_)) * MM, (byp + r * math.sin(2 * math.pi * k / seg_)) * MM, (ztop + h) * MM)) if r > 0 else None for k in range(seg_)])
c0 = bm.verts.new((bxp * MM, byp * MM, (ztop + 3.2) * MM)); c1 = bm.verts.new((bxp * MM, byp * MM, (ztop - 2.6) * MM))
rws[0] = [c0] * seg_; rws[-1] = [c1] * seg_
for a, b in zip(rws[:-1], rws[1:]):
    for k in range(seg_):
        k2 = (k + 1) % seg_
        if a[k] is a[k2]: bm.faces.new((a[k], b[k2], b[k]))
        elif b[k] is b[k2]: bm.faces.new((a[k], a[k2], b[k]))
        else: bm.faces.new((a[k], a[k2], b[k2], b[k]))
bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
part(mesh_obj("play_button", bm), M["button"])
# knobs (knurled)
def knurl(name, cx, cy, h, r=9.0, n=44):
    bm = bmesh.new(); lo, hi = [], []
    for k in range(2 * n):
        rr = r if k % 2 == 0 else r - 0.55; a = math.pi * k / n
        lo.append(bm.verts.new(((cx + rr * math.cos(a)) * MM, (cy + rr * math.sin(a)) * MM, ztop * MM)))
        hi.append(bm.verts.new(((cx + rr * math.cos(a)) * MM, (cy + rr * math.sin(a)) * MM, (ztop + h) * MM)))
    for i in range(2 * n):
        j = (i + 1) % (2 * n); bm.faces.new((lo[i], lo[j], hi[j], hi[i]))
    bm.faces.new(lo[::-1]); bm.faces.new(hi)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return mesh_obj(name, bm)
for i, (kx, ky) in enumerate(D["knobs"]):
    part(knurl("knob%d" % i, kx, ky, 12.0), M["knob"], False)
    part(cyl("knob_cap%d" % i, 7.0, 0.8, (kx, ky, ztop + 12.2), "z", 48), M["alu"])
    ang = math.radians(35 + 70 * i)
    part(box("knob_tick%d" % i, (6.0, 1.2, 0.3), (kx + 3.0 * math.cos(ang), ky + 3.0 * math.sin(ang), ztop + 12.7), (0, 0, ang)), M["button"], False)
# back ports
part(cyl("dc_liner", 5.0, 0.4, (-FX + 7.7, 62, 52), "x", 32), M["black"], False)
part(cyl("dc_pin", 1.3, 7, (-FX + 4.2, 62, 52), "x", 16), M["alu"], False)
part(box("usb_shell", (0.6, 12.4, 6.0), (-FX + 7.0, 20, 52)), M["alu"], False)
part(box("usb_tongue", (5.0, 8.0, 1.6), (-FX + 9.0, 20, 52)), M["black"], False)
part(box("vent_liner", (0.3, 48, 66), (-FX + 5.9, -64, 96)), M["black"], False)
# drip tray (clear) at the front base
tw, td, th = D["tray"]
tray = rbox("drip_tray", (td, tw, th), (FX + td / 2 - 2.0, 0, z0 + th / 2), 2.4, 3)
cut(tray, rbox("tray_in", (td - 5.0, tw - 5.0, th), (FX + td / 2 - 2.0 + 1.0, 0, z0 + th / 2 + 3.2), 1.6, 3))
part(tray, M["tray"])

pose_cheeks("open"); cart_install()
bpy.context.view_layer.update()
# fix grouped arm/post y so they ride with the pad group (their authored y was 0 = group origin)
for o in bpy.data.objects:
    if o.type == "MESH": o.select_set(False)

# ----------------------------------------------------------------------------------------
# Environment (render-only, never exported)
# ----------------------------------------------------------------------------------------
ENV = {k: [] for k in ("hero", "detail", "top", "cartridge", "assembly")}
LIGHTS = {k: [] for k in ENV}
ENVMATS = {}

def mat_wood():
    m = bpy.data.materials.new("Walnut"); m.use_nodes = True; nt = m.node_tree; b = nt.nodes["Principled BSDF"]
    tc = nt.nodes.new("ShaderNodeTexCoord"); mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (1.0, 0.04, 1.0)
    nt.links.new(tc.outputs["Object"], mp.inputs["Vector"])
    w = nt.nodes.new("ShaderNodeTexWave"); w.wave_type = "BANDS"; w.bands_direction = "X"; w.wave_profile = "SAW"
    w.inputs["Scale"].default_value = 28; w.inputs["Distortion"].default_value = 6.0; w.inputs["Detail"].default_value = 3.0; w.inputs["Detail Scale"].default_value = 1.4
    nt.links.new(mp.outputs["Vector"], w.inputs["Vector"])
    nz = nt.nodes.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 3.0; nz.inputs["Detail"].default_value = 4.0
    nt.links.new(mp.outputs["Vector"], nz.inputs["Vector"])
    mx = nt.nodes.new("ShaderNodeMix"); mx.data_type = "FLOAT"; mx.inputs[0].default_value = 0.2
    nt.links.new(w.outputs["Fac"], mx.inputs[2]); nt.links.new(nz.outputs["Fac"], mx.inputs[3])
    cr = nt.nodes.new("ShaderNodeValToRGB")
    cr.color_ramp.elements[0].color = (*srgb("#080403"), 1); cr.color_ramp.elements[1].color = (*srgb("#2c180d"), 1); cr.color_ramp.elements[0].position = 0.25; cr.color_ramp.elements[1].position = 0.75
    nt.links.new(mx.outputs["Result"], cr.inputs["Fac"]); nt.links.new(cr.outputs["Color"], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.5; setin(b, ("Coat Weight",), 0.12); setin(b, ("Coat Roughness",), 0.2)
    bn = nt.nodes.new("ShaderNodeBump"); bn.inputs["Strength"].default_value = 0.3; bn.inputs["Distance"].default_value = 0.0006
    nt.links.new(w.outputs["Fac"], bn.inputs["Height"]); nt.links.new(bn.outputs["Normal"], b.inputs["Normal"])
    return m

def mat_noise(name, c1, c2, rough, scale, bump, bdist=0.0004):
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree; b = nt.nodes["Principled BSDF"]
    tc = nt.nodes.new("ShaderNodeTexCoord"); nz = nt.nodes.new("ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value = scale; nz.inputs["Detail"].default_value = 8.0
    nt.links.new(tc.outputs["Object"], nz.inputs["Vector"])
    cr = nt.nodes.new("ShaderNodeValToRGB"); cr.color_ramp.elements[0].color = (*c1, 1); cr.color_ramp.elements[1].color = (*c2, 1)
    nt.links.new(nz.outputs["Fac"], cr.inputs["Fac"]); nt.links.new(cr.outputs["Color"], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = rough
    bn = nt.nodes.new("ShaderNodeBump"); bn.inputs["Strength"].default_value = bump; bn.inputs["Distance"].default_value = bdist
    nt.links.new(nz.outputs["Fac"], bn.inputs["Height"]); nt.links.new(bn.outputs["Normal"], b.inputs["Normal"])
    return m

def mat_cutmat():
    m = bpy.data.materials.new("Cutting_mat"); m.use_nodes = True; nt = m.node_tree; b = nt.nodes["Principled BSDF"]
    tc = nt.nodes.new("ShaderNodeTexCoord"); br = nt.nodes.new("ShaderNodeTexBrick")
    br.inputs["Scale"].default_value = 100.0; br.inputs["Mortar Size"].default_value = 0.012; br.inputs["Mortar Smooth"].default_value = 0.1
    br.inputs["Bias"].default_value = 0.0; br.offset = 0.0; br.squash = 1.0
    br.inputs["Brick Width"].default_value = 1.0; br.inputs["Row Height"].default_value = 1.0
    br.inputs["Color1"].default_value = (*srgb("#1f5a3e"), 1); br.inputs["Color2"].default_value = (*srgb("#1f5a3e"), 1)
    br.inputs["Mortar"].default_value = (*srgb("#8fc0a4"), 1)
    nt.links.new(tc.outputs["Object"], br.inputs["Vector"]); nt.links.new(br.outputs["Color"], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.6
    return m

def plane(name, size, mat, loc=(0, 0, 0)):
    bpy.ops.mesh.primitive_plane_add(size=size, location=loc)
    o = bpy.context.active_object; o.name = name; assign(o, mat); return o

def area(name, loc, target, energy, size, color=(1, 1, 1), shape="SQUARE"):
    bpy.ops.object.light_add(type="AREA", location=loc)
    l = bpy.context.active_object; l.name = name; l.data.energy = energy; l.data.size = size; l.data.color = color; l.data.shape = shape
    d = Vector(target) - Vector(loc); l.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    return l

def world(color=None, strength=1.0, gradient=None):
    w_ = bpy.data.worlds.new("W"); w_.use_nodes = True
    nt = w_.node_tree; bg = nt.nodes["Background"]
    if gradient:
        tc = nt.nodes.new("ShaderNodeTexCoord"); sep = nt.nodes.new("ShaderNodeSeparateXYZ")
        nt.links.new(tc.outputs["Generated"], sep.inputs["Vector"])
        rp = nt.nodes.new("ShaderNodeValToRGB"); el = rp.color_ramp.elements
        el[0].position = gradient[0][0]; el[0].color = (*gradient[0][1], 1)
        el[1].position = gradient[1][0]; el[1].color = (*gradient[1][1], 1)
        for pos, col in gradient[2:]:
            e = el.new(pos); e.color = (*col, 1)
        nt.links.new(sep.outputs["Z"], rp.inputs["Fac"]); nt.links.new(rp.outputs["Color"], bg.inputs["Color"])
    else:
        bg.inputs["Color"].default_value = (*color, 1)
    bg.inputs["Strength"].default_value = strength
    return w_

bpy.ops.object.camera_add()
cam = bpy.context.active_object; cam.name = "camera"; scene.camera = cam
cam.data.lens = 50; cam.data.sensor_width = 36; cam.data.clip_end = 80; cam.data.clip_start = 0.01
def aim(loc, target):
    cam.location = loc; cam.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
def look_basis(loc, target):
    f = (Vector(target) - Vector(loc)).normalized()
    r = f.cross(Vector((0, 0, 1))).normalized(); u = r.cross(f).normalized()
    return f, r, u
scene.render.image_settings.file_format = "PNG"
for vt in ("AgX", "Khronos PBR Neutral", "Standard"):
    try: scene.view_settings.view_transform = vt; break
    except TypeError: pass
try: scene.view_settings.look = "AgX - Medium High Contrast"
except Exception: pass

# ----- hero set: walnut desk, mixing console (blurred), headphones
def make_console():
    root = bpy.data.objects.new("console_root", None); bpy.context.collection.objects.link(root)
    W, Dp, H0, H1 = 900.0, 420.0, 30.0, 95.0
    hull = [(-W / 2, -Dp / 2, 0), (W / 2, -Dp / 2, 0), (W / 2, Dp / 2, 0), (-W / 2, Dp / 2, 0),
            (-W / 2, -Dp / 2, H0), (W / 2, -Dp / 2, H0), (W / 2, Dp / 2, H1), (-W / 2, Dp / 2, H1)]
    bm = bmesh.new(); vs = [bm.verts.new((x * MM, y * MM, z * MM)) for x, y, z in hull]
    bmesh.ops.convex_hull(bm, input=vs)
    body_ = mesh_obj("console_body", bm); assign(body_, make_mat("Console_body", srgb("#1b1c1e"), 0.5, 0.2)); body_.parent = root
    tilt = math.atan2(H1 - H0, Dp)
    top = bpy.data.objects.new("console_top", None); bpy.context.collection.objects.link(top)
    top.parent = root; top.location = V(0, 0, (H0 + H1) / 2 + 0.2); top.rotation_euler = (tilt, 0, 0)
    knob_cols = ["#c8372d", "#e2b13a", "#3a78c4", "#d9d9d6"]
    parts = {"cap": [], "dark": [], "slot": [], "cap2": [], "ledg": [], "leda": [], "ledr": []}
    n_ch = 14
    for c in range(n_ch):
        x = -W / 2 + 45 + c * (W - 90) / (n_ch - 1)
        for rw in range(4):
            y = Dp / 2 - 40 - rw * 38
            kb = cyl("k", 8.5, 12, (x, y, 6), "z", 20); parts["dark"].append(kb)
            kc = cyl("kc", 6.5, 1.0, (x, y, 12.5), "z", 20); parts["cap"].append((kc, rw))
        slot = box("s", (5.0, 190.0, 1.0), (x, -Dp / 2 + 130, 0.3)); parts["slot"].append(slot)
        fd = box("f", (14.0, 22.0, 9.0), (x, -Dp / 2 + 130 - 40 + (c * 37 % 120), 4.5)); parts["cap2"].append(fd)
        for i in range(8):
            led = box("l", (4.0, 4.0, 1.5), (x + 15.5, -Dp / 2 + 80 + i * 8.5, 0.8)); parts["ledg" if i < 5 else ("leda" if i < 7 else "ledr")].append(led)
    for rw in range(4):
        grp = [o for (o, r_) in parts["cap"] if r_ == rw]
        j = join("kcaps%d" % rw, grp); assign(j, make_mat("kc%d" % rw, srgb(knob_cols[rw]), 0.45, 0.0, 0.4)); j.parent = top
    for key, mat_ in (("dark", make_mat("Console_knob", srgb("#0d0d0e"), 0.5, 0.0, 0.4)), ("slot", make_mat("Console_slot", srgb("#050505"), 0.8)),
                      ("cap2", make_mat("Fader_cap", srgb("#9b9ea3"), 0.4, 0.9, 0.5)),
                      ("ledg", make_mat("LEDg", srgb("#59ff9a"), 0.4, emit=srgb("#59ff9a"), emit_strength=22.0)),
                      ("leda", make_mat("LEDa", srgb("#ffc34a"), 0.4, emit=srgb("#ffc34a"), emit_strength=22.0)),
                      ("ledr", make_mat("LEDr", srgb("#ff4a3a"), 0.4, emit=srgb("#ff4a3a"), emit_strength=22.0))):
        j = join("c_" + key, parts[key]); assign(j, mat_); j.parent = top
    for o in list(root.children_recursive):
        if o.type == "MESH": o.hide_render = True
    return root

def make_headphones():
    root = bpy.data.objects.new("headphones", None); bpy.context.collection.objects.link(root)
    mb = make_mat("HP_plastic", srgb("#151517"), 0.35, 0.0, 0.5); ml = make_mat("HP_leather", srgb("#2a211d"), 0.55, 0.0, 0.3)
    mm = make_mat("HP_metal", srgb("#8d8f93"), 0.35, 0.9, 0.5)
    R = 88.0
    for s in (1, -1):
        cup = cyl("hp_cup", 46, 34, (s * R, 0, 17), "z", 56); assign(cup, mb); smooth(cup); bevel(cup, 5, 3); cup.parent = root
        pad_ = cyl("hp_pad", 44, 14, (s * R, 0, 41), "z", 56); cut(pad_, cyl("hp_pad_in", 26, 20, (s * R, 0, 41), "z", 40)); bevel_all(pad_, 5.5, 4)
        assign(pad_, ml); smooth(pad_); pad_.parent = root
        drv = cyl("hp_drv", 27, 1, (s * R, 0, 34.2), "z", 40); assign(drv, make_mat("HP_cloth", srgb("#0c0c0d"), 0.9)); drv.parent = root
        yoke = box("hp_yoke", (10, 24, 8), (s * R, 48, 22)); assign(yoke, mm); yoke.parent = root
    pts = []
    for k in range(25):
        a = math.pi + math.pi * k / 24 * -1.0
        pts.append((R * math.cos(math.pi * k / 24) , -R * 1.05 * math.sin(math.pi * k / 24) - 46, 22))
    pts = [(R * math.cos(math.pi * k / 24), 46 + 96 * math.sin(math.pi * k / 24), 22) for k in range(25)]
    cu = bpy.data.curves.new("hp_band", "CURVE"); cu.dimensions = "3D"
    sp = cu.splines.new("POLY"); sp.points.add(len(pts) - 1)
    for p, v in zip(sp.points, pts): p.co = (v[0] * MM, v[1] * MM, v[2] * MM, 1)
    cu.bevel_depth = 6.0 * MM; cu.bevel_resolution = 4; cu.use_fill_caps = True
    band = bpy.data.objects.new("hp_band", cu); bpy.context.collection.objects.link(band)
    active(band); bpy.ops.object.convert(target="MESH"); band = bpy.context.active_object
    assign(band, mb); smooth(band); band.scale = (1, 1, 3.4); band.parent = root
    return root

wood = mat_wood()
desk_hero = plane("desk_hero", 12, wood); ENV["hero"].append(desk_hero); ENV["detail"].append(desk_hero)
desk_mat = plane("desk_mat", 12, mat_noise("Desk_mat_grey", srgb("#aaaaab"), srgb("#c2c2c1"), 0.92, 900, 0.5, 0.0006)); ENV["top"].append(desk_mat)
bench = plane("bench", 12, mat_noise("Plywood", srgb("#80603f"), srgb("#a07a4e"), 0.6, 40, 0.15)); ENV["cartridge"].append(bench)
cutmat = plane("cut_mat", 0.62, mat_cutmat(), (0.04, 0.03, 0.0008)); cutmat.scale = (1, 0.75, 1); ENV["cartridge"].append(cutmat)
studio_floor = plane("studio_floor", 400, make_mat("Studio_floor", srgb("#8a8b8e"), 0.7, 0.0, 0.2)); ENV["assembly"].append(studio_floor)
console = make_console(); headphones = make_headphones()
for root_, key in ((console, "hero"), (headphones, "hero")):
    for o in root_.children_recursive: ENV[key].append(o)
    ENV[key].append(root_)
for o in console.children_recursive: o.hide_render = True
WORLDS = {
    "hero": world(strength=0.10, color=(0.10, 0.06, 0.04)),
    "detail": world(strength=0.10, color=(0.10, 0.06, 0.04)),
    "top": world(color=(0.62, 0.64, 0.68), strength=0.22),
    "cartridge": world(color=(0.60, 0.62, 0.66), strength=0.2),
    "assembly": world(color=(0.42, 0.43, 0.45), strength=0.75),
}
def set_visible(shot):
    for objs in ENV.values():
        for o in objs: o.hide_render = True
    for o in ENV[shot]: o.hide_render = False
    for k, ls in LIGHTS.items():
        for l in ls: l.hide_render = (k != shot)
    scene.world = WORLDS[shot]

def setup_engine():
    scene.render.engine = "CYCLES"
    c = scene.cycles; c.samples = SAMPLES; c.use_denoising = True; c.use_adaptive_sampling = True; c.max_bounces = 10
    try:
        pr = bpy.context.preferences.addons["cycles"].preferences
        pr.compute_device_type = "METAL"; pr.get_devices()
        for d in pr.devices: d.use = True
        c.device = "GPU"
    except Exception as e:
        print("GPU setup failed, CPU:", e)

def do_render(path, res, exposure=0.0):
    scene.render.resolution_x, scene.render.resolution_y = int(res[0] * RSCALE), int(res[1] * RSCALE)
    scene.view_settings.exposure = exposure; scene.render.filepath = path
    r = time.time(); bpy.ops.render.render(write_still=True)
    print("RENDER %s %.1fs" % (os.path.basename(path), time.time() - r), flush=True)

for p in (CAD, BLEND, RENDER, SHOTS, STL): os.makedirs(p, exist_ok=True)
t0 = time.time()
cam.data.dof.use_dof = False

if DO_RENDER:
    setup_engine()
    sfx = SUFFIX
    TGT = Vector((0, 0, 0.078))
    # ===== assembly-hero: neutral grey seamless, cheeks open, clean three-quarter =====
    if "assembly" in ONLY:
        pose_cheeks("open"); cart_install()
        az = math.radians(36); dist = 0.74
        loc = Vector((dist * math.cos(az), dist * math.sin(az), 0.42)); aim(loc, TGT + Vector((0, 0, -0.012)))
        cam.data.lens = 50; cam.data.dof.use_dof = False
        f, r, u = look_basis(loc, TGT)
        LIGHTS["assembly"] = [area("a_key", TGT - r * 0.9 + u * 0.7 - f * 0.3 + Vector((0, 0, 0.5)), TGT, 30, 0.9, (1.0, 0.96, 0.9)),
                              area("a_fill", TGT + r * 1.1 + Vector((0.2, 0, 0.2)), TGT, 10, 1.4, (0.9, 0.94, 1.0)),
                              area("a_rim", TGT + f * 0.9 + Vector((0, 0, 0.9)) + r * 0.3, TGT, 18, 0.8, (1, 1, 1))]
        set_visible("assembly")
        do_render(os.path.join(RENDER, "assembly-hero%s.png" % sfx), D["asm_res"], -0.2)
    # ===== hero: walnut desk, console behind, headphones, warm key from camera-left =====
    if "hero" in ONLY:
        pose_cheeks("open"); cart_install()
        az = math.radians(36); dist = 0.80
        loc = Vector((dist * math.cos(az), dist * math.sin(az), 0.27)); tgt = TGT + Vector((0, 0, 0.002))
        f, r, u = look_basis(loc, tgt)
        fh = Vector((f.x, f.y, 0)).normalized()
        cam.data.lens = 34; aim(loc, tgt + r * 0.085)
        f, r, u = look_basis(loc, tgt + r * 0.085)
        cam.data.dof.use_dof = True; cam.data.dof.aperture_fstop = 3.2; cam.data.dof.focus_distance = (Vector((0.10, 0.02, 0.085)) - loc).length
        console.location = Vector((0, 0, 0)) + fh * 0.62 - r * 0.02; console.rotation_euler = (0, 0, math.atan2(-fh.x, fh.y))
        headphones.location = r * 0.285 + fh * 0.02; headphones.location.z = 0
        headphones.rotation_euler = (0, 0, math.atan2(-fh.x, fh.y) + math.radians(8))
        LIGHTS["hero"] = [
            area("h_key", TGT - r * 0.75 + Vector((0, 0, 0.55)) + fh * 0.15, TGT, 42, 0.45, (1.0, 0.72, 0.44)),
            area("h_fill", TGT + r * 0.9 - fh * 0.2 + Vector((0, 0, 0.25)), TGT, 5, 0.9, (0.62, 0.74, 1.0)),
            area("h_rim", TGT + fh * 0.7 + Vector((0, 0, 0.45)) + r * 0.45, TGT, 40, 0.4, (1.0, 0.8, 0.55)),
            area("h_cons", TGT + fh * 0.30 - r * 0.2 + Vector((0, 0, 0.3)), TGT + fh * 0.5, 14, 0.6, (1.0, 0.6, 0.3)),
        ]
        set_visible("hero")
        do_render(os.path.join(SHOTS, "hero-blender%s.png" % sfx), D["shot_res"], 0.0)
        cam.data.dof.use_dof = False
    # ===== detail: ring + cheek pads closed, shallow DOF, raking light =====
    if "detail" in ONLY:
        pose_cheeks("closed"); cart_install()
        ctr = Vector((0.114, 0.0, 0.083))
        az = math.radians(30); dist = 0.68
        loc = ctr + Vector((math.cos(az), math.sin(az), 0.0)) * dist + Vector((0, 0, 0.05))
        cam.data.lens = 85; aim(loc, ctr + Vector((0, 0, 0.0)))
        cam.data.dof.use_dof = True; cam.data.dof.aperture_fstop = 2.8; cam.data.dof.focus_distance = (Vector((0.115, 0, 0.083)) - loc).length
        f, r, u = look_basis(loc, ctr)
        LIGHTS["detail"] = [
            area("d_rake", Vector((0.30, -0.45, 0.14)), ctr, 14, 0.30, (1.0, 0.9, 0.78)),
            area("d_fill", Vector((0.65, 0.35, 0.25)), ctr, 1.6, 0.8, (0.7, 0.8, 1.0)),
            area("d_top", Vector((0.1, 0.0, 0.5)), ctr, 1.2, 0.5, (1.0, 0.9, 0.8)),
        ]
        set_visible("detail")
        do_render(os.path.join(SHOTS, "detail-blender%s.png" % sfx), D["shot_res"], 0.0)
        cam.data.dof.use_dof = False
    # ===== top: 60 degrees, light grey mat =====
    if "top" in ONLY:
        pose_cheeks("open"); cart_install()
        ctr = Vector((0.02, 0.0, 0.14))
        az = math.radians(10); el = math.radians(60); dist = 0.80
        loc = ctr + Vector((math.cos(az) * math.cos(el), math.sin(az) * math.cos(el), math.sin(el))) * dist
        cam.data.lens = 42; aim(loc, ctr); cam.data.dof.use_dof = False
        LIGHTS["top"] = [area("t_key", Vector((0.3, -0.5, 0.9)), ctr, 48, 0.9, (1.0, 0.96, 0.9)),
                         area("t_fill", Vector((0.2, 0.7, 0.5)), ctr, 14, 1.2, (0.9, 0.95, 1.0)),
                         area("t_back", Vector((-0.8, 0.1, 0.5)), ctr, 12, 1.0, (1, 1, 1))]
        set_visible("top")
        do_render(os.path.join(SHOTS, "top-blender%s.png" % sfx), D["shot_res"], 0.0)
    # ===== cartridge: out, lying beside the body, workbench props =====
    if "cartridge" in ONLY:
        pose_cheeks("open")
        az = math.radians(30); dist = 0.72
        loc = Vector((dist * math.cos(az), dist * math.sin(az), 0.32)); tgt = Vector((0.05, 0.02, 0.05))
        f, r, u = look_basis(loc, tgt); fh = Vector((f.x, f.y, 0)).normalized()
        cam.data.lens = 34; tgt = tgt + Vector((0.0, 0.0, 0.0)); aim(loc, tgt); f, r, u = look_basis(loc, tgt)
        aim(loc, tgt + r * 0.14); f, r, u = look_basis(loc, tgt + r * 0.14)
        def cp(rt, fw): return r * rt + fh * fw
        cart_lying(cp(0.30, -0.02))
        cart.location.z = D["carrier_d"] * MM + 0.0008
        # props
        props = []
        def put(o, loc_, rz=0.0):
            o.location = loc_; o.rotation_euler = (0, 0, rz); props.append(o); return o
        mouldA = rbox("mould_A", (120, 120, 28), (0, 0, 14), 6, 3)
        cut(mouldA, cyl("mA_cav", 36.5, 22, (0, 0, 28 - 11 + 0.0), "z", 96))
        union(mouldA, cyl("mA_core", 12, 18, (0, 0, 28 - 22 + 9), "z", 48)); bevel(mouldA, 0.6, 2, 40)
        for ang in (0, 90, 180, 270):
            union(mouldA, cyl("mA_pin", 3.2, 6, (50 * math.cos(math.radians(ang + 45)) * 1.15, 50 * math.sin(math.radians(ang + 45)) * 1.15, 31), "z", 20))
        part_ = mouldA; assign(mouldA, M["mould"]); smooth(mouldA); PARTS.remove(mouldA) if mouldA in PARTS else None
        mouldB = rbox("mould_B", (120, 120, 14), (0, 0, 7), 6, 3)
        cut(mouldB, cyl("mB_pour", 5, 20, (0, 0, 7), "z", 24))
        for ang in (45, 135, 225, 315):
            cut(mouldB, cyl("mB_hole", 3.5, 8, (57 * math.cos(math.radians(ang)) * 1.0, 57 * math.sin(math.radians(ang)) * 1.0, 14), "z", 20))
        bevel(mouldB, 0.6, 2, 40); assign(mouldB, M["mould"]); smooth(mouldB)
        put(mouldA, cp(0.37, 0.17), math.radians(24))
        put(mouldB, cp(0.17, 0.33), math.radians(-10))
        mouldB.location.z = 0
        # spare carrier (printed, empty) + spare pad + spare arm + screws + hex key
        sc = cyl("spare_carrier", D["carrier_r"], D["carrier_d"], (0, 0, D["carrier_d"] / 2), "z", 96)
        cut(sc, cyl("sc_bore", D["ring_r"] + 0.15, 16, (0, 0, D["carrier_d"] - 6), "z", 96))
        bevel(sc, 0.8, 2); assign(sc, M["carrier"]); smooth(sc)
        put(sc, cp(0.33, -0.19), 0.3)
        sp = bpy.data.objects.new("spare_pad", bpy.data.meshes.new("spare_pad_m")); bpy.context.collection.objects.link(sp)
        pp = rbox("pp_tmp", (24, 60, 88), (0, 0, 0), 11.0, 8); sp.data = pp.data; bpy.data.objects.remove(pp, do_unlink=True)
        assign(sp, M["pad"]); smooth(sp); sp.rotation_euler = (math.pi / 2, 0, 0)
        put(sp, cp(0.45, 0.0) + Vector((0, 0, 0.012)), math.radians(40)); sp.rotation_euler = (math.pi / 2, 0, math.radians(40)); sp.location.z = 0.012
        for k in range(2):
            sa = rbox("spare_arm", (7, 36, 9), (0, 0, 0), 1.0, 2); assign(sa, M["alu"]); smooth(sa)
            put(sa, cp(0.14 + 0.05 * k, -0.20 - 0.015 * k) + Vector((0, 0, 0.0045)), math.radians(70 + 8 * k))
        hexk = bpy.data.objects.new("hexkey", None)
        pts = [(0, 0, 0), (60, 0, 0), (60, 0, 0), (60, 0, 0)]
        kc = bpy.data.curves.new("hexkey_c", "CURVE"); kc.dimensions = "3D"; sp2 = kc.splines.new("POLY"); sp2.points.add(2)
        for p_, v_ in zip(sp2.points, [(0, 0, 0), (0, 0, 0.002), (0, 0.075, 0.002)]): p_.co = (v_[0], v_[1], v_[2], 1)
        sp2.points[0].co = (0.0, 0.0, 0.0, 1); sp2.points[1].co = (0.0, 0.07, 0.0, 1); sp2.points[2].co = (0.045, 0.07, 0.0, 1)
        kc.bevel_depth = 0.0026; kc.bevel_resolution = 3; kc.use_fill_caps = True
        hk = bpy.data.objects.new("hexkey", kc); bpy.context.collection.objects.link(hk); active(hk); bpy.ops.object.convert(target="MESH")
        hk = bpy.context.active_object; assign(hk, make_mat("Hexkey", srgb("#2a2a2c"), 0.35, 0.9, 0.5)); smooth(hk)
        put(hk, cp(0.10, -0.19) + Vector((0, 0, 0.0025)), math.radians(15))
        bpy.data.objects.remove(hexk, do_unlink=True)
        for k in range(3):
            scw = cyl("screw", 3.0, 8, (0, 0, 4), "z", 20); union(scw, cyl("sh", 5.2, 2.5, (0, 0, 9.2), "z", 20)); assign(scw, M["alu"]); smooth(scw)
            scw.rotation_euler = (math.pi / 2, 0, 0); put(scw, cp(0.03 + 0.025 * k, -0.20 + 0.012 * k) + Vector((0, 0, 0.0045)), 0.5 + k)
            scw.rotation_euler = (math.pi / 2, 0, 0.5 + k * 1.1); scw.location.z = 0.0045
        for o in props: ENV["cartridge"].append(o)
        LIGHTS["cartridge"] = [area("c_key", tgt - r * 0.6 + Vector((0.2, 0, 0.9)), tgt, 36, 0.8, (1.0, 0.93, 0.82)),
                               area("c_fill", tgt + r * 0.9 + Vector((0.2, 0.0, 0.3)), tgt, 12, 1.2, (0.88, 0.93, 1.0)),
                               area("c_top", Vector((0.0, 0.0, 1.1)), tgt, 18, 1.2, (1, 1, 1))]
        for o in props: o.hide_render = False
        set_visible("cartridge")
        for o in props: o.hide_render = False
        do_render(os.path.join(SHOTS, "cartridge-blender%s.png" % sfx), D["shot_res"], 0.0)
        for o in props: o.hide_render = True
print("RENDERS done t=%.1fs" % (time.time() - t0), flush=True)

# ----------------------------------------------------------------------------------------
# Save blend (assembly state), STLs, viewer GLB (object only, flat colours)
# ----------------------------------------------------------------------------------------
if DO_EXPORT:
    pose_cheeks("open"); cart_install(); set_visible("assembly")
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(BLEND, "fart_valve.blend"))
    def stl(o, name):
        active(o)
        kw = dict(filepath=os.path.join(STL, name + ".stl"), global_scale=1000.0)
        try:
            bpy.ops.wm.stl_export(export_selected_objects=True, apply_modifiers=True, **kw)
        except Exception:
            bpy.ops.export_mesh.stl(use_selection=True, use_mesh_modifiers=True, **kw)
    # printed parts in their assembled places (mm); the ring carrier is exported in its own frame, rotated onto the face
    for o, nm in ((bpy.data.objects["body_top"], "body_top_shell"), (bpy.data.objects["body_base"], "body_base"), (bezel, "bezel"), (carrier, "ring_carrier")):
        stl(o, nm)
    # mould halves exist only in the cartridge scene; rebuild quick copies for the STL set
    for nm in ("mould_A", "mould_B"):
        if nm in bpy.data.objects:
            o = bpy.data.objects[nm]; o.hide_render = False; o.location = (0, 0, 0); o.rotation_euler = (0, 0, 0); stl(o, "ring_" + nm.lower())
    # GLB
    def flat_copy(m):
        n = bpy.data.materials.new("viewer_" + m.name); n.use_nodes = True
        b0 = m.node_tree.nodes["Principled BSDF"]; b = n.node_tree.nodes["Principled BSDF"]
        col = b0.inputs["Base Color"].default_value
        b.inputs["Base Color"].default_value = col
        for k in ("Roughness", "Metallic"): b.inputs[k].default_value = b0.inputs[k].default_value
        if "Emission Strength" in b0.inputs and b0.inputs["Emission Strength"].default_value > 0:
            b.inputs["Emission Color"].default_value = b0.inputs["Emission Color"].default_value
            b.inputs["Emission Strength"].default_value = min(1.0, b0.inputs["Emission Strength"].default_value)
        return n
    flat = {k: flat_copy(v) for k, v in M.items()}
    # glass tray: light-grey translucent
    t = flat["tray"]; tb = t.node_tree.nodes["Principled BSDF"]; tb.inputs["Alpha"].default_value = 0.28; tb.inputs["Base Color"].default_value = (0.8, 0.9, 0.95, 1)
    for a_, v_ in (("surface_render_method", "BLENDED"), ("blend_method", "BLEND")):
        try: setattr(t, a_, v_)
        except Exception: pass
    inv = {id(v): k for k, v in M.items()}
    sel = []
    for o in PARTS:
        if o.type != "MESH" or o.name.startswith(("mould", "spare")): continue
        new = []
        for sl in o.data.materials:
            k = inv.get(id(sl)); new.append(flat[k] if k else sl)
        o.data.materials.clear()
        for m_ in new: o.data.materials.append(m_)
        sel.append(o)
    bpy.ops.object.select_all(action="DESELECT")
    for o in sel + [cart, CHEEKS["L"][0], CHEEKS["R"][0]]: o.select_set(True)
    for o in list(sel):
        pass
    active(sel[0])
    for o in sel + [cart, CHEEKS["L"][0], CHEEKS["R"][0]]: o.select_set(True)
    glb = os.path.join(RENDER, "model.glb")
    bpy.ops.export_scene.gltf(filepath=glb, export_format="GLB", use_selection=True, export_apply=True,
                              export_draco_mesh_compression_enable=False, export_yup=True)
    print("GLB %.2f MB, %d objects" % (os.path.getsize(glb) / 1e6, len(sel)))
print("DONE total %.1fs" % (time.time() - t0))
