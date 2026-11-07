"""Third Person VR rig: printable parts, mannequin assembly, GLB and Cycles renders.

Run:  /Applications/Blender.app/Contents/MacOS/Blender -b -P cad/build_third_person_vr.py -- [--samples 128] [--scale 1.0] [--only hero,a,b,c] [--no-render]
Parts are polygon meshes (Blender booleans), not parametric solids. Units: metres in the scene, STLs are written in mm.
"""
import bpy, bmesh, math, os, sys, time, random
from mathutils import Vector, Matrix, Euler

T0 = time.time()
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
def arg(name, default):
    a = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    if name in a:
        i = a.index(name); return a[i + 1] if i + 1 < len(a) else True
    return default
SAMPLES = int(arg("--samples", "128")); RSCALE = float(arg("--scale", "1.0"))
ONLY = [s for s in str(arg("--only", "hero,a,b,c")).split(",") if s]
NO_RENDER = "--no-render" in sys.argv

# ---------------------------------------------------------------- dimensions (mm unless noted)
D = dict(
    pod_w=86, pod_h=34, pod_d=40, pod_r=8, pod_wall=4, lens_gap=60, lens_hole_d=13, pod_boss_d=19, pod_boss_h=10.5, pod_pilot_d=6.4, pod_pilot_depth=10,
    lid_t=4, lid_hole_d=11,
    sled_x=164, sled_y=164, sled_h=12, sled_floor=3, bank=(70, 150, 27), pi=(56, 85), pi_gap=6, sled_margin=12, slot=(4, 30), slot_y=62,
    clip_pole_d=25, clip_clear=0.8, clip_wall=3.6, clip_w=10, clip_gap=19, clip_eye_od=11, clip_eye_id=5.6,
    pole_d=25, cable_d=4.4,
    # metres
    H_total=1.77, backpack=(0.34, 0.20, 0.52), pole_base_z=1.30, pole_y=-0.355, pod_pos=(0.0, -1.15, 2.18), pod_pitch=13.0,
)
mm = lambda v: v / 1000.0

scene = bpy.context.scene
for o in list(bpy.data.objects): bpy.data.objects.remove(o, do_unlink=True)
scene.unit_settings.system = "METRIC"

# ---------------------------------------------------------------- helpers
def srgb(h):
    h = h.lstrip("#"); c = [int(h[i:i+2], 16) / 255 for i in (0, 2, 4)]
    return tuple(((x / 12.92) if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4) for x in c)

def mat(name, rgb, rough=0.5, metal=0.0, coat=0.0, emit=None, emit_s=0.0):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*rgb[:3], 1)
    b.inputs["Roughness"].default_value = rough; b.inputs["Metallic"].default_value = metal
    if coat: b.inputs["Coat Weight"].default_value = coat; b.inputs["Coat Roughness"].default_value = 0.1
    if emit:
        b.inputs["Emission Color"].default_value = (*emit, 1); b.inputs["Emission Strength"].default_value = emit_s
    return m

def bump_noise(m, scale, strength, dist=0.001, kind="NOISE"):
    nt = m.node_tree; b = nt.nodes["Principled BSDF"]
    tc = nt.nodes.new("ShaderNodeTexCoord")
    if kind == "CHECK":
        t = nt.nodes.new("ShaderNodeTexChecker"); t.inputs["Scale"].default_value = scale
        mp = nt.nodes.new("ShaderNodeMapping"); mp.inputs["Rotation"].default_value = (0, 0, math.radians(45))
        nt.links.new(tc.outputs["Object"], mp.inputs["Vector"]); nt.links.new(mp.outputs["Vector"], t.inputs["Vector"])
        out = t.outputs["Fac"]
    else:
        t = nt.nodes.new("ShaderNodeTexNoise"); t.inputs["Scale"].default_value = scale; t.inputs["Detail"].default_value = 8
        nt.links.new(tc.outputs["Object"], t.inputs["Vector"]); out = t.outputs["Fac"]
    bp = nt.nodes.new("ShaderNodeBump"); bp.inputs["Strength"].default_value = strength; bp.inputs["Distance"].default_value = dist
    nt.links.new(out, bp.inputs["Height"]); nt.links.new(bp.outputs["Normal"], b.inputs["Normal"])

M = dict(
    clay=mat("Clay", srgb("#A39D95"), 0.72),
    pod=mat("Pod_charcoal", srgb("#2C2D30"), 0.5),
    orange=mat("Orange_PETG", srgb("#F2640C"), 0.38),
    carbon=mat("Carbon", srgb("#101112"), 0.28, 0.0, 0.5),
    pack=mat("Backpack", srgb("#566370"), 0.88),
    strap=mat("Webbing", srgb("#1B1D20"), 0.9),
    white=mat("Headset_white", srgb("#D9D8D3"), 0.42),
    visor=mat("Headset_visor", srgb("#0B0C0E"), 0.12, 0.0, 0.3),
    cable=mat("Cable", srgb("#0C0D0E"), 0.45),
    pcb=mat("PCB", srgb("#0E5A32"), 0.5),
    metal=mat("Silver", srgb("#BDBFC2"), 0.3, 1.0),
    black=mat("Black_plastic", srgb("#0A0A0B"), 0.5),
    bank=mat("Powerbank", srgb("#1D2026"), 0.38, 0.0, 0.2),
    label=mat("Bank_label", srgb("#8D9298"), 0.5),
    mount=mat("Mount_gunmetal", srgb("#3B3E43"), 0.35, 0.9),
    glass=mat("Lens_glass", srgb("#0A1220"), 0.04, 0.0, 1.0),
)
bump_noise(M["pack"], 900, 0.5, 0.0006); bump_noise(M["carbon"], 520, 0.35, 0.0004, "CHECK")

def finish(bm, angle=38):
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    lim = math.radians(angle)
    for e in bm.edges:
        e.smooth = not (len(e.link_faces) == 2 and e.calc_face_angle(0) > lim)
    for f in bm.faces: f.smooth = True

def to_obj(bm, name, m=None, angle=38):
    finish(bm, angle)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); scene.collection.objects.link(o)
    if m: o.data.materials.append(m)
    return o

def reshade(o, angle=38):
    bm = bmesh.new(); bm.from_mesh(o.data); finish(bm, angle); bm.to_mesh(o.data); bm.free()

