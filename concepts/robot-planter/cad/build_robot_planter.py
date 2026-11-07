"""Robot planter (Concept) - parametric printed parts + assembly + renders + photo-shot scenes.

Run headless:
  /Applications/Blender.app/Contents/MacOS/Blender -b -P build_robot_planter.py -- [--engine cycles|eevee] [--samples 128] [--no-render] [--only hero,detail,night,dock,assembly,exploded]

All lengths are metres (Blender units). STLs are exported scaled x1000, so they open in
millimetres in a slicer. Outputs go next to this folder: ../cad, ../blender, ../render, ../render/shots.
Front of the robot (sensor eyes) faces +X in Blender (glTF: +X as well, glTF is Y-up so Blender +Y -> glTF -Z).
"""
import bpy, bmesh, math, os, sys, time, random
from mathutils import Vector, Matrix

# ----------------------------------------------------------------------------------------
# Dimensions (metres). Change here and re-run.
# ----------------------------------------------------------------------------------------
D = dict(
    # bought parts (stand-ins)
    chassis=(0.200, 0.150, 0.022), chassis_corner_r=0.030, chassis_ground_gap=0.014,
    wheel_d=0.065, wheel_w=0.026, wheel_x=0.048,
    pi=(0.085, 0.056, 0.012), pi_y=-0.045,
    battery=(0.155, 0.048, 0.040), battery_y=0.040,
    pot_bottom_d=0.110, pot_top_d=0.150, pot_h=0.130, pot_wall=0.003, pot_base=0.004,
    # shell: ONE tapered tub (printed)
    shell_d_bottom=0.250, shell_d_top=0.225, shell_h=0.105, shell_z0=0.010,   # z0 = ground gap under the skirt
    shell_fillet_bottom=0.010, shell_fillet_top=0.012,
    shell_wall=0.0035, lid_t=0.012, pot_sink=0.060, pot_clear=0.0015, pocket_wall=0.003, pocket_floor=0.006,
    wheel_arch_r=0.034, wheel_y=0.080,
    # sensor recess + eyes on the front (+X) face
    recess_w=0.066, recess_h=0.036, recess_depth=0.004, recess_r=0.010, eye_y=0.030, eye_z=0.052,
    eye_d=0.016, eye_gap=0.026, eye_len=0.0075,
    # light sensor: frosted dome in a thin white ring, flush in the rear top rim (replaces the old mast)
    sensor_d=0.022, dome_h=0.008, sensor_xy=(-0.0143, 0.0843), sensor_tilt_deg=4.0, ring_w=0.0017, ring_h=0.003,
    plant_gap_xy=(-0.015, 0.089),   # direction where the pothos is kept low (was the mast position; kept so the plant is unchanged)
    # pothos
    pothos_seed=11, n_upright=13, n_trail=3, trail_angle=-55.0, leaf_len=0.072,
    # dock ramp (printed) + bought contacts/LED/cable
    ramp_w=0.230, ramp_l=0.120, ramp_rise=0.025, backrest_h=0.090, backrest_t=0.014,
    post_y=0.030, post_z0=0.040, post_h=0.040, post_w=0.014, post_d=0.012,
    # battery tray (printed)
    tray_wall=0.003, tray_floor=0.003, tray_wall_h=0.022, tray_clear=0.001,
    strap_slot=(0.004, 0.036), strap_x=0.045,
    # photo shots
    shot_res=(1672, 941), asm_res=(1600, 1200),
)
OUT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CAD, BLEND, RENDER = (os.path.join(OUT, n) for n in ("cad", "blender", "render"))
SHOTS = os.path.join(RENDER, "shots")

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
def arg(name, default):
    return argv[argv.index(name) + 1] if name in argv else default
ENGINE = arg("--engine", "cycles")
SAMPLES = int(arg("--samples", "128"))
DO_RENDER = "--no-render" not in argv
ONLY = set(arg("--only", "assembly,exploded,hero,detail,night,dock").split(","))

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

def join(name, objs):
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs: o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.join()
    o = bpy.context.active_object; o.name = name; return o

def hull_obj(name, pts):
    bm = bmesh.new()
    vs = [bm.verts.new(p) for p in pts]
    bmesh.ops.convex_hull(bm, input=vs)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); bpy.context.collection.objects.link(o); return o

def lathe(name, profile, seg=96):
    """Solid of revolution about Z from a (r, z) polyline that starts and ends on the axis (r=0)."""
    bm = bmesh.new()
    rings = []
    for (r, z) in profile:
        if r < 1e-9:
            rings.append([bm.verts.new((0, 0, z))])
        else:
            rings.append([bm.verts.new((r * math.cos(2 * math.pi * k / seg), r * math.sin(2 * math.pi * k / seg), z)) for k in range(seg)])
    for a, b in zip(rings[:-1], rings[1:]):
        if len(a) == 1 and len(b) == 1: continue
        for k in range(seg):
            k2 = (k + 1) % seg
            if len(a) == 1:   bm.faces.new((a[0], b[k2], b[k]))
            elif len(b) == 1: bm.faces.new((a[k], a[k2], b[0]))
            else:             bm.faces.new((a[k], a[k2], b[k2], b[k]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); bpy.context.collection.objects.link(o); return o

def rounded_profile(corners, n=10):
    """corners = [(r, z, fillet_distance)]; quadratic-bezier fillets."""
    out = []
    for i, (r, z, d) in enumerate(corners):
        if d <= 0 or i == 0 or i == len(corners) - 1:
            out.append((r, z)); continue
        P = Vector((r, z)); A = Vector(corners[i - 1][:2]); B = Vector(corners[i + 1][:2])
        u1 = (A - P).normalized(); u2 = (B - P).normalized()
        p0, p2 = P + u1 * d, P + u2 * d
        for k in range(n + 1):
            t = k / n
            q = (1 - t) ** 2 * p0 + 2 * t * (1 - t) * P + t * t * p2
            out.append((q.x, q.y))
    return out

def recalc(o):
    bm = bmesh.new(); bm.from_mesh(o.data)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces); bm.to_mesh(o.data); bm.free()

def tube_curve(name, pts, r, mat, res=3, order=4):
    cu = bpy.data.curves.new(name, "CURVE"); cu.dimensions = "3D"
    sp = cu.splines.new("NURBS"); sp.points.add(len(pts) - 1)
    for p, v in zip(sp.points, pts): p.co = (v[0], v[1], v[2], 1)
    sp.order_u = min(order, len(pts)); sp.use_endpoint_u = True; sp.resolution_u = 6
    cu.bevel_depth = r; cu.bevel_resolution = res; cu.use_fill_caps = True
    o = bpy.data.objects.new(name, cu); bpy.context.collection.objects.link(o)
    active(o); bpy.ops.object.convert(target="MESH")
    o = bpy.context.active_object; o.name = name
    o.data.materials.clear(); o.data.materials.append(mat); smooth(o); return o