def dirmat(p1, p2):
    p1, p2 = Vector(p1), Vector(p2); d = p2 - p1
    up = "X" if abs(d.normalized().x) < 0.9 else "Y"
    return Matrix.Translation((p1 + p2) / 2) @ d.to_track_quat("Z", up).to_matrix().to_4x4(), d.length

def add_cyl(bm, p1, p2, r1, r2=None, seg=16):
    M_, L = dirmat(p1, p2)
    if L < 1e-6: return
    bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=seg, radius1=r1, radius2=r1 if r2 is None else r2, depth=L, matrix=M_)

def add_sphere(bm, c, r, seg=20, scale=(1, 1, 1), rot=None):
    m = Matrix.Translation(c)
    if rot: m = m @ Euler(rot).to_matrix().to_4x4()
    m = m @ Matrix.Diagonal((*scale, 1))
    bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=max(8, seg // 2), radius=r, matrix=m)

def tube(name, pts, r, m, seg=14, joints=True):
    bm = bmesh.new()
    for a, b in zip(pts, pts[1:]): add_cyl(bm, a, b, r, seg=seg)
    if joints:
        for p in pts[1:-1]: add_sphere(bm, p, r, seg=seg)
    return to_obj(bm, name, m)

def limb(name, p1, p2, r1, r2, m, cap=True):
    bm = bmesh.new(); add_cyl(bm, p1, p2, r1, r2, seg=20)
    if cap: add_sphere(bm, p1, r1, 20); add_sphere(bm, p2, r2, 20)
    return to_obj(bm, name, m)

def ellipsoid(name, c, radii, m, rot=None, seg=32):
    bm = bmesh.new(); add_sphere(bm, c, 1.0, seg, radii, rot); return to_obj(bm, name, m)

def rbox_bm(size, r, seg=3, center=(0, 0, 0)):
    bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts: v.co = Vector((v.co.x * size[0], v.co.y * size[1], v.co.z * size[2]))
    if r > 0: bmesh.ops.bevel(bm, geom=list(bm.edges), offset=r, segments=seg, affect="EDGES", profile=0.5)
    bmesh.ops.translate(bm, verts=bm.verts, vec=Vector(center)); return bm

def rbox(name, size, r, m, center=(0, 0, 0), seg=3):
    return to_obj(rbox_bm(size, r, seg, center), name, m)

def prism_y(w, h, depth, r, y0, seg=7, front_bevel=0.0):
    """Rounded-rectangle prism along +Y starting at y0 (profile in XZ)."""
    bm = bmesh.new(); prof = []
    cx, cz = w / 2 - r, h / 2 - r
    for sx, sz, a0 in ((1, 1, 0), (-1, 1, 90), (-1, -1, 180), (1, -1, 270)):
        for i in range(seg + 1):
            a = math.radians(a0 + 90 * i / seg); prof.append((sx * cx + r * math.cos(a), sz * cz + r * math.sin(a)))
    ring0 = [bm.verts.new((x, y0, z)) for x, z in prof]; ring1 = [bm.verts.new((x, y0 + depth, z)) for x, z in prof]
    n = len(prof)
    for i in range(n): bm.faces.new((ring0[i], ring0[(i + 1) % n], ring1[(i + 1) % n], ring1[i]))
    bm.faces.new(ring0[::-1]); bm.faces.new(ring1)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    if front_bevel > 0:
        es = [e for e in bm.edges if all(abs(v.co.y - (y0 + depth)) < 1e-9 for v in e.verts)]
        bmesh.ops.bevel(bm, geom=es, offset=front_bevel, segments=3, affect="EDGES", profile=0.5)
    return bm

def cyl_obj(name, p1, p2, r, seg=48):
    bm = bmesh.new(); add_cyl(bm, p1, p2, r, seg=seg); return to_obj(bm, name)

def boolean(target, cutter, op="DIFFERENCE", keep=False):
    md = target.modifiers.new("b", "BOOLEAN"); md.object = cutter; md.operation = op; md.solver = "EXACT"
    bpy.ops.object.select_all(action="DESELECT"); bpy.context.view_layer.objects.active = target; target.select_set(True)
    bpy.ops.object.modifier_apply(modifier=md.name)
    if not keep: bpy.data.objects.remove(cutter, do_unlink=True)

def nonmanifold(o):
    bm = bmesh.new(); bm.from_mesh(o.data); n = sum(1 for e in bm.edges if not e.is_manifold); f = len(bm.faces); bm.free(); return n, f

def chaikin(pts, it=2):
    pts = [Vector(p) for p in pts]
    for _ in range(it):
        out = [pts[0]]
        for a, b in zip(pts, pts[1:]): out += [a * 0.75 + b * 0.25, a * 0.25 + b * 0.75]
        out.append(pts[-1]); pts = out
    return pts

# ================================================================ 1. PRINTED PARTS (built at origin, exported, then placed)
PARTS = {}
# ---- camera pod: local X width, +Y forward (lenses), Z up. origin = body centre.
w, h, d, r = mm(D["pod_w"]), mm(D["pod_h"]), mm(D["pod_d"]), mm(D["pod_r"])
pod = to_obj(prism_y(w, h, d, r, -d / 2, front_bevel=0.0025), "camera-pod", M["pod"])
wall = mm(D["pod_wall"])
cav = to_obj(prism_y(w - 2 * wall, h - 2 * wall + 0.002, d - wall + 0.002, mm(4.5), -d / 2 - 0.001), "cav")
boolean(pod, cav)
for sx in (-1, 1):
    boolean(pod, cyl_obj("hole", (sx * mm(D["lens_gap"]) / 2, d / 2 - wall - 0.002, 0), (sx * mm(D["lens_gap"]) / 2, d / 2 + 0.004, 0), mm(D["lens_hole_d"]) / 2))
boss = cyl_obj("boss", (0, 0, -h / 2 - mm(D["pod_boss_h"])), (0, 0, -h / 2 + 0.003), mm(D["pod_boss_d"]) / 2)
boolean(pod, boss, "UNION")
boolean(pod, cyl_obj("pilot", (0, 0, -h / 2 - mm(D["pod_boss_h"]) - 0.001), (0, 0, -h / 2 - mm(D["pod_boss_h"]) + mm(D["pod_pilot_depth"])), mm(D["pod_pilot_d"]) / 2, 40))
reshade(pod, 40); PARTS["camera-pod"] = pod

lid = to_obj(prism_y(w, h, mm(D["lid_t"]), r, -d / 2 - mm(D["lid_t"])), "camera-pod-lid", M["orange"])
boolean(lid, cyl_obj("lh", (0, -d / 2 - 0.01, -h / 2 + mm(9)), (0, -d / 2 + 0.01, -h / 2 + mm(9)), mm(D["lid_hole_d"]) / 2, 40))
reshade(lid, 40); PARTS["camera-pod-lid"] = lid

# ---- Pi + power bank sled: local X, Y in the plate plane, Z up from plate bottom (z=0), pockets open to +Z
SX, SY, SH = mm(D["sled_x"]), mm(D["sled_y"]), mm(D["sled_h"]); fl = mm(D["sled_floor"])
sled = rbox("pi-battery-sled", (SX, SY, SH), mm(3), M["orange"], center=(0, 0, SH / 2), seg=2)
bx, by, bz = [mm(v) for v in D["bank"]]; pw, pl = mm(D["pi"][0]), mm(D["pi"][1])
mg = mm(D["sled_margin"]); gap = mm(D["pi_gap"])
pocket_pi_w = pw + mm(4); pocket_bank_w = bx + mm(4)
x_pi = -SX / 2 + mg + pocket_pi_w / 2; x_bank = x_pi + pocket_pi_w / 2 + gap + pocket_bank_w / 2
cutters = [rbox("c1", (pocket_bank_w, by + mm(4), 0.03), mm(5), None, center=(x_bank, 0, fl + 0.015)),
           rbox("c2", (pocket_pi_w, pl + mm(5), 0.03), mm(4), None, center=(x_pi, 0, fl + 0.015))]
for c in cutters: boolean(sled, c)
sx_, sy_ = mm(D["slot"][0]), mm(D["slot"][1])
for sx in (-1, 1):
    for sy in (-1, 1):
        boolean(sled, rbox("slot", (sx_, sy_, 0.03), mm(1.5), None, center=(sx * (SX / 2 - mg / 2), sy * mm(D["slot_y"]), 0.0)))
boolean(sled, rbox("vent", (mm(34), mm(34), 0.03), mm(3), None, center=(x_pi, mm(-8), 0)))
for sy in (-1, 1):  # cable notches through the pocket end walls
    boolean(sled, rbox("n", (mm(26), mm(14), 0.03), mm(3), None, center=(x_pi, sy * (pl / 2 + mm(8)), fl + 0.016 + mm(1))))
boolean(sled, rbox("n2", (mm(18), mm(14), 0.03), mm(3), None, center=(x_bank, by / 2 + mm(2), fl + 0.016 + mm(1))))
reshade(sled, 40); PARTS["pi-battery-sled"] = sled

# ---- cable clip: local Z = pole axis, eyelet toward +Y, snap opening toward -Y
pr = mm(D["clip_pole_d"]) / 2 + mm(D["clip_clear"]); cw = mm(D["clip_w"]); ro = pr + mm(D["clip_wall"])
bm = bmesh.new(); add_cyl(bm, (0, 0, -cw / 2), (0, 0, cw / 2), ro, seg=64)
eye_c = ro + mm(D["clip_eye_od"]) / 2 - mm(2.2)
add_cyl(bm, (0, eye_c, -cw / 2), (0, eye_c, cw / 2), mm(D["clip_eye_od"]) / 2, seg=40)
clip = to_obj(bm, "cable-clip", M["orange"])
boolean(clip, cyl_obj("in", (0, 0, -0.02), (0, 0, 0.02), pr, 64))
boolean(clip, cyl_obj("eye", (0, eye_c, -0.02), (0, eye_c, 0.02), mm(D["clip_eye_id"]) / 2, 32))
boolean(clip, rbox("gap", (mm(D["clip_gap"]), 0.03, 0.03), 0, None, center=(0, -ro, 0)))
reshade(clip, 40); PARTS["cable-clip"] = clip
CLIP_EYE = eye_c

stl_report = {}
def export_stls():
    for name, o in [("camera-pod", pod), ("pi-battery-sled", sled), ("cable-clip", clip), ("camera-pod-lid", lid)]:
        bpy.ops.object.select_all(action="DESELECT"); o.select_set(True); bpy.context.view_layer.objects.active = o
        p = os.path.join(HERE, name + ".stl")
        bpy.ops.wm.stl_export(filepath=p, export_selected_objects=True, global_scale=1000.0, apply_modifiers=True, ascii_format=False)
        bb = [Vector(c) for c in o.bound_box]
        dims = [(max(v[i] for v in bb) - min(v[i] for v in bb)) * 1000 for i in range(3)]
        stl_report[name] = (dims, nonmanifold(o), os.path.getsize(p))
        print("STL", name, ["%.1f" % x for x in dims], "nonmanifold edges/faces", nonmanifold(o), os.path.getsize(p), "bytes")
export_stls()

# ================================================================ 2. ASSEMBLY
RIG, MAN = [], []
def reg(o, group): group.append(o); return o

# ---- mannequin (+Y is forward, feet on z=0)
HIP_H = 0.951
def seg(p, ang, L, dx=0.0):
    a = math.radians(ang); return Vector((p.x + dx, p.y + L * math.sin(a), p.z - L * math.cos(a)))
FOOT_R0, FOOT_R1 = 0.034, 0.027
def leg(side, a1, a2, toe_up=None):
    hip = Vector((side * 0.095, 0.0, HIP_H)); knee = seg(hip, a1, 0.46, side * 0.004); ank = seg(knee, a2, 0.44, side * 0.004)
    heel = ank + Vector((0, -0.04, -0.065))
    if toe_up is None:
        s = max(-0.95, min(0.95, (heel.z - FOOT_R1) / 0.25)); toe_up = -math.degrees(math.asin(s))
    toe = heel + Vector((0, 0.25 * math.cos(math.radians(toe_up)), 0.25 * math.sin(math.radians(toe_up))))
    n = "R" if side < 0 else "L"
    reg(limb("man_thigh_" + n, hip, knee, 0.086, 0.060, M["clay"]), MAN)
    reg(limb("man_shin_" + n, knee, ank, 0.058, 0.041, M["clay"]), MAN)
    reg(limb("man_foot_" + n, heel, toe, FOOT_R0, FOOT_R1, M["clay"]), MAN)
    return ank
leg(+1, 24, 8, 12.0)      # left leg forward, heel strike
leg(-1, -16, -40)         # right leg back, toe push-off
# pelvis / torso / neck / head
reg(loft := None, MAN) if False else None
def loft(name, rings, m, seg=32):
    bm = bmesh.new(); vr = []
    for (cx, cy, cz, rx, ry) in rings:
        vr.append([bm.verts.new((cx + rx * math.cos(2 * math.pi * i / seg), cy + ry * math.sin(2 * math.pi * i / seg), cz)) for i in range(seg)])
    for a, b in zip(vr, vr[1:]):
        for i in range(seg): bm.faces.new((a[i], a[(i + 1) % seg], b[(i + 1) % seg], b[i]))
    bm.faces.new(vr[0][::-1]); bm.faces.new(vr[-1])
    return to_obj(bm, name, m, 50)
torso = [(0, 0, 0.86, 0.11, 0.08), (0, 0, 0.90, 0.165, 0.108), (0, 0, 1.02, 0.160, 0.104), (0, 0, 1.10, 0.145, 0.098), (0, 0, 1.22, 0.162, 0.110),
         (0, 0.005, 1.34, 0.180, 0.120), (0, 0, 1.42, 0.186, 0.112), (0, 0, 1.47, 0.145, 0.088), (0, 0, 1.505, 0.06, 0.05), (0, 0, 1.52, 0.04, 0.04)]
reg(loft("man_torso", torso, M["clay"]), MAN)
reg(ellipsoid("man_pelvis", (0, 0, 0.93), (0.172, 0.112, 0.092), M["clay"]), MAN)
for s in (-1, 1): reg(ellipsoid("man_shoulder_%d" % s, (s * 0.195, 0.0, 1.425), (0.052, 0.052, 0.052), M["clay"]), MAN)
reg(limb("man_neck", (0, 0.005, 1.50), (0, 0.012, 1.60), 0.045, 0.040, M["clay"]), MAN)
HEAD_C = Vector((0, 0.012, 1.665)); HEAD_R = (0.080, 0.096, 0.108)
reg(ellipsoid("man_head", HEAD_C, HEAD_R, M["clay"], seg=40), MAN)
# arms: right arm forward (opposite the forward left leg)
def arm(side, a1, a2):
    sh = Vector((side * 0.195, 0.0, 1.425)); el = seg(sh, a1, 0.29, side * 0.03); wr = seg(el, a2, 0.26, side * 0.015)
    n = "R" if side < 0 else "L"
    reg(limb("man_uarm_" + n, sh, el, 0.050, 0.041, M["clay"]), MAN)
    reg(limb("man_farm_" + n, el, wr, 0.040, 0.031, M["clay"]), MAN)
    reg(ellipsoid("man_hand_" + n, wr + (wr - el).normalized() * 0.05, (0.026, 0.04, 0.052) if False else (0.03, 0.03, 0.06), M["clay"], rot=(math.radians(a2), 0, 0)), MAN)
arm(-1, 24, 58); arm(+1, -20, -12)

# ---- headset (generic, no branding)
hs = Vector((0, 0.128, 1.672))
reg(rbox("hs_visor", (0.188, 0.092, 0.092), 0.032, M["white"], center=hs, seg=5), RIG)
reg(rbox("hs_face", (0.172, 0.006, 0.078), 0.02, M["visor"], center=(0, hs.y + 0.046, hs.z), seg=4), RIG)
for sx in (-1, 1): reg(ellipsoid("hs_sensor_%d" % sx, (sx * 0.062, hs.y + 0.050, hs.z + 0.002), (0.0075, 0.003, 0.0075), M["black"], seg=12), RIG)
band = []
for i in range(0, 25):
    a = 2 * math.pi * i / 24 + math.pi * 0.0
    band.append((HEAD_C.x + (HEAD_R[0] + 0.011) * math.sin(a), HEAD_C.y + (HEAD_R[1] + 0.012) * math.cos(a), 1.695))
reg(tube("hs_band", band, 0.0105, M["strap"], seg=12), RIG)
top = []
for i in range(0, 13):
    y = 0.07 - 0.15 * i / 12; zz = HEAD_C.z + HEAD_R[2] * math.sqrt(max(0.0, 1 - ((y - HEAD_C.y) / HEAD_R[1]) ** 2)) + 0.006
    top.append((0, y, zz))
reg(tube("hs_top", top, 0.0095, M["strap"], seg=12), RIG)
reg(rbox("hs_rear", (0.115, 0.05, 0.075), 0.02, M["white"], center=(0, HEAD_C.y - HEAD_R[1] - 0.012, 1.68), seg=4), RIG)

# ---- backpack, straps, mount
BP = D["backpack"]; BP_REAR = -0.318; BP_Z0 = 1.015
bp_c = (0, BP_REAR + BP[1] / 2, BP_Z0 + BP[2] / 2)
reg(rbox("backpack", BP, 0.05, M["pack"], center=bp_c, seg=5), RIG)
reg(rbox("backpack_pocket", (0.26, 0.05, 0.20), 0.02, M["pack"], center=(0, BP_REAR - 0.018, 1.17), seg=3), RIG) if False else None
reg(rbox("backpack_flap", (BP[0] - 0.012, BP[1] + 0.014, 0.17), 0.045, M["pack"], center=(0, bp_c[1], BP_Z0 + BP[2] - 0.085), seg=5), RIG)
for sx in (-1, 1):
    reg(rbox("backpack_side_%d" % sx, (0.075, 0.15, 0.26), 0.032, M["pack"], center=(sx * (BP[0] / 2 + 0.012), bp_c[1] + 0.01, BP_Z0 + 0.20), seg=4), RIG)
reg(tube("backpack_handle", [(-0.06, bp_c[1], BP_Z0 + BP[2] + 0.004), (-0.05, bp_c[1], BP_Z0 + BP[2] + 0.05), (0.05, bp_c[1], BP_Z0 + BP[2] + 0.05), (0.06, bp_c[1], BP_Z0 + BP[2] + 0.004)], 0.008, M["strap"], seg=8), RIG)
for sx in (-1, 1):
    pts = [(sx * 0.115, -0.12, 1.50), (sx * 0.135, -0.05, 1.525), (sx * 0.148, 0.04, 1.497), (sx * 0.125, 0.112, 1.40), (sx * 0.118, 0.114, 1.29)]
    reg(tube("strap_%d" % sx, chaikin(pts, 2), 0.0155, M["strap"], seg=10, joints=True), RIG)
reg(tube("chest_strap", [(-0.128, 0.115, 1.34), (0.0, 0.126, 1.34), (0.128, 0.115, 1.34)], 0.009, M["strap"], seg=8), RIG)
PX = D["pole_y"]; ZB = D["pole_base_z"]
reg(rbox("mount_plate", (0.14, 0.022, 0.20), 0.008, M["mount"], center=(0, BP_REAR - 0.011, 1.405), seg=3), RIG)
reg(rbox("mount_block", (0.070, 0.046, 0.090), 0.014, M["mount"], center=(0, BP_REAR - 0.040, 1.405), seg=4), RIG)
# ---- pod placement, ball head, pole (straight carbon pole leaning back, so it stays below and outside the camera's view)
POD_C = Vector(D["pod_pos"]); PITCH = D["pod_pitch"]
POD_M = Matrix.Translation(POD_C) @ Matrix.Rotation(-math.radians(PITCH), 4, "X")
n_down = POD_M.to_3x3() @ Vector((0, 0, -1))
BALL_R = 0.0145
BALL = POD_C + n_down * (h / 2 + mm(D["pod_boss_h"]) + BALL_R - 0.002)
P0 = Vector((0, PX, ZB)); B = BALL
pdir = (B - P0).normalized(); POLE_LEN = (B - P0).length
for nm, o in (("camera-pod", pod), ("camera-pod-lid", lid)):
    o.matrix_world = POD_M; reg(o, RIG)
sled.matrix_world = Matrix.Translation((0, BP_REAR, BP_Z0 + 0.092)) @ Matrix.Rotation(math.radians(90), 4, "X"); reg(sled, RIG)
for sx in (-1, 1):
    bm = bmesh.new(); add_cyl(bm, (0, 0.0105, 0), (0, d / 2 - 0.0012, 0), 0.0058, seg=32)
    bm2 = bmesh.new(); add_cyl(bm2, (0, d / 2 - 0.0013, 0), (0, d / 2 - 0.0006, 0), 0.0050, seg=32)
    for bmx, nm, m_ in ((bm, "lens_barrel", M["black"]), (bm2, "lens_glass", M["glass"])):
        o = to_obj(bmx, "%s_%d" % (nm, sx), m_); o.matrix_world = POD_M @ Matrix.Translation((sx * mm(D["lens_gap"]) / 2, 0, 0)); reg(o, RIG)
bm = bmesh.new(); add_sphere(bm, BALL, BALL_R, 32)
add_cyl(bm, BALL, BALL + n_down * -(0.026), 0.0045, seg=20)
add_cyl(bm, BALL - pdir * 0.004, BALL - pdir * 0.040, 0.0175, seg=32)
reg(to_obj(bm, "ball_head", M["mount"]), RIG)
r_pole = mm(D["pole_d"]) / 2
bm = bmesh.new(); add_cyl(bm, P0, B - pdir * 0.03, r_pole, seg=40)
reg(to_obj(bm, "pole_carbon", M["carbon"]), RIG)
# clamp on the mount, tilted with the pole, and a telescope lock ring half way up
bm = bmesh.new(); add_cyl(bm, P0 - pdir * 0.03, P0 + pdir * 0.11, 0.0185, seg=32); add_cyl(bm, P0 + pdir * 0.11, P0 + pdir * 0.124, 0.0215, seg=32)
reg(to_obj(bm, "mount_clamp", M["mount"]), RIG)
bm = bmesh.new(); mid = P0 + pdir * (POLE_LEN * 0.5); add_cyl(bm, mid - pdir * 0.02, mid + pdir * 0.02, 0.0175, seg=32); add_cyl(bm, mid + pdir * 0.02, mid + pdir * 0.032, 0.0155, seg=32)
reg(to_obj(bm, "pole_lock", M["mount"]), RIG)

# ---- cable + clips along the underside (back-down side) of the pole
off = CLIP_EYE  # cable axis = eyelet centre distance from the pole axis
aperp = Vector((0, -pdir.z, pdir.y)); aperp = aperp if aperp.y < 0 else -aperp
def clip_at(name, center, axis, perp):
    z = axis.normalized(); y = perp.normalized(); x = y.cross(z)
    o = bpy.data.objects.new(name, clip.data); scene.collection.objects.link(o)
    o.matrix_world = Matrix.Translation(center) @ Matrix((x, y, z)).transposed().to_4x4()
    return reg(o, RIG)
lid_port = POD_M @ Vector((0, -d / 2 - mm(D["lid_t"]) - 0.001, -h / 2 + mm(9)))
near_ball = B - pdir * 0.07 + aperp * off
base_pt = P0 + pdir * 0.02 + aperp * off
cable_pts = [lid_port, lid_port + Vector((0, -0.03, -0.012)), near_ball, base_pt, base_pt + Vector((-0.004, -0.012, -0.05)),
             Vector((-0.025, -0.362, 1.215)), Vector((-0.04, -0.342, 1.165))]
reg(tube("cable_main", chaikin(cable_pts, 3), mm(D["cable_d"]) / 2, M["cable"], seg=10), RIG)
for k, s in enumerate((0.075, 0.45, 0.82)):
    clip_at("clip_pole_%d" % k, B - pdir * (s + 0.03), pdir, aperp)
bpy.data.objects.remove(clip, do_unlink=True)   # the master clip sits at the origin; the instances above share its mesh

# ---- Pi, cooler and power bank on the sled (sled local -> world)
SLED_M = sled.matrix_world
def on_sled(o, loc, rot=(0, 0, 0)):
    o.matrix_world = SLED_M @ Matrix.Translation(loc) @ Euler(rot).to_matrix().to_4x4(); return reg(o, RIG)
pz = fl + mm(2.5)
on_sled(rbox("pi_board", (pw, pl, 0.0016), 0.0006, M["pcb"], seg=2), (x_pi, 0, pz + 0.0008))
on_sled(rbox("pi_cooler", (0.036, 0.036, 0.012), 0.002, M["metal"], seg=2), (x_pi + 0.002, -0.005, pz + 0.0016 + 0.006))
bm = bmesh.new(); add_cyl(bm, (0, 0, 0), (0, 0, 0.0035), 0.0155, seg=36)
on_sled(to_obj(bm, "pi_fan", M["black"]), (x_pi + 0.002, -0.005, pz + 0.0016 + 0.012))
on_sled(rbox("pi_header", (0.005, 0.051, 0.009), 0.0006, M["black"], seg=1), (x_pi + pw / 2 - 0.004, -0.010, pz + 0.0016 + 0.0045))
for k, yy in enumerate((0.0155, -0.0015)):
    on_sled(rbox("pi_usb_%d" % k, (0.0135, 0.0175, 0.0155), 0.0006, M["metal"], seg=1), (x_pi - 0.0065 + (0.0 if k == 0 else 0.0), pl / 2 - 0.0085 - k * 0.0, pz + 0.0016 + 0.0078)) if False else None
on_sled(rbox("pi_ports", (0.050, 0.021, 0.0155), 0.0006, M["metal"], seg=1), (x_pi - 0.002, pl / 2 - 0.0085, pz + 0.0016 + 0.0078))
on_sled(rbox("powerbank", (bx, by, bz), mm(8), M["bank"], seg=4), (x_bank, 0, fl + bz / 2 + 0.0005))
on_sled(rbox("bank_label", (0.040, 0.075, 0.0007), 0.0003, M["label"], seg=1), (x_bank, -0.012, fl + bz + 0.0005))
sc = [Vector((x_bank + 0.01, by / 2 + 0.0015, fl + bz * 0.5)), Vector((x_bank + 0.01, by / 2 + 0.03, fl + bz * 0.5 + 0.012)), Vector((x_pi + 0.04, by / 2 + 0.03, fl + 0.05)), Vector((x_pi + pw / 2 - 0.004, pl / 2 + 0.012, pz + 0.014))]
bmcable = [SLED_M @ p for p in chaikin(sc, 3)]
reg(tube("cable_power", bmcable, mm(D["cable_d"]) / 2, M["cable"], seg=10), RIG)

for o in RIG + MAN: pass
bpy.context.view_layer.update()
print("ASSEMBLED %.1fs" % (time.time() - T0))

# ================================================================ 3. SAVE BLEND + GLB (before dressing the scene)
def export_glb():
    bpy.ops.object.select_all(action="DESELECT")
    for o in RIG + MAN: o.select_set(True)
    p = os.path.join(ROOT, "blender", "model.glb")
    bpy.ops.export_scene.gltf(filepath=p, use_selection=True, export_apply=True, export_format="GLB", export_yup=True)
    sz = os.path.getsize(p)
    if sz > 8 * 1024 * 1024:
        bpy.ops.object.select_all(action="DESELECT")
        for o in RIG: o.select_set(True)
        bpy.ops.export_scene.gltf(filepath=p, use_selection=True, export_apply=True, export_format="GLB", export_yup=True); sz = os.path.getsize(p)
        print("GLB without mannequin (too big)")
    print("GLB", sz / 1e6, "MB"); return sz
GLB_SIZE = export_glb()

# ================================================================ 4. SET (render only)
SET, STUDIO = [], []
def setobj(o, grp=SET): grp.append(o); return o
def slab(name, x0, x1, y0, y1, z0, z1, m):
    return setobj(rbox(name, (x1 - x0, y1 - y0, z1 - z0), 0.0, m, center=((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2)))

def paving(name, c1, c2, mort, scale, rough=0.85):
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree; b = nt.nodes["Principled BSDF"]; b.inputs["Roughness"].default_value = rough
    tc = nt.nodes.new("ShaderNodeTexCoord"); br = nt.nodes.new("ShaderNodeTexBrick")
    br.inputs["Color1"].default_value = (*c1, 1); br.inputs["Color2"].default_value = (*c2, 1); br.inputs["Mortar"].default_value = (*mort, 1)
    br.inputs["Scale"].default_value = scale; br.inputs["Mortar Size"].default_value = 0.012; br.inputs["Brick Width"].default_value = 1.0; br.inputs["Row Height"].default_value = 1.0
    br.offset = 0.0; br.squash = 1.0
    nt.links.new(tc.outputs["Object"], br.inputs["Vector"]); nt.links.new(br.outputs["Color"], b.inputs["Base Color"])
    nz = nt.nodes.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 60; bp = nt.nodes.new("ShaderNodeBump"); bp.inputs["Strength"].default_value = 0.15; bp.inputs["Distance"].default_value = 0.002
    nt.links.new(tc.outputs["Object"], nz.inputs["Vector"]); nt.links.new(nz.outputs["Fac"], bp.inputs["Height"]); nt.links.new(bp.outputs["Normal"], b.inputs["Normal"])
    return m
walk = paving("Sidewalk", srgb("#8F8A82"), srgb("#807B74"), srgb("#4B4843"), 0.8)
kerbm = mat("Kerb", srgb("#A19C94"), 0.8); road = mat("Asphalt", srgb("#26272A"), 0.92); bump_noise(road, 400, 0.4, 0.002)
bpal = [mat("Bld%d" % i, srgb(c), 0.85) for i, c in enumerate(["#B9A58F", "#8E7C6D", "#6F7C86", "#A8665A", "#C9BFAE", "#5F6A60", "#847466"])]
winm = mat("Window_lit", srgb("#FFB35A"), 0.3, emit=srgb("#FFAA4A"), emit_s=3.5)
dark_win = mat("Window_dark", srgb("#10141A"), 0.1, 0.0, 0.6)
slab("sidewalk", -2.4, 1.6, -40, 80, -0.2, 0.0, walk); slab("kerb", 1.6, 1.78, -40, 80, -0.2, 0.0, kerbm)
slab("road", 1.78, 15.0, -40, 80, -0.3, -0.15, road); slab("sidewalk_far", 15.0, 19.0, -40, 80, -0.2, 0.0, walk)
lawn = mat("Lawn_dusk", srgb("#36422A"), 0.95); bump_noise(lawn, 300, 0.5, 0.01)
slab("verge", -80, -2.4, -60, 90, -0.3, -0.12, lawn)
hedge = mat("Hedge", srgb("#26361F"), 0.95); bump_noise(hedge, 120, 0.8, 0.02)
for yy in range(-30, 80, 9): setobj(rbox("hedge_%d" % yy, (0.7, 7.6, 0.85), 0.2, hedge, center=(-3.0, yy + 4, 0.35), seg=3))
slab("wall_low", -2.55, -2.4, -60, 90, -0.1, 0.45, kerbm)
random.seed(7)
win_bm = bmesh.new(); dwin_bm = bmesh.new()
def building(name, x0, x1, y0, y1, ht, face="east", m=None):
    slab(name, x0, x1, y0, y1, 0, ht, m or random.choice(bpal))
    fx = x1 + 0.005 if face == "east" else x0 - 0.005
    nyw = int((y1 - y0 - 1.0) // 3.0); nzw = int((ht - 1.2) // 3.3)
    for j in range(nyw):
        for k in range(nzw):
            yc = y0 + 1.5 + j * 3.0 + 0.2; zc = 2.3 + k * 3.3
            if random.random() < 0.55: tgt = win_bm
            else: tgt = dwin_bm
            v = [tgt.verts.new((fx, yc - 0.6, zc - 0.8)), tgt.verts.new((fx, yc + 0.6, zc - 0.8)), tgt.verts.new((fx, yc + 0.6, zc + 0.8)), tgt.verts.new((fx, yc - 0.6, zc + 0.8))]
            tgt.faces.new(v if face == "east" else v[::-1])
y = -50.0
while y < 90:
    wd = random.uniform(7, 15); building("bld_w_%d" % int(y), -62, -36, y, y + wd, random.uniform(7, 15), "east"); y += wd + random.uniform(0.2, 1.0)
y = -22.0
while y < 70:
    wd = random.uniform(9, 18); building("bld_e_%d" % int(y), 19.5, 30, y, y + wd, random.uniform(6, 16), "west"); y += wd + random.uniform(0.3, 1.2)
building("bld_end", -62, 30, 80, 92, 15, "east"); 
for bmx, m_, nm in ((win_bm, winm, "windows_lit"), (dwin_bm, dark_win, "windows_dark")):
    setobj(to_obj(bmx, nm, m_, 10))
# lamp posts, parked cars
lampm = mat("Lamp", srgb("#1B1D1F"), 0.5, 0.8); lamphead = mat("Lamp_light", srgb("#FFC27A"), 0.3, emit=srgb("#FFB066"), emit_s=40)
for i, yy in enumerate((-8, 6, 20, 34, 48)):
    bm = bmesh.new(); add_cyl(bm, (1.2, yy, 0), (1.2, yy, 4.8), 0.05, 0.035, 12); add_cyl(bm, (1.2, yy, 4.8), (1.75, yy, 5.0), 0.03, 0.03, 10)
    setobj(to_obj(bm, "lamp_%d" % i, lampm)); bm = bmesh.new(); add_sphere(bm, (1.8, yy, 4.95), 0.14, 14, (1.6, 1, 0.5)); setobj(to_obj(bm, "lamphead_%d" % i, lamphead))
carm = [mat("Car%d" % i, srgb(c), 0.3, 0.0, 0.8) for i, c in enumerate(["#222831", "#7A2B2B", "#C8C8C4", "#2B4A5E"])]
for i, yy in enumerate((-4.5, 5.0, 14.5, 26.0, 37.0)):
    cm = carm[i % 4]
    setobj(rbox("car_%d" % i, (1.85, 4.4, 0.75), 0.18, cm, center=(4.4, yy, 0.62), seg=4)); setobj(rbox("cabin_%d" % i, (1.6, 2.3, 0.62), 0.2, cm, center=(4.4, yy - 0.1, 1.2), seg=4))
    for sx in (-1, 1):
        for sy in (-1, 1):
            bm = bmesh.new(); add_cyl(bm, (4.4 + sx * 0.93, yy + sy * 1.4, 0.32), (4.4 + sx * 0.8, yy + sy * 1.4, 0.32), 0.32, seg=18) ; setobj(to_obj(bm, "wheel", M["black"]))
# studio floor
studio_floor = rbox("studio_floor", (900, 900, 0.02), 0.0, mat("Studio_floor", (0.75, 0.75, 0.76), 0.85), center=(0, 0, -0.01)); STUDIO.append(studio_floor)

# ---------------------------------------------------------------- worlds, lights, cameras
def world(stops, strength):
    w_ = bpy.data.worlds.new("W"); w_.use_nodes = True; nt = w_.node_tree; bg = nt.nodes["Background"]
    tc = nt.nodes.new("ShaderNodeTexCoord"); sep = nt.nodes.new("ShaderNodeSeparateXYZ"); rp = nt.nodes.new("ShaderNodeValToRGB")
    nt.links.new(tc.outputs["Generated"], sep.inputs["Vector"]); nt.links.new(sep.outputs["Z"], rp.inputs["Fac"]); nt.links.new(rp.outputs["Color"], bg.inputs["Color"])
    el = rp.color_ramp.elements; el[0].position = stops[0][0]; el[0].color = (*stops[0][1], 1); el[1].position = stops[1][0]; el[1].color = (*stops[1][1], 1)
    for pos, col in stops[2:]:
        e = el.new(pos); e.color = (*col, 1)
    bg.inputs["Strength"].default_value = strength; return w_
W_DUSK = world([(0.0, srgb("#FF9A55")), (0.06, srgb("#E88458")), (0.22, srgb("#7B6A9A")), (0.5, srgb("#2E4A86")), (0.9, srgb("#142447"))], 1.0)
W_STUDIO = bpy.data.worlds.new("WS"); W_STUDIO.use_nodes = True
_nt = W_STUDIO.node_tree; _bg = _nt.nodes["Background"]; _lp = _nt.nodes.new("ShaderNodeLightPath"); _mx = _nt.nodes.new("ShaderNodeMix"); _mx.data_type = "RGBA"
_mx.inputs[6].default_value = (0.40, 0.41, 0.43, 1); _mx.inputs[7].default_value = (0.30, 0.31, 0.33, 1)
_nt.links.new(_lp.outputs["Is Camera Ray"], _mx.inputs[0]); _nt.links.new(_mx.outputs[2], _bg.inputs["Color"]); _bg.inputs["Strength"].default_value = 1.0
lights = []
def area(name, loc, target, energy, size, color=(1, 1, 1)):
    l = bpy.data.lights.new(name, "AREA"); l.energy = energy; l.size = size; l.color = color
    o = bpy.data.objects.new(name, l); scene.collection.objects.link(o); o.location = loc
    o.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y").to_euler(); return o
def sun(name, direction, strength, color, angle=0.03):
    l = bpy.data.lights.new(name, "SUN"); l.energy = strength; l.color = color; l.angle = angle
    o = bpy.data.objects.new(name, l); scene.collection.objects.link(o)
    o.rotation_euler = (-Vector(direction)).to_track_quat("-Z", "Y").to_euler(); return o   # light travels along -direction
LT = {
 "studio": [area("key", (3.2, -3.4, 3.6), (0, -0.5, 1.5), 800, 2.2, (1.0, 0.96, 0.9)), area("fill", (-3.6, -2.0, 1.8), (0, -0.5, 1.3), 330, 3.0, (0.88, 0.93, 1.0)),
            area("rim", (-1.5, 3.4, 3.0), (0, -0.5, 1.5), 700, 1.6, (1, 1, 1)), area("top", (0, -1.0, 5.0), (0, -0.5, 1.5), 260, 2.5)],
 "a": [sun("sun_a", (0.80, -0.25, 0.16), 5.5, (1.0, 0.58, 0.28)), area("fill_a", (-3.0, -5, 2.0), (0, -0.5, 1.4), 260, 4, (0.6, 0.7, 1.0))],
 "b": [sun("sun_b", (0.55, -0.60, 0.30), 6.0, (1.0, 0.60, 0.30)), area("fill_b", (0, 6, 3.0), (0, -0.5, 1.5), 420, 6, (0.6, 0.7, 1.0))],
 "c": [sun("sun_c", (0.75, 0.35, 0.35), 5.0, (1.0, 0.62, 0.32)), area("fill_c", (-0.6, -0.2, 2.6), (0, -1.15, 2.2), 45, 1.2, (0.9, 0.9, 1.0))],
}
for L in LT.values():
    for o in L: o.hide_render = True
def cam_(name, loc, target, lens, sensor=36.0, roll=0.0):
    c = bpy.data.cameras.new(name); c.lens = lens; c.sensor_width = sensor; c.clip_start = 0.02; c.clip_end = 400
    o = bpy.data.objects.new(name, c); scene.collection.objects.link(o); o.location = loc
    o.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y").to_euler(); return o
CAMS = {
 "hero": cam_("cam_hero", (2.5, -4.5, 1.45), (0.0, -0.5, 1.2), 45),
 "a": cam_("cam_a", (3.0, -5.0, 0.85), (-0.1, -0.5, 1.2), 38),
 "c": cam_("cam_c", (-0.28, -0.52, 2.0), tuple(POD_C - pdir * 0.085), 62),
}
pod_look = POD_M @ Vector((0, 0.04, 0))
CAMS["b"] = cam_("cam_pov", POD_C + (POD_M.to_3x3() @ Vector((0, d / 2 + 0.01, 0))), POD_C + (POD_M.to_3x3() @ Vector((0, 2.0, 0.0))), 17.5)
CAMS["b"].data.sensor_width = 36
for k in ("a", "c"):
    CAMS[k].data.dof.use_dof = True; CAMS[k].data.dof.aperture_fstop = 4.0 if k == "a" else 6.0
CAMS["c"].data.dof.focus_object = None; CAMS["c"].data.dof.focus_distance = (CAMS["c"].location - POD_C).length
CAMS["a"].data.dof.focus_distance = (CAMS["a"].location - Vector((0, -0.6, 1.4))).length
ENVS = {"hero": ("studio", W_STUDIO, STUDIO), "a": ("a", W_DUSK, SET), "b": ("b", W_DUSK, SET), "c": ("c", W_DUSK, SET)}
SHOTS = {"hero": ("assembly-hero.png", (1600, 1200), os.path.join(ROOT, "render")),
         "a": ("hero-blender.png", (1672, 941), os.path.join(ROOT, "render", "shots")),
         "b": ("pov-blender.png", (1672, 941), os.path.join(ROOT, "render", "shots")),
         "c": ("detail-blender.png", (1672, 941), os.path.join(ROOT, "render", "shots"))}

bpy.ops.wm.save_as_mainfile(filepath=os.path.join(ROOT, "blender", "third-person-vr.blend"), compress=True)
print("SAVED blend %.1fs" % (time.time() - T0))

# ================================================================ 5. RENDER
scene.render.engine = "CYCLES"; cy = scene.cycles; cy.samples = SAMPLES; cy.use_denoising = True; cy.use_adaptive_sampling = True; cy.max_bounces = 8
try:
    pr = bpy.context.preferences.addons["cycles"].preferences; pr.compute_device_type = "METAL"; pr.get_devices()
    for dv in pr.devices: dv.use = True
    cy.device = "GPU"
except Exception as e: print("GPU setup failed, CPU:", e)
for vt in ("AgX", "Filmic", "Standard"):
    try: scene.view_settings.view_transform = vt; break
    except TypeError: pass
scene.render.image_settings.file_format = "PNG"
POD_PARTS = [o for o in RIG if o.name.startswith(("camera-pod", "lens_", "ball_head"))]
EXPOSURE = {"hero": -0.25, "a": -0.3, "b": -0.2, "c": -0.3}
if not NO_RENDER:
    for key in ONLY:
        lt, wd, vis = ENVS[key]; fn, res, folder = SHOTS[key]
        for o in SET + STUDIO: o.hide_render = True
        for o in vis: o.hide_render = False
        for L in LT.values():
            for o in L: o.hide_render = True
        for o in LT[lt]: o.hide_render = False
        for o in POD_PARTS: o.hide_render = (key == "b")
        for nm in str(arg("--hide", "")).split(","):
            if nm in bpy.data.objects: bpy.data.objects[nm].hide_render = True
        scene.world = wd; scene.camera = CAMS[key]; scene.view_settings.exposure = EXPOSURE[key]
        scene.render.resolution_x, scene.render.resolution_y = res; scene.render.resolution_percentage = int(100 * RSCALE)
        scene.render.filepath = os.path.join(folder, fn); t = time.time()
        bpy.ops.render.render(write_still=True); print("RENDER", fn, "%.1fs" % (time.time() - t))
print("DONE total %.1f min" % ((time.time() - T0) / 60))