def srgb(h):
    c = [int(h[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    lin = lambda v: v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4
    return tuple(lin(v) for v in c)

def make_mat(name, rgb, rough=0.5, metal=0.0, spec=0.5, emit=None, emit_strength=0.0):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*rgb, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    for k in ("Specular IOR Level", "Specular"):
        if k in b.inputs: b.inputs[k].default_value = spec; break
    if emit is not None:
        b.inputs["Emission Color"].default_value = (*emit, 1); b.inputs["Emission Strength"].default_value = emit_strength
    return m

def assign(o, m):
    o.data.materials.clear(); o.data.materials.append(m)

# ---- node-material helpers (procedural: renders only; GLB keeps base colour) ----
def new_nodes_mat(name):
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial"); bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return m, nt, bsdf

def N(nt, kind, **kw):
    n = nt.nodes.new(kind)
    for k, v in kw.items():
        try: setattr(n, k, v)
        except Exception: pass
    return n

def ramp_node(nt, stops):
    r = nt.nodes.new("ShaderNodeValToRGB")
    el = r.color_ramp.elements
    while len(el) > 2: el.remove(el[-1])
    el[0].position, el[0].color = stops[0][0], (*stops[0][1], 1)
    el[1].position, el[1].color = stops[1][0], (*stops[1][1], 1)
    for pos, col in stops[2:]:
        e = el.new(pos); e.color = (*col, 1)
    return r

def bump_from(nt, fac_socket, bsdf, strength=0.3, dist=0.002):
    b = nt.nodes.new("ShaderNodeBump"); b.inputs["Strength"].default_value = strength; b.inputs["Distance"].default_value = dist
    nt.links.new(fac_socket, b.inputs["Height"]); nt.links.new(b.outputs["Normal"], bsdf.inputs["Normal"])

def tile_material(name, size, col1, col2, mortar, rough=0.8, tile_noise=0.35, mortar_size=0.012, bump=0.4):
    m, nt, bsdf = new_nodes_mat(name)
    tc = N(nt, "ShaderNodeTexCoord"); mp = N(nt, "ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (1 / size, 1 / size, 1 / size)
    nt.links.new(tc.outputs["Object"], mp.inputs["Vector"])
    br = N(nt, "ShaderNodeTexBrick", offset=0.0, squash=1.0)
    br.inputs["Color1"].default_value = (*col1, 1); br.inputs["Color2"].default_value = (*col2, 1); br.inputs["Mortar"].default_value = (*mortar, 1)
    br.inputs["Mortar Size"].default_value = mortar_size; br.inputs["Mortar Smooth"].default_value = 0.1
    br.inputs["Brick Width"].default_value = 1.0; br.inputs["Row Height"].default_value = 1.0; br.inputs["Scale"].default_value = 1.0
    nt.links.new(mp.outputs["Vector"], br.inputs["Vector"])
    nz = N(nt, "ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 18 / size * 0.45 * 2.2; nz.inputs["Detail"].default_value = 8
    nt.links.new(tc.outputs["Object"], nz.inputs["Vector"])
    mix = N(nt, "ShaderNodeMixRGB", blend_type="MULTIPLY"); mix.inputs["Fac"].default_value = tile_noise
    nt.links.new(br.outputs["Color"], mix.inputs["Color1"]); nt.links.new(nz.outputs["Fac"], mix.inputs["Color2"])
    nt.links.new(mix.outputs["Color"], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = rough
    nz2 = N(nt, "ShaderNodeTexNoise"); nz2.inputs["Scale"].default_value = 260; nz2.inputs["Detail"].default_value = 6
    nt.links.new(tc.outputs["Object"], nz2.inputs["Vector"])
    bump_from(nt, nz2.outputs["Fac"], bsdf, bump, 0.003)
    out = [n for n in nt.nodes if n.bl_idname == "ShaderNodeOutputMaterial"][0]
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return m

def noise_material(name, stops, scale, detail=6, rough=0.9, bump_scale=None, bump=0.3, big_scale=None):
    m, nt, bsdf = new_nodes_mat(name)
    tc = N(nt, "ShaderNodeTexCoord")
    nz = N(nt, "ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = scale; nz.inputs["Detail"].default_value = detail
    nt.links.new(tc.outputs["Object"], nz.inputs["Vector"])
    rp = ramp_node(nt, stops); nt.links.new(nz.outputs["Fac"], rp.inputs["Fac"])
    col = rp.outputs["Color"]
    if big_scale:
        nb = N(nt, "ShaderNodeTexNoise"); nb.inputs["Scale"].default_value = big_scale; nb.inputs["Detail"].default_value = 3
        nt.links.new(tc.outputs["Object"], nb.inputs["Vector"])
        mx = N(nt, "ShaderNodeMixRGB", blend_type="MULTIPLY"); mx.inputs["Fac"].default_value = 0.8
        nt.links.new(col, mx.inputs["Color1"]); nt.links.new(nb.outputs["Fac"], mx.inputs["Color2"]); col = mx.outputs["Color"]
    nt.links.new(col, bsdf.inputs["Base Color"]); bsdf.inputs["Roughness"].default_value = rough
    if bump_scale:
        n2 = N(nt, "ShaderNodeTexNoise"); n2.inputs["Scale"].default_value = bump_scale; n2.inputs["Detail"].default_value = 8
        nt.links.new(tc.outputs["Object"], n2.inputs["Vector"]); bump_from(nt, n2.outputs["Fac"], bsdf, bump, 0.004)
    out = [n for n in nt.nodes if n.bl_idname == "ShaderNodeOutputMaterial"][0]
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return m

def fence_material(name):
    m, nt, bsdf = new_nodes_mat(name)
    tc = N(nt, "ShaderNodeTexCoord"); sep = N(nt, "ShaderNodeSeparateXYZ"); nt.links.new(tc.outputs["Object"], sep.inputs["Vector"])
    cu = N(nt, "ShaderNodeCombineXYZ")
    mu = N(nt, "ShaderNodeMath", operation="MULTIPLY"); mu.inputs[1].default_value = 1 / 0.15
    nt.links.new(sep.outputs["Y"], mu.inputs[0]); nt.links.new(mu.outputs["Value"], cu.inputs["X"])
    mz = N(nt, "ShaderNodeMath", operation="MULTIPLY"); mz.inputs[1].default_value = 1 / 3.0
    nt.links.new(sep.outputs["Z"], mz.inputs[0]); nt.links.new(mz.outputs["Value"], cu.inputs["Y"])
    br = N(nt, "ShaderNodeTexBrick", offset=0.0, squash=1.0)
    br.inputs["Color1"].default_value = (0.20, 0.12, 0.07, 1); br.inputs["Color2"].default_value = (0.12, 0.07, 0.04, 1)
    br.inputs["Mortar"].default_value = (0.01, 0.008, 0.006, 1); br.inputs["Mortar Size"].default_value = 0.025
    br.inputs["Brick Width"].default_value = 1.0; br.inputs["Row Height"].default_value = 1.0
    nt.links.new(cu.outputs["Vector"], br.inputs["Vector"])
    bsdf.inputs["Roughness"].default_value = 0.85
    nt.links.new(br.outputs["Color"], bsdf.inputs["Base Color"])
    out = [n for n in nt.nodes if n.bl_idname == "ShaderNodeOutputMaterial"][0]
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return m

def leaf_material(name, dark, light, glossy=0.45):
    m, nt, bsdf = new_nodes_mat(name)
    tc = N(nt, "ShaderNodeTexCoord"); oi = N(nt, "ShaderNodeObjectInfo")
    sc = N(nt, "ShaderNodeVectorMath", operation="SCALE"); sc.inputs["Scale"].default_value = 47.0
    nt.links.new(oi.outputs["Location"], sc.inputs[0])
    ad = N(nt, "ShaderNodeVectorMath", operation="ADD")
    nt.links.new(tc.outputs["Object"], ad.inputs[0]); nt.links.new(sc.outputs["Vector"], ad.inputs[1])
    nz = N(nt, "ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 70; nz.inputs["Detail"].default_value = 3
    nt.links.new(ad.outputs["Vector"], nz.inputs["Vector"])
    rp = ramp_node(nt, [(0.50, dark), (0.60, light)]); nt.links.new(nz.outputs["Fac"], rp.inputs["Fac"])
    nt.links.new(rp.outputs["Color"], bsdf.inputs["Base Color"]); bsdf.inputs["Roughness"].default_value = glossy
    for k in ("Specular IOR Level", "Specular"):
        if k in bsdf.inputs: bsdf.inputs[k].default_value = 0.5; break
    tr = N(nt, "ShaderNodeBsdfTranslucent"); nt.links.new(rp.outputs["Color"], tr.inputs["Color"])
    mx = N(nt, "ShaderNodeMixShader"); mx.inputs["Fac"].default_value = 0.25
    nt.links.new(bsdf.outputs["BSDF"], mx.inputs[1]); nt.links.new(tr.outputs["BSDF"], mx.inputs[2])
    out = nt.nodes.new("ShaderNodeOutputMaterial"); nt.links.new(mx.outputs["Shader"], out.inputs["Surface"])
    m.diffuse_color = (*dark, 1)   # viewport / GLB fallback colour
    return m

def mesh_face_material(name):
    m, nt, bsdf = new_nodes_mat(name)
    tc = N(nt, "ShaderNodeTexCoord")
    ck = N(nt, "ShaderNodeTexChecker"); ck.inputs["Scale"].default_value = 2600
    ck.inputs["Color1"].default_value = (0.02, 0.02, 0.022, 1); ck.inputs["Color2"].default_value = (0.09, 0.09, 0.09, 1)
    nt.links.new(tc.outputs["Object"], ck.inputs["Vector"])
    nt.links.new(ck.outputs["Color"], bsdf.inputs["Base Color"]); bsdf.inputs["Roughness"].default_value = 0.6
    out = nt.nodes.new("ShaderNodeOutputMaterial"); nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return m

# ----------------------------------------------------------------------------------------
# Reset scene
# ----------------------------------------------------------------------------------------
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.unit_settings.system = "METRIC"; scene.unit_settings.scale_length = 1.0

def pot_r(h):  # outer pot radius at height h above pot bottom
    return D["pot_bottom_d"] / 2 + (D["pot_top_d"] - D["pot_bottom_d"]) / 2 * h / D["pot_h"]

RB, RT, H = D["shell_d_bottom"] / 2, D["shell_d_top"] / 2, D["shell_h"]
def shell_r(z):  # outer shell radius at local height z (above skirt)
    return RB + (RT - RB) * z / H
SHELL_TOP_W = D["shell_z0"] + H                       # world z of the flat rim
POT_Z0 = SHELL_TOP_W - D["pot_sink"]                  # world z of the pot's bottom
POT_TOP = POT_Z0 + D["pot_h"]

# ----------------------------------------------------------------------------------------
# Printed part 1: ONE smooth tapered shell (local z=0 is the skirt bottom)
# ----------------------------------------------------------------------------------------
def build_shell():
    fb, ft = D["shell_fillet_bottom"], D["shell_fillet_top"]
    prof = rounded_profile([(0, 0, 0), (RB, 0, fb), (RT, H, ft), (0, H, 0)])
    shell = lathe("shell_body", prof)
    w = D["shell_wall"]
    pot_local = POT_Z0 - D["shell_z0"]                # pocket bottom, local z
    cav_top = H - D["lid_t"]
    # hollow body: cavity open at the bottom, tapered like the outside
    cav = lathe("_cav", [(0, -0.001), (RB - fb - w, -0.001), (RB - fb - w, 0.0), (shell_r(fb) - w, fb),
                         (shell_r(cav_top) - w, cav_top), (0, cav_top)])
    cut(shell, cav)
    # pot pocket tube (solid wall around the pot) then the pocket itself
    pr0 = pot_r(0) + D["pot_clear"]; pr1 = pot_r(D["pot_sink"] + 0.005) + D["pot_clear"]
    floor_z = pot_local - D["pocket_floor"]
    tube_h = H - floor_z - 0.001
    union(shell, cone("_tube", pr0 + D["pocket_wall"], pot_r(D["pot_sink"]) + D["pot_clear"] + D["pocket_wall"], tube_h, z0=floor_z))
    cut(shell, cone("_pocket", pr0, pr1, D["pot_sink"] + 0.005 + 0.001, z0=pot_local))
    # drain hole through the pocket floor
    cut(shell, cyl("_drain", 0.012, 0.03, z0=floor_z - 0.01, verts=48))
    # wheel arches (cylinders along Y at each wheel)
    ar = D["wheel_arch_r"]
    for sx in (1, -1):
        for sy in (1, -1):
            cut(shell, cyl("_arch", ar, 0.05, x=sx * D["wheel_x"], y=sy * (D["wheel_y"] + 0.0135 + 0.003), z0=-0.025 - 0.0,
                           rot=(math.pi / 2, 0, 0), verts=64))
    # shallow rounded-rect recess in the front (+X) face, floor concentric with the tub (4 mm deep)
    rw, rh, rd = D["recess_w"], D["recess_h"], D["recess_depth"]
    zc = D["eye_z"]
    pad = box("_pad", 0.05, rw + 0.020, rh + 0.020, x=0.115, y=D["eye_y"], z0=zc - rh / 2 - 0.010)
    boolean(pad, cone("_padk", RB - 0.0005, RT - 0.0005, H, z0=0, verts=128), "INTERSECT")
    union(shell, pad)
    prism = box("_rp", 0.12, rw, rh, x=0.14, y=D["eye_y"], z0=zc - rh / 2)
    bevel(prism, D["recess_r"], 6, 20)
    cut(prism, cone("_keep", RB - rd, RT - rd, H, z0=0, verts=128))
    cut(shell, prism)
    # light-sensor seat: shallow round recess in the rear top rim, tilted to follow the rim
    sx_, sy_ = D["sensor_xy"]; tl = math.radians(D["sensor_tilt_deg"]); az = math.atan2(sy_, sx_)
    seat = cyl("_seat", D["sensor_d"] / 2 + D["ring_w"] + 0.0002, 0.012, verts=64)
    seat.rotation_euler = (0, tl, az); seat.location = (sx_, sy_, H - 0.0045 + 0.006 * 0)   # local z of shell = H at the rim
    seat.location = Vector((sx_, sy_, H - 0.0045)) + Vector((0, 0, 0.006))
    apply_xf(seat); cut(shell, seat)
    smooth(shell)
    return shell

# ----------------------------------------------------------------------------------------
# Printed part 3: dock ramp with backrest (local origin: low end centre on ground; x rises towards the backrest)
# ----------------------------------------------------------------------------------------
def build_ramp():
    w = D["ramp_w"] / 2; L = D["ramp_l"]; rise = D["ramp_rise"]; bh = D["backrest_h"]; bt = D["backrest_t"]
    ramp = hull_obj("dock_ramp", [(0, -w, 0), (L, -w, 0), (L, -w, rise), (0, -w, 0.003),
                                  (0, w, 0), (L, w, 0), (L, w, rise), (0, w, 0.003)])
    # backrest slab: rounded-rectangle profile in (y, z), extruded along x
    rr = 0.022; pts = []
    for (cy_, cz_, a0) in ((w - rr, bh - rr, 0), (-(w - rr), bh - rr, 90)):
        for k in range(7):
            a = math.radians(a0 + 90 * k / 6)
            pts.append((cy_ + rr * math.cos(a), cz_ + rr * math.sin(a)))
    pts += [(-w, 0), (w, 0)]
    union(ramp, hull_obj("_back", [(x_, y_, z_) for x_ in (L - bt, L) for (y_, z_) in pts]))
    # side wings that rise towards the backrest
    for s in (1, -1):
        y0, y1 = s * (w - 0.010), s * w
        union(ramp, hull_obj("_wing", [(L - 0.050, y0, 0), (L - 0.050, y1, 0), (L - 0.050, y0, 0.034), (L - 0.050, y1, 0.034),
                                       (L - 0.004, y0, 0), (L - 0.004, y1, 0), (L - 0.004, y0, bh - 0.020), (L - 0.004, y1, bh - 0.020)]))
    # bores behind the two spring-contact posts, dome-LED seat, cable exit
    for s in (1, -1):
        cut(ramp, cyl("_pb", 0.004, 0.030, x=L - bt / 2, y=s * D["post_y"], z0=D["post_z0"] + D["post_h"] / 2 - 0.015, verts=24,
                      rot=(0, math.pi / 2, 0)))
    cut(ramp, cyl("_led", 0.0075, 0.012, x=L - bt / 2 - 0.0, y=0, z0=bh - 0.010, verts=32))
    cut(ramp, cyl("_cab", 0.0035, 0.030, x=L - bt / 2, y=-0.060, z0=0.025 - 0.015, verts=24, rot=(0, math.pi / 2, 0)))
    bevel(ramp, 0.0015, 2, 35); active(ramp); bpy.ops.object.shade_flat()
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
    for s in (1, -1):
        cut(tray, cyl("_sc", 0.013, 0.02, x=0, y=s * (cy / 2 + w / 2), z0=f + wh - 0.012,
                      rot=(math.pi / 2, 0, 0), verts=48))
    sw, sl = D["strap_slot"]
    for s in (1, -1):
        sx = s * D["strap_x"]
        cut(tray, box("_ss", sw, sl, 0.02, x=sx, z0=-0.005))
        cut(tray, box("_ch", sw + 0.006, oy + 0.02, 0.002, x=sx, z0=-0.0005))
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
parts = {"shell_ring_cradle": build_shell(),
         "dock_ramp": build_ramp(), "battery_tray": build_tray()}
parts["shell_ring_cradle"].name = "shell_body"
print("PARTS built t=%.1fs" % (time.time() - t0))

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
    shell=make_mat("PETG_warm_white", srgb("#E6E1D5"), 0.62, 0.0, 0.35),
    chassis=make_mat("Chassis_grey", srgb("#3A3C40"), 0.55, 0.3),
    rubber=make_mat("Rubber_black", srgb("#101010"), 0.85, 0.0, 0.2),
    hub=make_mat("Hub_alu", srgb("#8C8F94"), 0.35, 0.8),
    pot=make_mat("Terracotta", srgb("#B8613E"), 0.8, 0.0, 0.25),
    soil=make_mat("Soil", srgb("#3A2A1E"), 0.95, 0.0, 0.1),
    stem=make_mat("Stem", srgb("#7BA843"), 0.55),
    pi=make_mat("Pi_board", srgb("#1F6B3A"), 0.5, 0.0),
    batt=make_mat("Battery_blue", srgb("#24408A"), 0.5),
    silver=make_mat("Silver_rim", srgb("#C9CCD1"), 0.28, 1.0),
    dark=make_mat("Dark_plastic", srgb("#16171A"), 0.5, 0.0, 0.4),
    brass=make_mat("Brass", srgb("#C79A3B"), 0.3, 1.0),
    cable=make_mat("Cable_black", srgb("#0C0C0D"), 0.45, 0.0, 0.5),
    led=make_mat("LED_warm", srgb("#FFD9A0"), 0.3, 0.0, 0.5, emit=srgb("#FFB35C"), emit_strength=18.0),
    dome=make_mat("Sensor_dome_frosted", srgb("#E9EEF0"), 0.34, 0.0, 0.5),
    chip=make_mat("Sensor_chip", srgb("#15181B"), 0.4, 0.0, 0.4),
    ground=make_mat("Ground", srgb("#605F5B"), 0.9, 0.0, 0.0),
)
try:
    b_ = M["dome"].node_tree.nodes["Principled BSDF"]
    for k in ("Transmission Weight", "Transmission"):
        if k in b_.inputs: b_.inputs[k].default_value = 0.85; break
except Exception as e: print("dome mat", e)
M["leaf"] = leaf_material("Pothos_leaf", (0.030, 0.17, 0.035), (0.50, 0.58, 0.12))
M["eye_face"] = mesh_face_material("Transducer_mesh")
for o in parts.values(): assign(o, M["shell"])

# ----------------------------------------------------------------------------------------
# Assembly: stand-ins and placement
# ----------------------------------------------------------------------------------------
bought = []
cx, cy, cz = D["chassis"]; gap = D["chassis_ground_gap"]
bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0)
for v in bm.verts: v.co.x *= cx; v.co.y *= cy; v.co.z *= cz
vedges = [e for e in bm.edges if abs(e.verts[0].co.z - e.verts[1].co.z) > 1e-6]
bmesh.ops.bevel(bm, geom=vedges, offset=D["chassis_corner_r"], segments=8, affect="EDGES", profile=0.5)
me = bpy.data.meshes.new("chassis"); bm.to_mesh(me); bm.free()
chassis = bpy.data.objects.new("chassis_standin", me); bpy.context.collection.objects.link(chassis)
chassis.location = (0, 0, gap + cz / 2); apply_xf(chassis); bevel(chassis, 0.002, 2, 40); smooth(chassis)
assign(chassis, M["chassis"]); bought.append(chassis)
wr = D["wheel_d"] / 2
for sx in (1, -1):
    for sy in (1, -1):
        y = sy * D["wheel_y"]
        bpy.ops.mesh.primitive_cylinder_add(vertices=64, radius=wr, depth=D["wheel_w"],
                                            location=(sx * D["wheel_x"], y, wr), rotation=(math.pi / 2, 0, 0))
        w = bpy.context.active_object; w.name = "wheel"; apply_xf(w); bevel(w, 0.003, 3, 40); smooth(w)
        assign(w, M["rubber"]); bought.append(w)
        bpy.ops.mesh.primitive_cylinder_add(vertices=32, radius=0.017, depth=D["wheel_w"] + 0.004,
                                            location=(sx * D["wheel_x"], y, wr), rotation=(math.pi / 2, 0, 0))
        hub = bpy.context.active_object; hub.name = "hub"; apply_xf(hub); smooth(hub)
        assign(hub, M["hub"]); bought.append(hub)
top = gap + cz
px, py, pz = D["pi"]
pi = box("pi_standin", px, py, pz, x=0, y=D["pi_y"], z0=top); bevel(pi, 0.0015); smooth(pi)
assign(pi, M["pi"]); bought.append(pi)
bx, by, bz = D["battery"]
tray = parts["battery_tray"]
tray.location = (0, D["battery_y"], top)
batt = box("battery_standin", bx, by, bz, x=0, y=D["battery_y"], z0=top + D["tray_floor"] + 0.0005)
bevel(batt, 0.003, 3, 40); smooth(batt); assign(batt, M["batt"]); bought.append(batt)
shell = parts["shell_ring_cradle"]; shell.location = (0, 0, D["shell_z0"])

# ---- ultrasonic transducers in the front recess ----
Rs_floor = shell_r(D["eye_z"]) - D["recess_depth"]
eyes = []
for sgn in (1, -1):
    ye = D["eye_y"] + sgn * D["eye_gap"] / 2
    xe = math.sqrt(Rs_floor ** 2 - ye ** 2)
    phi = math.atan2(ye, xe)
    zw = D["shell_z0"] + D["eye_z"]
    r_e = D["eye_d"] / 2; L_e = D["eye_len"]
    rim = cyl("eye_rim", r_e, L_e, z0=-L_e / 2, verts=48, rot=(0, math.pi / 2, 0))   # along +X, centred at origin
    cut(rim, cyl("_pk", r_e - 0.0016, 0.0025, x=L_e / 2 - 0.001 + 0.00025, z0=-0.00125, verts=48, rot=(0, math.pi / 2, 0)))
    bevel(rim, 0.0004, 2, 40); smooth(rim); assign(rim, M["silver"])
    face = cyl("eye_face", r_e - 0.0017, 0.0006, x=L_e / 2 - 0.0012 - 0.0003, z0=-0.0003, verts=48, rot=(0, math.pi / 2, 0))
    smooth(face); assign(face, M["eye_face"])
    for o in (rim, face):
        # base of the transducer sits 1 mm below the recess floor; axis radial
        o.rotation_euler = (0, 0, phi)
        o.location = (Vector((math.cos(phi), math.sin(phi), 0)) * (Rs_floor - 0.001 + L_e / 2) + Vector((0, 0, zw)))
        # object origin at world origin before location: vertices were centred at origin already
        eyes.append(o)
bought += eyes

# ---- terracotta pot sunk into the shell (only the top ~70 mm shows) ----
pot = cone("pot", D["pot_bottom_d"] / 2, D["pot_top_d"] / 2, D["pot_h"], z0=POT_Z0, verts=96)
inner = cone("_pi", D["pot_bottom_d"] / 2 - D["pot_wall"], D["pot_top_d"] / 2 - D["pot_wall"],
             D["pot_h"] - D["pot_base"] + 0.001, z0=POT_Z0 + D["pot_base"], verts=96)
cut(pot, inner)
bpy.ops.mesh.primitive_torus_add(major_radius=D["pot_top_d"] / 2 - 0.0005, minor_radius=0.0045,
                                 major_segments=96, minor_segments=16,
                                 location=(0, 0, POT_TOP - 0.0045))
rim = bpy.context.active_object; rim.name = "_rim"; union(pot, rim); smooth(pot); assign(pot, M["pot"])
bought.append(pot)
soil_top = POT_TOP - 0.020
soil = cyl("soil", pot_r(soil_top - POT_Z0) - D["pot_wall"] - 0.0005, 0.012, z0=soil_top - 0.012, verts=64)
smooth(soil); assign(soil, M["soil"]); bought.append(soil)

# ---- pothos: heart-shaped leaves on curved stems, some trailing over the rim ----
random.seed(D["pothos_seed"])
def make_leaf_mesh(length):
    """Heart leaf: petiole at the notch (origin), tip along +Y, +Z up. Three rings + centre fan, folded and drooped."""
    N_ = 40; pts = []
    for i in range(N_):
        t = 2 * math.pi * i / N_
        x = 16 * math.sin(t) ** 3; yv = 13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t)
        pts.append((0.66 * x, 5 - yv))                      # v: 0 at the notch, +22 at the tip, lobes just behind
    s = length / 22.0
    cen = (0.0, 9.0)
    bm = bmesh.new(); rings = []
    for f in (1.0, 0.66, 0.33):
        rings.append([bm.verts.new(((cen[0] + (p[0] - cen[0]) * f) * s, (cen[1] + (p[1] - cen[1]) * f) * s, 0)) for p in pts])
    c = bm.verts.new((cen[0] * s, cen[1] * s, 0))
    for a, b in zip(rings[:-1], rings[1:]):
        for i in range(N_):
            j = (i + 1) % N_; bm.faces.new((a[i], a[j], b[j], b[i]))
    for i in range(N_):
        j = (i + 1) % N_; bm.faces.new((rings[-1][i], rings[-1][j], c))
    for v in bm.verts:
        x, y = v.co.x / length, v.co.y / length
        v.co.z = 0.07 * length * abs(x) * 2.2 - 0.20 * (y ** 2) * length * 0.8 + 0.05 * length * (x * 2) ** 2
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new("leaf_mesh"); bm.to_mesh(me); bm.free()
    for p in me.polygons: p.use_smooth = True
    return me
LEAF_ME = make_leaf_mesh(D["leaf_len"])

def place_leaf(pos, tip, normal_hint, size, name="leaf"):
    Y = Vector(tip).normalized(); Zr = Vector(normal_hint)
    Z = (Zr - Y * Zr.dot(Y)); 
    if Z.length < 1e-4: Z = Vector((0, 0, 1))
    Z.normalize(); X = Y.cross(Z)
    mtx = Matrix(((X.x, Y.x, Z.x), (X.y, Y.y, Z.y), (X.z, Y.z, Z.z))).to_4x4()
    o = bpy.data.objects.new(name, LEAF_ME); bpy.context.collection.objects.link(o)
    o.matrix_world = Matrix.Translation(pos) @ mtx @ Matrix.Scale(size, 4)
    o.data.materials.clear() if False else None
    if not o.data.materials: o.data.materials.append(M["leaf"])
    return o

def bez(p0, p1, p2, t):
    return (1 - t) ** 2 * p0 + 2 * t * (1 - t) * p1 + t * t * p2

def sample_poly(ctrl, n):
    """Catmull-Rom-ish smooth sampling through control points."""
    out = []
    for i in range(len(ctrl) - 1):
        p0 = ctrl[max(i - 1, 0)]; p1 = ctrl[i]; p2 = ctrl[i + 1]; p3 = ctrl[min(i + 2, len(ctrl) - 1)]
        for k in range(n):
            t = k / n
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3))
    out.append(ctrl[-1]); return out

plant = []
stem_mat = M["stem"]
def add_stem(ctrl, r):
    pts = sample_poly(ctrl, 4)
    s = tube_curve("stem", pts, r, stem_mat, res=2, order=4); plant.append(s); return pts

def leaf_on(p, tip, nh, size, petiole=0.018):
    tipv = Vector(tip).normalized()
    base = Vector(p) + tipv * petiole
    cyl_ = cyl_between("petiole", p, base, 0.0012, 8); assign(cyl_, stem_mat); plant.append(cyl_)
    plant.append(place_leaf(base, tipv, nh, size))

centre = Vector((0, 0, soil_top - 0.002))
for i in range(D["n_upright"]):
    a = 2 * math.pi * i / D["n_upright"] + random.uniform(-0.25, 0.25)
    out_ = Vector((math.cos(a), math.sin(a), 0))
    r0 = random.uniform(0.004, 0.022); h = random.uniform(0.060, 0.125); re = random.uniform(0.030, 0.062)
    da = abs((a - math.atan2(D["plant_gap_xy"][1], D["plant_gap_xy"][0]) + math.pi) % (2 * math.pi) - math.pi)
    if da < 0.9: re *= 0.35 + 0.65 * da / 0.9
    P0 = centre + out_ * r0
    P1 = P0 + Vector((0, 0, h * 0.75)) + out_ * (re * 0.35)
    P2 = P0 + Vector((0, 0, h)) + out_ * re
    ctrl = [P0, bez(P0, P1, P2, 0.35), bez(P0, P1, P2, 0.7), P2]
    add_stem(ctrl, 0.0017)
    for k, t in enumerate((0.45, 0.68, 0.88, 1.0)):
        p = bez(P0, P1, P2, t)
        side = 1 if k % 2 == 0 else -1
        ang = a + side * random.uniform(0.5, 1.1) + (0 if k < 3 else random.uniform(-0.3, 0.3))
        if k < 3: d = Vector((math.cos(ang), math.sin(ang), random.uniform(-0.65, -0.05)))      # outer leaves droop, faces turn outward
        else:     d = Vector((math.cos(ang) * 0.6, math.sin(ang) * 0.6, random.uniform(0.45, 0.9)))   # crown leaves reach up
        sz = random.uniform(0.70, 1.05) * (1.0 if k < 3 else 0.85)
        nh = Vector((0, 0, 1.0)) + Vector((math.cos(a), math.sin(a), 0)) * (0.6 if k < 3 else 0.15)
        leaf_on(p, d, nh, sz)

ta = math.radians(D["trail_angle"])
for j in range(D["n_trail"]):
    a = ta + (j - (D["n_trail"] - 1) / 2) * 0.42 + random.uniform(-0.05, 0.05)
    o_ = Vector((math.cos(a), math.sin(a), 0))
    ln = 1.0 if j == 1 else random.uniform(0.7, 0.9)
    zr = SHELL_TOP_W
    def at(r, z): return Vector((o_.x * r, o_.y * r, z))
    z_side = lambda z: shell_r(z - D["shell_z0"]) + 0.006
    ctrl = [at(0.020, soil_top + 0.002), at(0.050, soil_top + 0.018), at(0.078, POT_TOP + 0.001), at(0.086, POT_TOP - 0.030),
            at(0.090, SHELL_TOP_W + 0.040), at(0.098, zr + 0.006), at(0.113, zr + 0.003),
            at(z_side(zr - 0.010), zr - 0.012), at(z_side(zr - 0.040), zr - 0.040 * ln - 0.005),
            at(z_side(zr - 0.075 * ln) + 0.002, zr - 0.075 * ln)]
    ctrl[-1].z = max(ctrl[-1].z, 0.030)
    pts = add_stem(ctrl, 0.0017)
    # leaves along the vine: on the pot/rim, then hanging against the shell
    ncp = len(pts)
    for fr in (0.18, 0.32, 0.48, 0.60, 0.72, 0.84, 0.96):
        p = pts[int(fr * (ncp - 1))]; q = pts[min(int(fr * (ncp - 1)) + 3, ncp - 1)]
        along = (q - p)
        if along.length < 1e-6: along = Vector((o_.x, o_.y, -1))
        along.normalize()
        radial = Vector((p.x, p.y, 0)).normalized()
        side = 1 if int(fr * 100) % 2 else -1
        if p.z > SHELL_TOP_W + 0.005 and fr < 0.35:
            tip = Vector((o_.x, o_.y, 0.1)) + Vector((-o_.y, o_.x, 0)) * side * 0.7; nh = (0, 0, 1)
        elif p.z > SHELL_TOP_W - 0.002:
            tip = along * 0.6 + radial * 0.5 + Vector((-radial.y, radial.x, 0)) * side * 0.6; nh = radial * 0.5 + Vector((0, 0, 1))
        else:
            tip = Vector((0, 0, -1)) + radial * 0.25 + Vector((-radial.y, radial.x, 0)) * side * 0.45; nh = radial
        leaf_on(p + radial * 0.002, tip, nh, random.uniform(0.7, 1.0) * (0.9 if fr > 0.5 else 1.0), petiole=0.014)
bought += plant

# ---- light sensor: frosted dome in a thin white ring, flush in the rear rim ----
def build_sensor():
    sx_, sy_ = D["sensor_xy"]; tl = math.radians(D["sensor_tilt_deg"]); az = math.atan2(sy_, sx_)
    r = D["sensor_d"] / 2; rw = D["ring_w"]; rh = D["ring_h"]
    base = Vector((sx_, sy_, SHELL_TOP_W))
    rot = (0, tl, az)
    n = Vector((0, 0, 1)); n.rotate(__import__("mathutils").Euler(rot, "XYZ"))
    # ring: top stands 0.4 mm proud of the rim, body sunk into the seat
    ring = cyl("sensor_ring", r + rw, rh + 0.002, verts=64)
    bevel(ring, 0.0005, 2, 40); smooth(ring)
    ring.rotation_euler = rot; ring.location = base + n * (0.0004 - (rh + 0.002))
    assign(ring, M["shell"])
    top = base + n * 0.0004
    # dome: squashed half sphere, r 11 mm, 8 mm tall
    bm = bmesh.new(); res = bmesh.ops.create_uvsphere(bm, u_segments=48, v_segments=24, radius=r)
    for v in res["verts"]: v.co.z *= D["dome_h"] / r
    bmesh.ops.bisect_plane(bm, geom=list(bm.verts) + list(bm.edges) + list(bm.faces), plane_co=(0, 0, 0), plane_no=(0, 0, 1), clear_inner=True)
    me = bpy.data.meshes.new("m_sdome"); bm.to_mesh(me); bm.free()
    dome = bpy.data.objects.new("sensor_dome", me); bpy.context.collection.objects.link(dome)
    dome.rotation_euler = rot; dome.location = top
    for pl in me.polygons: pl.use_smooth = True
    me.materials.append(M["dome"])
    # dark sensor chip just under the dome
    chip = cyl("sensor_chip", r * 0.55, 0.0008, verts=32)
    chip.rotation_euler = rot; chip.location = top + n * 0.0003
    assign(chip, M["chip"])
    return [ring, dome, chip]
sensor_objs = build_sensor()
bought += sensor_objs

# ---- dock ramp (printed) + bought contacts, LED, cable, all parented to the ramp ----
ramp = parts["dock_ramp"]
Lr, bt_, bh_ = D["ramp_l"], D["backrest_t"], D["backrest_h"]
dock_extras = []
for s in (1, -1):
    y = s * D["post_y"]
    post = box("contact_post", D["post_d"], D["post_w"], D["post_h"], x=Lr - bt_ - D["post_d"] / 2, y=y, z0=D["post_z0"])
    bevel(post, 0.0015, 2, 40); smooth(post); assign(post, M["dark"]); dock_extras.append(post)
    rings = []
    for k in range(7):
        bpy.ops.mesh.primitive_torus_add(major_radius=0.0046, minor_radius=0.0012, major_segments=24, minor_segments=8,
                                         location=(Lr - bt_ - D["post_d"] - 0.0005, y, D["post_z0"] + 0.008 + k * 0.0042))
        t_ = bpy.context.active_object; t_.name = "coil"; smooth(t_); assign(t_, M["brass"]); rings.append(t_)
    dock_extras.append(join("spring_coil", rings))
bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=16, radius=0.011, location=(Lr - bt_ / 2, 0, bh_ - 0.002))
led = bpy.context.active_object; led.name = "led_dome"; led.scale = (1, 1, 0.9); apply_xf(led); smooth(led)
assign(led, M["led"]); dock_extras.append(led)
cab = [(Lr - bt_ / 2, -0.060, 0.025), (Lr + 0.003, -0.060, 0.025), (Lr + 0.010, -0.064, 0.016), (Lr + 0.011, -0.09, 0.005),
       (Lr + 0.011, -0.16, 0.0035), (Lr + 0.011, -0.30, 0.0035), (Lr + 0.011, -0.50, 0.0035)]
dock_extras.append(tube_curve("dock_cable", cab, 0.0033, M["cable"], res=3))
for o in dock_extras: o.parent = ramp
bought += dock_extras   # hidden in the exploded view

# ---- parent the robot to one root so scenes can pose it ----
bpy.ops.object.empty_add(type="PLAIN_AXES", location=(0, 0, 0)); root = bpy.context.active_object; root.name = "robot_root"
robot_objs = [shell, tray] + [o for o in bought if o not in dock_extras]
for o in robot_objs: o.parent = root
root_children = robot_objs

# ----------------------------------------------------------------------------------------
# Studio ground, lights, world, camera (used for assembly-hero and parts-exploded)
# ----------------------------------------------------------------------------------------
def area(name, loc, target, energy, size, color=(1, 1, 1)):
    bpy.ops.object.light_add(type="AREA", location=loc)
    l = bpy.context.active_object; l.name = name; l.data.energy = energy; l.data.size = size; l.data.color = color
    d = Vector(target) - Vector(loc); l.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    return l

bpy.ops.mesh.primitive_plane_add(size=40, location=(0, 0, 0))
ground = bpy.context.active_object; ground.name = "ground_studio"; assign(ground, M["ground"])

bpy.ops.object.camera_add()
cam = bpy.context.active_object; cam.name = "camera"; scene.camera = cam
cam.data.lens = 50; cam.data.sensor_width = 36; cam.data.clip_end = 60; cam.data.clip_start = 0.01
def aim(loc, target, cam_=None):
    c = cam_ or cam
    c.location = loc
    c.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()

scene.render.image_settings.file_format = "PNG"
for vt in ("Khronos PBR Neutral", "AgX", "Standard"):
    try: scene.view_settings.view_transform = vt; break
    except TypeError: pass

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
W_STUDIO = world(color=(0.30, 0.32, 0.36), strength=0.6)

L_STUDIO = [area("key", (0.35, -0.9, 1.1), (0, 0, 0.15), 60, 0.6, (1.0, 0.96, 0.9)),
            area("fill", (-0.9, -0.6, 0.4), (0, 0, 0.15), 14, 1.2, (0.88, 0.93, 1.0)),
            area("rim", (-0.5, 0.9, 0.7), (0, 0, 0.15), 40, 0.5, (1, 1, 1))]

# ----------------------------------------------------------------------------------------
# Scene dressing for the photo shots (render-only; not in the GLB)
# ----------------------------------------------------------------------------------------
def big_plane(name, size, mat):
    bpy.ops.mesh.primitive_plane_add(size=size, location=(0, 0, 0))
    o = bpy.context.active_object; o.name = name; assign(o, mat); return o

MAT = dict(
    patio=tile_material("Patio_stone", 0.45, srgb("#6C675F"), srgb("#58534C"), srgb("#262420"), 0.82, 0.45, 0.012, 0.5),
    pavers=tile_material("Wet_pavers", 0.32, srgb("#8A8A87"), srgb("#6E6F70"), srgb("#222322"), 0.38, 0.5, 0.018, 0.35),
    lawn=noise_material("Lawn", [(0.25, srgb("#17380F")), (0.75, srgb("#5E9630"))], 22, 8, 0.95, 160, 0.8, 0.9),
    stucco=noise_material("Stucco", [(0.35, srgb("#C4BDAD")), (0.7, srgb("#E0DACB"))], 8, 6, 0.92, 700, 0.12, 1.2),
    fence=fence_material("Fence_boards"),
    frame=make_mat("Window_frame", srgb("#0E0F0F"), 0.4, 0.0, 0.5),
)
ENV = {k: [] for k in ("hero", "detail", "night", "dock")}
ENV["hero"] += [big_plane("patio_hero", 200, MAT["patio"]), box("fence_hero", 0.08, 40.0, 1.8, x=-3.4, y=0, z0=0)]
assign(ENV["hero"][1], MAT["fence"])
ENV["detail"] += [big_plane("patio_detail", 200, MAT["patio"])]
ENV["night"] += [big_plane("lawn_night", 60, MAT["lawn"])]
ENV["dock"] += [big_plane("pavers_dock", 30, MAT["pavers"])]
wallA = box("wall_dock_a", 0.12, 3.0, 2.2, x=0, y=0, z0=0)   # re-placed below once the ramp pose is known
wallB = box("wall_dock_b", 3.0, 0.12, 2.2, x=0, y=0, z0=0)
for o in (wallA, wallB): assign(o, MAT["stucco"])
ENV["dock"] += [wallA, wallB]

LIGHTS = {}
def set_world(w_): scene.world = w_
WORLDS = {
    "hero": world(strength=0.55, gradient=[(0.0, (0.34, 0.20, 0.17)), (0.10, (0.16, 0.18, 0.34)), (0.55, (0.035, 0.06, 0.20))]),
    "detail": world(color=(0.55, 0.62, 0.72), strength=0.9),
    "night": world(color=(0.015, 0.025, 0.055), strength=0.3),
    "dock": world(color=(0.72, 0.75, 0.80), strength=0.45),
}

def set_visible(shot):
    for k, objs in ENV.items():
        for o in objs: o.hide_render = (k != shot)
    for k, ls in LIGHTS.items():
        for l in ls: l.hide_render = (k != shot)
    ground.hide_render = (shot not in ("assembly", "exploded"))
    for l in L_STUDIO: l.hide_render = (shot not in ("assembly", "exploded"))
    set_world(WORLDS[shot] if shot in WORLDS else W_STUDIO)

def look_basis(loc, target):
    f = (Vector(target) - Vector(loc)).normalized()
    r = f.cross(Vector((0, 0, 1))).normalized()
    u = r.cross(f).normalized()
    return f, r, u

# ----------------------------------------------------------------------------------------
# Save blend + GLB (robot + ramp assembly; ground, walls, lights excluded)
# ----------------------------------------------------------------------------------------
os.makedirs(BLEND, exist_ok=True); os.makedirs(RENDER, exist_ok=True); os.makedirs(SHOTS, exist_ok=True)
ramp.rotation_euler = (0, 0, math.pi); ramp.location = (-0.30, 0.0, 0)      # beside/behind the robot for the assembly pose
set_visible("assembly")
# GLB first (a clean assembly pose), then the blend
M["leaf_simple"] = make_mat("Pothos_leaf_simple", srgb("#3F7F2A"), 0.5, 0.0, 0.4)
M["eye_simple"] = make_mat("Transducer_mesh_simple", srgb("#1A1A1C"), 0.6)
LEAF_ME.materials.clear(); LEAF_ME.materials.append(M["leaf_simple"])
for o in eyes:
    if o.name.startswith("eye_face"): assign(o, M["eye_simple"])
bpy.ops.object.select_all(action="DESELECT")
for o in [root, ramp] + root_children + dock_extras: o.select_set(True)
bpy.context.view_layer.objects.active = root
bpy.ops.export_scene.gltf(filepath=os.path.join(BLEND, "robot-planter.glb"), export_format="GLB",
                          use_selection=True, export_draco_mesh_compression_enable=False, export_apply=True,
                          export_yup=True)
LEAF_ME.materials.clear(); LEAF_ME.materials.append(M["leaf"])
for o in eyes:
    if o.name.startswith("eye_face"): assign(o, M["eye_face"])
print("SAVED glb t=%.1fs" % (time.time() - t0))

# ----------------------------------------------------------------------------------------
# Render
# ----------------------------------------------------------------------------------------
def setup_engine():
    if ENGINE == "cycles":
        scene.render.engine = "CYCLES"
        c = scene.cycles; c.samples = SAMPLES; c.use_denoising = True; c.use_adaptive_sampling = True
        c.max_bounces = 8
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

def do_render(path, res, exposure=-0.4):
    scene.render.resolution_x, scene.render.resolution_y = res
    scene.view_settings.exposure = exposure
    scene.render.filepath = path
    r = time.time(); bpy.ops.render.render(write_still=True)
    print("RENDER %s %.1fs" % (os.path.basename(path), time.time() - r))

def pose_robot(loc=(0, 0, 0), pitch_deg=0.0):
    root.location = loc; root.rotation_euler = (0, math.radians(pitch_deg), 0)

# ---- scene lights (created now, toggled per shot) ----
LIGHTS["hero"] = []; LIGHTS["detail"] = []; LIGHTS["night"] = []; LIGHTS["dock"] = []

if DO_RENDER:
    setup_engine()
    cam.data.dof.use_dof = False

    # ===== assembly-hero: neutral studio, whole object + ramp, true 3/4 =====
    if "assembly" in ONLY:
        set_visible("assembly"); pose_robot()
        ramp.rotation_euler = (0, 0, math.pi); ramp.location = (-0.26, 0.26, 0)
        cam.data.lens = 50
        aim((0.80, 0.84, 0.19), (-0.07, 0.07, 0.15))
        do_render(os.path.join(RENDER, "assembly-hero.png"), D["asm_res"], -0.4)

    # ===== hero-blender: low 3/4 front-left at ~30 cm, patio, fence, porch lamp =====
    if "hero" in ONLY:
        set_visible("hero"); pose_robot()
        ramp.hide_render = True
        for o in dock_extras: o.hide_render = True
        az = math.radians(42); dist = 0.92
        loc = Vector((dist * math.cos(az), dist * math.sin(az), 0.30))
        f, r, u = look_basis(loc, (0, 0, 0.13))
        tgt = Vector((0, 0, 0.13)) - r * 0.13 + Vector((0, 0, 0.02))      # aim a bit left so the robot sits centre-right
        cam.data.lens = 40
        aim(loc, tgt)
        # warm porch lamp upper-left, cool fill from the right, gentle rim
        f, r, u = look_basis(loc, tgt)
        base = Vector((0, 0, 0.13))
        LIGHTS["hero"] = [
            area("porch_lamp", base - r * 1.1 + u * 1.2 - f * 0.1 + Vector((0, 0, 0.35)), base, 130, 0.35, (1.0, 0.66, 0.36)),
            area("dusk_fill", base + r * 1.4 + Vector((0, 0, 0.6)) + f * 0.4, base, 35, 1.6, (0.55, 0.68, 1.0)),
            area("hero_rim", base - f * 1.2 + Vector((0, 0, 0.9)) + r * 0.2, base, 40, 0.7, (1.0, 0.8, 0.6)),
        ]
        set_visible("hero")
        do_render(os.path.join(SHOTS, "hero-blender.png"), D["shot_res"], 0.0)

    # ===== detail-blender: close-up of the front face, f/2.8 on the eyes =====
    if "detail" in ONLY:
        set_visible("detail"); pose_robot()
        ramp.hide_render = True
        for o in dock_extras: o.hide_render = True
        az = math.radians(9)
        eye_world = Vector((Rs_floor + 0.009, D["eye_y"], D["shell_z0"] + D["eye_z"]))
        dist = 0.50
        tgt = Vector((0.05, -0.065, 0.100))
        loc = tgt + Vector((math.cos(az), math.sin(az), 0)) * dist + Vector((0, 0, -0.01))
        cam.data.lens = 50
        aim(loc, tgt)
        cam.data.dof.use_dof = True; cam.data.dof.aperture_fstop = 2.8
        cam.data.dof.focus_distance = (eye_world - loc).length
        f, r, u = look_basis(loc, tgt)
        base = Vector((0.05, -0.02, 0.10))
        LIGHTS["detail"] = [
            area("morning_key", base + r * -0.7 + u * 0.8 + Vector((0.5, 0, 0.3)), base, 90, 0.5, (1.0, 0.90, 0.75)),
            area("detail_fill", base + r * 0.9 + Vector((0.6, 0, 0.1)), base, 25, 1.0, (0.85, 0.92, 1.0)),
        ]
        set_visible("detail")
        do_render(os.path.join(SHOTS, "detail-blender.png"), D["shot_res"], -0.2)
        cam.data.dof.use_dof = False

    # ===== night-blender: second-floor window, high angle, lawn =====
    if "night" in ONLY:
        set_visible("night"); pose_robot()
        ramp.hide_render = True
        for o in dock_extras: o.hide_render = True
        az = math.radians(58)
        loc = Vector((math.cos(az), math.sin(az), 0)) * 5.0 + Vector((0, 0, 3.5))
        f, r, u = look_basis(loc, (0, 0, 0.1))
        tgt = Vector((0, 0, 0.1)) - r * 0.32 + u * 0.12                     # robot lands right of centre, a bit low
        cam.data.lens = 70
        aim(loc, tgt)
        f, r, u = look_basis(loc, tgt)
        # strong light, low, behind and to the right of the robot (as seen from the camera) so the shadow runs to the lower left
        shadow_dir = (-(f * 0.6 + r * 0.8)); shadow_dir.z = 0; shadow_dir.normalize()
        el = math.radians(13)
        ldir = Vector((shadow_dir.x * math.cos(el), shadow_dir.y * math.cos(el), -math.sin(el)))
        bpy.ops.object.light_add(type="SUN")
        sun = bpy.context.active_object; sun.name = "night_light"; sun.data.energy = 10.0; sun.data.color = (1.0, 0.88, 0.62)
        sun.data.angle = math.radians(1.2)
        sun.rotation_euler = ldir.to_track_quat("-Z", "Y").to_euler()
        glow = area("house_glow", loc * 0.55 + Vector((0, 0, -0.5)), (0, 0, 0.1), 25, 1.6, (1.0, 0.82, 0.55))
        LIGHTS["night"] = [sun, glow]
        # dark window-frame block in the left foreground, parented to the camera
        fr1 = box("window_frame_v", 0.22, 1.6, 0.05); assign(fr1, MAT["frame"])   # camera-space axes: x right, y up, z back
        fr1.parent = cam; fr1.location = (-0.262, 0.0, -0.75); fr1.rotation_euler = (0, 0, math.radians(1.5))
        fr2 = fr1
        ENV["night"] += [fr1]
        set_visible("night")
        do_render(os.path.join(SHOTS, "night-blender.png"), D["shot_res"], 0.1)
        for o in (fr1, fr2): o.hide_render = True

    # ===== dock-blender: robot backed onto the ramp in a two-wall corner, overcast =====
    if "dock" in ONLY:
        set_visible("dock")
        Lr_, bt2 = D["ramp_l"], D["backrest_t"]
        shell_rear = shell_r(0.050) + 0.0
        face_x = -(shell_rear + D["post_d"] + 0.003)                  # world x of the backrest front face
        ox = face_x + (Lr_ - bt2)
        ramp.rotation_euler = (0, 0, math.pi); ramp.location = (ox, 0.0, 0)
        ramp.hide_render = False
        for o in dock_extras: o.hide_render = False
        # robot rear wheels ride the wedge: pitch the robot about its centre
        xl = ox + D["wheel_x"]; hs = 0.003 + (D["ramp_rise"] - 0.003) * xl / Lr_
        th = math.degrees(math.asin(hs / (2 * D["wheel_x"])))
        pose_robot((0, 0, hs / 2), th)
        wall_ax = ox - (Lr_ + 0.016)                                 # wall A front face x
        wallA.location = (wall_ax - 0.06, 0.85, 0.0)
        wallB.location = (0.6, -0.26 - 0.06, 0.0)
        # wall boxes were created at origin with world-sized verts; set their object origins instead of re-building
        cam.data.lens = 45
        loc = Vector((0.16, 1.12, 0.27)); tgt = Vector((-0.10, -0.02, 0.135))
        aim(loc, tgt)
        f, r, u = look_basis(loc, tgt)
        base = Vector((-0.05, 0.0, 0.1))
        LIGHTS["dock"] = [area("overcast_sky", Vector((0, 0.2, 2.6)), base, 260, 3.5, (0.92, 0.95, 1.0)),
                          area("dock_soft_fill", base + Vector((0.8, 0.9, 0.5)), base, 30, 1.5, (0.95, 0.97, 1.0))]
        set_visible("dock")
        do_render(os.path.join(SHOTS, "dock-blender.png"), D["shot_res"], -0.1)
        pose_robot(); ramp.location = (-0.30, 0.04, 0)

    # ===== exploded layout: printed parts only =====
    if "exploded" in ONLY:
        set_visible("exploded")
        for o in bought: o.hide_render = True
        ramp.hide_render = False
        pose_robot()
        shell.location = (0.0, 0.0, 0.0)
        ramp.rotation_euler = (0, 0, 0); ramp.location = (-0.05, -0.33, 0.0)
        tray.location = (0.30, -0.14, 0.0)
        cam.data.lens = 50
        aim((0.80, -0.92, 0.52), (0.13, -0.06, 0.07))
        do_render(os.path.join(RENDER, "parts-exploded.png"), D["asm_res"], -0.4)

# save the blend last, in the assembly pose
pose_robot(); ramp.rotation_euler = (0, 0, math.pi); ramp.location = (-0.30, 0.04, 0)
shell.location = (0, 0, D["shell_z0"]); tray.location = (0, D["battery_y"], top)
for o in bought + [ramp]: o.hide_render = False
set_visible("assembly")
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(BLEND, "robot-planter.blend"))
print("DONE total %.1fs" % (time.time() - t0))
