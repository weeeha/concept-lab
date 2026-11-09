"""Walking planter (Concept) - Waveshare HexArth + printed carapace, pot, pothos, dock pad.

Run headless:
  /Applications/Blender.app/Contents/MacOS/Blender -b -P build_walking_planter.py -- [--samples 128] [--scale 1.0] [--no-render] [--only assembly,hero,detail,night,dock]

Single source of truth for the photo shots (render/shots/*.png), the studio render and the viewer GLB.
Units: Blender metres; the parameter dict D and all builder helpers named *_mm take millimetres.
Coordinates: robot front = +X, left = +Y, up = +Z. GLB (glTF is Y-up, -Z forward): export_yup keeps
Blender +X as glTF +X, so the FRONT of the robot faces +X in the GLB and its left side is glTF -Z.
HexArth numbers come from Waveshare's dimension drawing: 344.30 x 428.59 x 154.88 standing, body line 73.68
above ground, top plate 152.01 x 136.41, hips at (+-53, +-48) front/rear and (0, +-78) middle, 3 servos
45.2 x 24.7 x 37.3 per leg, ~20 mm carbon foot tubes.
"""
import bpy, bmesh, math, os, sys, time, random
from mathutils import Vector, Matrix

MM = 0.001
D = dict(
    # ---- Waveshare HexArth (mm) ----
    body_bottom=73.68, plate_top=154.88, plate_xy=(152.0, 136.4),
    hips=dict(F=(53.0, 48.0), M=(0.0, 78.1), R=(-53.0, 48.0)),        # left side, y mirrored for the right
    leg_az=dict(F=31.0, M=90.0, R=149.0),                             # degrees from +X, left side
    hip_z=117.0, servo=(45.2, 24.7, 37.3),
    L1=98.0, L2=100.0, foot_r=10.0, tip_r=10.6,                       # femur axis length, knee to tip-sphere centre
    reach_stand=127.0, reach_sit=70.0, belly_gap=10.0,
    step_fwd=22.0, step_back=18.0, lift_h=30.0, lift_legs=("FL", "MR", "RL"),
    # ---- printed carapace (mm) ----
    car_a=100.0, car_b=85.0, car_n=2.6, car_z0=146.0, car_h=56.0, car_fillet=24.0, car_plateau_d=60.0,
    # pot: 12 cm grower pot
    pot_top_d=120.0, pot_bot_d=95.0, pot_h=105.0, pot_wall=1.6, pot_sink=44.0, pot_x=-6.0, pot_clear=1.8,
    sensor_x=-83.0, sensor_d=22.0,
    # ---- pothos (small) ----
    pothos_seed=7, n_upright=9, n_trail=3, leaf_len=52.0,
    # ---- dock pad ----
    pad=(300.0, 300.0, 12.0), pad_r=26.0, contact_y=22.0,
    # ---- photo shots ----
    shot_res=(1672, 941), asm_res=(1600, 1200),
)
OUT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CAD, BLEND, RENDER = (os.path.join(OUT, n) for n in ("cad", "blender", "render"))
SHOTS = os.path.join(RENDER, "shots")
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
def arg(name, default):
    return argv[argv.index(name) + 1] if name in argv else default
SAMPLES = int(arg("--samples", "128"))
RSCALE = float(arg("--scale", "1.0"))
DO_RENDER = "--no-render" not in argv
ONLY = set(arg("--only", "assembly,hero,detail,night,dock").split(","))
SUFFIX = arg("--suffix", "")

# ----------------------------------------------------------------------------------------
# Helpers (copied from robot-planter/cad/build_robot_planter.py)
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
    rp = ramp_node(nt, [(0.55, dark), (0.70, light)]); nt.links.new(nz.outputs["Fac"], rp.inputs["Fac"])
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
# mm-based mesh builders (bmesh, no operators, so they are fast and shareable)
# ----------------------------------------------------------------------------------------
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.unit_settings.system = "METRIC"; scene.unit_settings.scale_length = 1.0

def _new_faces(bm, verts):
    fs = set()
    for v in verts:
        for f in v.link_faces: fs.add(f)
    return list(fs)

def add_box(bm, sx, sy, sz, c=(0, 0, 0), mat=0, bev=0.0, seg=2):
    r = bmesh.ops.create_cube(bm, size=1.0)
    vs = r["verts"]
    for v in vs: v.co = Vector((v.co.x * sx, v.co.y * sy, v.co.z * sz)) * MM + Vector(c) * MM
    fs = _new_faces(bm, vs)
    if bev > 0:
        es = list({e for f in fs for e in f.edges})
        res = bmesh.ops.bevel(bm, geom=es, offset=bev * MM, segments=seg, affect="EDGES", profile=0.5)
        fs = list(res["faces"]) + fs
        fs = [f for f in set(fs) if f.is_valid]
    for f in fs: f.material_index = mat
    return fs

def add_cyl(bm, r, h, c=(0, 0, 0), axis="z", mat=0, n=32, r2=None):
    res = bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=n, radius1=r * MM, radius2=(r if r2 is None else r2) * MM, depth=h * MM)
    vs = res["verts"]
    if axis == "x": rot = Matrix.Rotation(math.pi / 2, 3, "Y")
    elif axis == "y": rot = Matrix.Rotation(math.pi / 2, 3, "X")
    else: rot = Matrix.Identity(3)
    for v in vs: v.co = rot @ v.co + Vector(c) * MM
    fs = _new_faces(bm, vs)
    for f in fs: f.material_index = mat
    return fs

def add_sphere(bm, r, c=(0, 0, 0), mat=0, seg=24, sz=1.0):
    res = bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=max(6, seg // 2), radius=r * MM)
    vs = res["verts"]
    for v in vs: v.co = Vector((v.co.x, v.co.y, v.co.z * sz)) + Vector(c) * MM
    fs = _new_faces(bm, vs)
    for f in fs: f.material_index = mat
    return fs

def to_mesh(name, bm):
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    return me

def mesh_box(name, sx, sy, sz, bev=0.0, seg=2):
    bm = bmesh.new(); add_box(bm, sx, sy, sz, bev=bev, seg=seg); return to_mesh(name, bm)

def mesh_cyl(name, r, h, axis="z", n=32, r2=None):
    bm = bmesh.new(); add_cyl(bm, r, h, axis=axis, n=n, r2=r2); return to_mesh(name, bm)

def mesh_prism(name, pts, z0, z1):
    bm = bmesh.new()
    lo = [bm.verts.new((x * MM, y * MM, z0 * MM)) for x, y in pts]
    hi = [bm.verts.new((x * MM, y * MM, z1 * MM)) for x, y in pts]
    n = len(pts)
    bm.faces.new(lo[::-1]); bm.faces.new(hi)
    for i in range(n):
        j = (i + 1) % n; bm.faces.new((lo[i], lo[j], hi[j], hi[i]))
    return to_mesh(name, bm)

def oct_pts(hx, hy, c):
    return [(-hx + c, -hy), (hx - c, -hy), (hx, -hy + c), (hx, hy - c), (hx - c, hy), (-hx + c, hy), (-hx, hy - c), (-hx, -hy + c)]

def put(name, me, mat=None, parent=None, loc=(0, 0, 0), rot=(0, 0, 0), smooth_it=True):
    """Create an object (mm local coordinates) and give it a material (or list of slots)."""
    ob = bpy.data.objects.new(name, me)
    bpy.context.collection.objects.link(ob)
    if mat is not None and len(me.materials) == 0:
        for m_ in (mat if isinstance(mat, (list, tuple)) else [mat]): me.materials.append(m_)
    ob.parent = parent
    ob.location = Vector(loc) * MM
    ob.rotation_euler = rot
    if smooth_it and not me.get("smoothed"):
        smooth(ob); me["smoothed"] = 1
    return ob

def empty(name, parent=None, loc=(0, 0, 0), rot=(0, 0, 0)):
    e = bpy.data.objects.new(name, None); e.empty_display_type = "PLAIN_AXES"; e.empty_display_size = 0.02
    bpy.context.collection.objects.link(e)
    e.parent = parent; e.location = Vector(loc) * MM; e.rotation_euler = rot
    return e

# ----------------------------------------------------------------------------------------
# Materials
# ----------------------------------------------------------------------------------------
def carbon_material(name):
    m, nt, bsdf = new_nodes_mat(name)
    tc = N(nt, "ShaderNodeTexCoord"); mp = N(nt, "ShaderNodeMapping")
    mp.inputs["Rotation"].default_value = (0, 0, math.radians(45))
    nt.links.new(tc.outputs["Object"], mp.inputs["Vector"])
    ck = N(nt, "ShaderNodeTexChecker"); ck.inputs["Scale"].default_value = 520
    ck.inputs["Color1"].default_value = (0.010, 0.010, 0.012, 1); ck.inputs["Color2"].default_value = (0.055, 0.055, 0.06, 1)
    nt.links.new(mp.outputs["Vector"], ck.inputs["Vector"])
    nt.links.new(ck.outputs["Color"], bsdf.inputs["Base Color"]); bsdf.inputs["Roughness"].default_value = 0.38
    for k in ("Coat Weight", "Clearcoat"):
        if k in bsdf.inputs: bsdf.inputs[k].default_value = 0.35; break
    bump_from(nt, ck.outputs["Fac"], bsdf, 0.12, 0.0004)
    out = [n for n in nt.nodes if n.bl_idname == "ShaderNodeOutputMaterial"][0]
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    m.diffuse_color = (0.03, 0.03, 0.035, 1)
    return m

def soil_material(name):
    m = noise_material(name, [(0.35, srgb("#2B1E15")), (0.7, srgb("#4A362A"))], 900, 6, 0.95, 2400, 0.5)
    return m

MT = dict(
    shell=make_mat("PETG_warm_white", srgb("#E6E1D5"), 0.62, 0.0, 0.35),
    black=make_mat("HexArth_black", srgb("#161617"), 0.55, 0.0, 0.45),
    servo=make_mat("Servo_black", srgb("#0F0F10"), 0.48, 0.0, 0.5),
    label=make_mat("Servo_label_green", srgb("#1F8F3C"), 0.5, 0.0, 0.4),
    silver=make_mat("Horn_silver", srgb("#C9CCD1"), 0.28, 1.0),
    screw=make_mat("Screw_dark", srgb("#1B1B1D"), 0.4, 0.8),
    gold=make_mat("Standoff_brass", srgb("#C79A3B"), 0.3, 1.0),
    pcb=make_mat("PCB_dark", srgb("#10202A"), 0.45, 0.0, 0.5),
    rubber=make_mat("Rubber_black", srgb("#0C0C0C"), 0.85, 0.0, 0.2),
    glass=make_mat("OLED_glass", srgb("#06090C"), 0.12, 0.0, 0.9),
    pot=make_mat("Pot_terracotta_plastic", srgb("#B05A3C"), 0.52, 0.0, 0.45),
    soil=soil_material("Soil"),
    leca=make_mat("LECA_pebble", srgb("#A65F36"), 0.9, 0.0, 0.2),
    stem=make_mat("Stem", srgb("#7BA843"), 0.55),
    wire_red=make_mat("Wire_red", srgb("#B3201C"), 0.5), wire_white=make_mat("Wire_white", srgb("#E8E8E4"), 0.5),
    wire_black=make_mat("Wire_black", srgb("#0B0B0B"), 0.5),
    cable=make_mat("Cable_black", srgb("#0C0C0D"), 0.45, 0.0, 0.5),
    dome=make_mat("Sensor_dome_frosted", srgb("#E9EEF0"), 0.34, 0.0, 0.5),
    chip=make_mat("Sensor_chip", srgb("#15181B"), 0.4, 0.0, 0.4),
    brass=make_mat("Brass", srgb("#C79A3B"), 0.3, 1.0),
    contact_base=make_mat("Contact_housing", srgb("#18181A"), 0.5),
)
try:
    b_ = MT["dome"].node_tree.nodes["Principled BSDF"]
    for k in ("Transmission Weight", "Transmission"):
        if k in b_.inputs: b_.inputs[k].default_value = 0.85; break
except Exception as e: print("dome mat", e)
MT["carbon"] = carbon_material("Carbon_tube")
MT["leaf"] = leaf_material("Pothos_leaf", (0.022, 0.12, 0.03), (0.30, 0.40, 0.07))

# ----------------------------------------------------------------------------------------
# Robot root + HexArth body
# ----------------------------------------------------------------------------------------
root = empty("robot_root")
body = empty("hexarth_body", root)

def build_body():
    bt, hz = D["body_bottom"], D["hip_z"]
    put("body_plate_lower", mesh_prism("m_plate_lo", oct_pts(70, 62, 20), bt, bt + 2.6), MT["black"], body)
    put("body_core", mesh_prism("m_core", oct_pts(50, 42, 12), bt + 2.6, 126.0), MT["black"], body)
    put("body_deck", mesh_prism("m_deck", oct_pts(70, 62, 20), 126.0, 128.6), MT["black"], body)
    # side rails: the dark plates visible between the leg roots
    for s in (1, -1):
        put("side_rail", mesh_box("m_rail", 96, 3.0, 40.0, bev=1.0), MT["black"], body, loc=(0, s * 49.0, 98.0))
    # standoffs, PCB, Pi (seen through the gap under the carapace skirt)
    bm = bmesh.new()
    for x in (-50, 0, 50):
        for y in (-38, 38):
            add_cyl(bm, 3.4, 23.8, c=(x, y, 128.6 + 11.9), mat=0, n=14)
    put("standoffs", to_mesh("m_standoffs", bm), MT["gold"], body)
    put("pcb", mesh_box("m_pcb", 112, 78, 1.8, bev=0.4, seg=1), MT["pcb"], body, loc=(0, 0, 136.0))
    put("pi_board", mesh_box("m_pi", 86, 56, 16, bev=1.0), MT["black"], body, loc=(-4, 0, 145.0))
    put("top_plate", mesh_prism("m_top", oct_pts(76, 68, 22), 152.4, D["plate_top"]), MT["black"], body)
    # front face: OLED window, button and LED (the HexArth side view shows them), on the core's front face (x = 50)
    put("oled", mesh_box("m_oled", 1.2, 30, 12, bev=0.3, seg=1), MT["glass"], body, loc=(50.6, 0, 100.0))
    put("btn", mesh_cyl("m_btn", 5.0, 3.0, "x", 24), MT["silver"], body, loc=(51.5, 22.0, 100.0))
    put("btn2", mesh_cyl("m_btn2", 3.2, 3.0, "x", 24), MT["silver"], body, loc=(51.5, 22.0, 86.0))
    # belly contacts (for the dock): two brass discs under the lower plate
    for s in (1, -1):
        put("belly_contact", mesh_cyl("m_bc", 5.5, 1.6, "z", 24), MT["brass"], body, loc=(0, s * D["contact_y"], bt - 0.8))
build_body()

# ----------------------------------------------------------------------------------------
# Legs: fixed coxa servo -> yaw (hip) -> femur pitch -> tibia/foot pitch
# ----------------------------------------------------------------------------------------
def make_servo_mesh():
    sx, sy, sz = D["servo"]
    bm = bmesh.new()
    add_box(bm, sx, sy, sz, mat=0, bev=1.1, seg=2)
    add_box(bm, 55.0, sy, 2.4, c=(0, 0, -sz / 2 + 4.5), mat=0, bev=0.5, seg=1)
    for xs in (-25.2, 25.2):
        add_cyl(bm, 1.7, 1.0, c=(xs, 0, -sz / 2 + 6.4), mat=3, n=10)
    add_box(bm, 24, 0.5, 11, c=(-5, sy / 2 + 0.1, 3), mat=1)
    add_cyl(bm, 6.5, 2.4, c=(sx / 2 - 8, 0, sz / 2 + 1.0), mat=2, n=24)
    add_cyl(bm, 1.8, 2.8, c=(sx / 2 - 8, 0, sz / 2 + 1.5), mat=3, n=10)
    return to_mesh("m_servo", bm)
SERVO_ME = make_servo_mesh()
for m_ in (MT["servo"], MT["label"], MT["silver"], MT["screw"]): SERVO_ME.materials.append(m_)
HORN_ME = None

LEGS = {}
def build_leg(name, hx, hy, az_deg, side):
    az = math.radians(az_deg); ux, uy = math.cos(az), math.sin(az)
    hz = D["hip_z"]; tsg = side
    L1 = D["L1"]; fr, tr = D["foot_r"], D["tip_r"]
    sx_, sy_, sz_ = D["servo"]
    # fixed coxa servo, long axis along the tangent, tucked inboard of the hip axis
    put(name + "_coxa_servo", SERVO_ME, None, body, loc=(hx - 23 * ux, hy - 23 * uy, hz - 2.5 - sz_ / 2), rot=(0, 0, az + math.pi / 2 + (0 if tsg > 0 else math.pi)))
    hipE = empty(name + "_hip", body, loc=(hx, hy, hz), rot=(0, 0, az))
    put(name + "_hip_bracket", mesh_box("m_hipbr", 22, 27, 36, bev=2.0), MT["black"], hipE, loc=(1, 0, -2))
    put(name + "_hip_horn", mesh_cyl("m_horn", 9.0, 2.5, "y", 28), MT["silver"], hipE, loc=(0, tsg * 14.6, 0))
    put(name + "_hip_horn_screw", mesh_cyl("m_hornscrew", 3.0, 3.2, "y", 12), MT["screw"], hipE, loc=(0, tsg * 15.3, 0))
    femE = empty(name + "_femur", hipE)
    put(name + "_femur_servo", SERVO_ME, None, femE, loc=(12 + sx_ / 2, tsg * -6.0, 0), rot=(0, 0, 0 if tsg > 0 else math.pi))
    put(name + "_femur_arm", mesh_box("m_arm", 52, 24, 27, bev=3.0), MT["black"], femE, loc=(L1 - 22, tsg * -1.0, 1.0))
    put(name + "_knee_block", mesh_box("m_kneeblk", 30, 28, 30, bev=3.0), MT["black"], femE, loc=(L1 - 1, 0, 0))
    tibE = empty(name + "_tibia", femE, loc=(L1, 0, 0))
    put(name + "_tibia_servo", SERVO_ME, None, tibE, loc=(34.0, tsg * 6.0, 0), rot=(0, 0, 0 if tsg > 0 else math.pi))
    put(name + "_knee_horn", mesh_cyl("m_horn", 9.0, 2.5, "y", 28), MT["silver"], tibE, loc=(0, tsg * 19.0, 0))
    put(name + "_knee_horn_screw", mesh_cyl("m_hornscrew", 3.0, 3.2, "y", 12), MT["screw"], tibE, loc=(0, tsg * 19.8, 0))
    put(name + "_sleeve", mesh_cyl("m_sleeve", 13.5, 16, "x", 28), MT["black"], tibE, loc=(54.0, tsg * 2.0, 0))
    put(name + "_foot_tube", mesh_cyl("m_foot", fr, 80, "x", 28), MT["carbon"], tibE, loc=(52.0, tsg * 2.0, 0))
    bm = bmesh.new()
    add_cyl(bm, tr, 8, c=(96.0, 0, 0), axis="x", n=28); add_sphere(bm, tr, c=(100.0, 0, 0), seg=28)
    put(name + "_foot_tip", to_mesh("m_tip", bm), MT["rubber"], tibE, loc=(0, tsg * 2.0, 0))
    LEGS[name] = dict(hipE=hipE, femE=femE, tibE=tibE, hip=(hx, hy), az=az, side=side, wires=[])

for side_name, s in (("L", 1), ("R", -1)):
    for k in ("F", "M", "R"):
        hx, hy = D["hips"][k]; azd = D["leg_az"][k]
        build_leg(k + side_name, hx, hy * s, azd * s, s)
print("legs built", len(LEGS))

def solve_leg(L, target, dz):
    """target = world tip-sphere centre (mm, root frame); dz = body z offset. Sets the joint rotations."""
    hx, hy = L["hip"]; hz = D["hip_z"] + dz
    tx, ty, tz = target
    psi = math.atan2(ty - hy, tx - hx)
    R = math.hypot(tx - hx, ty - hy); H = tz - hz
    a, b = D["L1"], D["L2"]
    d = min(math.hypot(R, H), a + b - 0.5)
    x = (d * d + a * a - b * b) / (2 * d); h = math.sqrt(max(a * a - x * x, 0))
    dirv = Vector((R, H)).normalized(); perp = Vector((-dirv.y, dirv.x))
    K = x * dirv + h * perp; C = Vector((R, H)) if d < a + b - 0.5 else (a + b - 0.5) * dirv
    alpha = math.atan2(K.y, K.x); gamma = math.atan2(-(C.y - K.y), C.x - K.x)
    L["hipE"].rotation_euler = (0, 0, psi)
    L["femE"].rotation_euler = (0, -alpha, 0)
    L["tibE"].rotation_euler = (0, gamma + alpha, 0)
    return K

def pose_robot(pose="standing", ground=0.0):
    """pose: standing | sitting | midstep. ground = world height (mm) of the surface under the feet."""
    sitting = pose == "sitting"
    dz = (ground + D["belly_gap"] - D["body_bottom"]) if sitting else ground * 0.0
    body.location = (0, 0, dz * MM)
    reach = D["reach_sit"] if sitting else D["reach_stand"]
    for name, L in LEGS.items():
        hx, hy = L["hip"]; az = L["az"]
        tx = hx + reach * math.cos(az); ty = hy + reach * math.sin(az); lift = 0.0
        if pose == "midstep":
            if name in D["lift_legs"]: tx += D["step_fwd"]; lift = D["lift_h"]
            else: tx -= D["step_back"]
        solve_leg(L, (tx, ty, ground + lift + D["tip_r"]), dz)
    bpy.context.view_layer.update()
    rebuild_wires()
    lows = {n: round((L["tibE"].matrix_world @ Vector((D["L2"] * MM, 0, 0))).z / MM - D["tip_r"], 1) for n, L in LEGS.items()}
    print("POSE", pose, "foot-tip bottom z (mm):", lows)

# wires: red / white / black servo leads looping between the servos, rebuilt for every pose
WIRE_OBJS = []
def rebuild_wires():
    for o in WIRE_OBJS:
        bpy.data.objects.remove(o, do_unlink=True)
    WIRE_OBJS.clear()
    rinv = root.matrix_world.inverted()
    for name, L in LEGS.items():
        tsg = L["side"]
        def W(e, p): return rinv @ (e.matrix_world @ (Vector((p[0], tsg * p[1], p[2])) * MM))
        hipE, femE, tibE = L["hipE"], L["femE"], L["tibE"]
        for i, (mname, off) in enumerate((("wire_red", -1.7), ("wire_white", 0.0), ("wire_black", 1.7))):
            # loop 1: hip bracket -> femur servo
            a = W(hipE, (-8, 14.5 + off, 10)); b = W(femE, (30, tsg * 0 + 13.5 + off, 8))
            m_ = (a + b) / 2 + Vector((0, 0, -10 * MM))
            WIRE_OBJS.append(tube_curve("wire", [a, a.lerp(m_, 0.5) + Vector((0, 0, -5 * MM)), m_, b.lerp(m_, 0.5) + Vector((0, 0, -3 * MM)), b], 1.1 * MM, MT[mname], res=2))
            # loop 2: femur servo -> tibia servo, sagging below
            a = W(femE, (50, 13.5 + off, 14)); b = W(tibE, (28, 18.5 + off, 14))
            mid = (a + b) / 2 + Vector((0, 0, -26 * MM))
            WIRE_OBJS.append(tube_curve("wire", [a, a.lerp(mid, 0.55), mid, b.lerp(mid, 0.5), b], 1.1 * MM, MT[mname], res=2))
    for o in WIRE_OBJS: o.parent = root

# ----------------------------------------------------------------------------------------
# Printed carapace with pot recess and sensor dome
# ----------------------------------------------------------------------------------------
CA, CB, CN = D["car_a"], D["car_b"], D["car_n"]
CH = D["car_h"]; CZ0 = D["car_z0"]; CTOP = CZ0 + CH
def sup_pts(a, b, n, N_=128):
    pts = []
    for k in range(N_):
        t = 2 * math.pi * k / N_; c, s = math.cos(t), math.sin(t)
        pts.append((a * math.copysign(abs(c) ** (2 / n), c), b * math.copysign(abs(s) ** (2 / n), s)))
    return pts
PROFILE = rounded_profile([(8, 0, 0), (0, 0, 3.0), (5, CH, D["car_fillet"]), (D["car_plateau_d"], CH, 0)], n=12)
UPPER = PROFILE[min(range(len(PROFILE)), key=lambda i: PROFILE[i][0]):]
def z_surf(d):
    """carapace top surface height (mm above carapace bottom) at inset d from the outline."""
    d = max(d, 0.0)
    for (d0, z0), (d1, z1) in zip(UPPER[:-1], UPPER[1:]):
        if d0 <= d <= d1 and d1 > d0: return z0 + (z1 - z0) * (d - d0) / (d1 - d0)
    return UPPER[-1][1] if d > UPPER[-1][0] else 0.0
def z_slope(d):
    return (z_surf(d + 0.6) - z_surf(d - 0.6)) / 1.2

def build_carapace():
    bm = bmesh.new(); rings = []
    for (d, z) in PROFILE:
        rings.append([bm.verts.new((x * MM, y * MM, z * MM)) for (x, y) in sup_pts(CA - d, CB - d, CN)])
    N_ = len(rings[0])
    for r0, r1 in zip(rings[:-1], rings[1:]):
        for k in range(N_):
            k2 = (k + 1) % N_; bm.faces.new((r0[k], r0[k2], r1[k2], r1[k]))
    bm.faces.new(rings[0][::-1]); bm.faces.new(rings[-1])
    me = to_mesh("carapace_m", bm)
    ob = bpy.data.objects.new("carapace", me); bpy.context.collection.objects.link(ob)
    me.materials.append(MT["shell"])
    ob.location = (0, 0, CZ0 * MM); apply_xf(ob)       # world position so the cut tools sit in world space
    smooth(ob, 40)
    px = D["pot_x"]; cl = D["pot_clear"]
    def potr(h): return D["pot_bot_d"] / 2 + (D["pot_top_d"] - D["pot_bot_d"]) / 2 * h / D["pot_h"]
    sink = D["pot_sink"]; floor_z = CTOP - sink
    # pot pocket: tapered, a hair wider than the pot
    pock = cone("_pocket", (potr(0) + cl) * MM, (potr(sink + 2) + cl) * MM, (sink + 2 + 0.5) * MM, x=px * MM, y=0, z0=floor_z * MM, verts=128)
    cut(ob, pock)
    # drain hole through the pocket floor
    cut(ob, cyl("_drain", 9 * MM, 0.05, x=px * MM, z0=floor_z * MM - 0.02, verts=32))
    # sensor recess (tilted to the local surface)
    sx = D["sensor_x"]; dd = CA + sx
    th = -math.atan(z_slope(dd))
    zc = CZ0 + z_surf(dd)
    cut(ob, cyl("_srec", (D["sensor_d"] / 2 + 1.6) * MM, 0.012, x=sx * MM, y=0, z0=(zc - 5.0) * MM, verts=48, rot=(0, th, 0)))
    # vent slots on both flanks, behind the pot: 6 shallow slots each
    for sg in (1, -1):
        for k in range(6):
            xk = -62 + k * 7.5
            yw = CB * (1 - (abs(xk) / CA) ** CN) ** (1 / CN) - 1.0
            slot = box("_slot", 0.0032, 0.010, 0.020, x=xk * MM, y=sg * (yw + 3.0) * MM, z0=(CZ0 + 20) * MM)
            bevel(slot, 0.0012, 2, 30)
            cut(ob, slot)
    smooth(ob, 40)
    return ob, th, zc
carapace, SENS_TH, SENS_Z = build_carapace()

def build_sensor():
    sx = D["sensor_x"]; r = D["sensor_d"] / 2
    ctr = (sx, 0, SENS_Z - 2.6)
    # local frame rotated to the surface normal
    holder = empty("sensor_holder", body, loc=ctr, rot=(0, SENS_TH, 0))
    put("sensor_ring", mesh_cyl("m_sring", r + 1.7, 3.0, "z", 48, r2=r + 1.7), MT["shell"], holder, loc=(0, 0, 2.6))
    bm = bmesh.new(); add_sphere(bm, r, c=(0, 0, 0), seg=40, sz=0.30)
    bmesh.ops.bisect_plane(bm, geom=list(bm.verts) + list(bm.edges) + list(bm.faces), plane_co=(0, 0, 0), plane_no=(0, 0, 1), clear_inner=True)
    me = to_mesh("m_sdome", bm)
    put("sensor_dome", me, MT["dome"], holder, loc=(0, 0, 2.6))
    put("sensor_chip", mesh_cyl("m_chip", r * 0.55, 0.8, "z", 24), MT["chip"], holder, loc=(0, 0, 2.5))
build_sensor()
carapace.parent = body
# dark gasket strip under the skirt (printed shell meets the black body plates)
gk = put("carapace_gasket", mesh_prism("m_gasket", sup_pts(CA - 3.0, CB - 3.0, CN, 96), CZ0 - 3.2, CZ0 + 0.4), MT["black"], body, smooth_it=True)
def potr(h): return D["pot_bot_d"] / 2 + (D["pot_top_d"] - D["pot_bot_d"]) / 2 * h / D["pot_h"]
PX = D["pot_x"]; POT_Z0 = CTOP - D["pot_sink"]; POT_TOP = POT_Z0 + D["pot_h"]
# collar ring softening the pot opening (printed, same part as the carapace)
bpy.ops.mesh.primitive_torus_add(major_radius=(potr(D["pot_sink"]) + D["pot_clear"] + 1.6) * MM, minor_radius=1.7 * MM, major_segments=96, minor_segments=12,
                                 location=(PX * MM, 0, (CTOP - 0.4) * MM))
collar = bpy.context.active_object; collar.name = "pot_collar"; collar.data.materials.append(MT["shell"]); smooth(collar); collar.parent = body

# ----------------------------------------------------------------------------------------
# 12 cm grower pot, soil + LECA, small pothos
# ----------------------------------------------------------------------------------------
pot = cone("pot", D["pot_bot_d"] / 2 * MM, D["pot_top_d"] / 2 * MM, D["pot_h"] * MM, x=PX * MM, z0=POT_Z0 * MM, verts=96)
w = D["pot_wall"]
inner = cone("_pi", (D["pot_bot_d"] / 2 - w) * MM, (D["pot_top_d"] / 2 - w) * MM, (D["pot_h"] - w + 0.5) * MM, x=PX * MM, z0=(POT_Z0 + w) * MM, verts=96)
cut(pot, inner)
bpy.ops.mesh.primitive_torus_add(major_radius=(D["pot_top_d"] / 2 - 0.6) * MM, minor_radius=2.4 * MM, major_segments=96, minor_segments=12,
                                 location=(PX * MM, 0, (POT_TOP - 2.4) * MM))
rim = bpy.context.active_object; rim.name = "_rim"; union(pot, rim)
band = cone("_band", (potr(92) + 0.9) * MM, (D["pot_top_d"] / 2 + 0.9) * MM, 13.0 * MM, x=PX * MM, z0=(POT_TOP - 13.0) * MM, verts=96)
union(pot, band)
smooth(pot, 40); assign(pot, MT["pot"]); pot.parent = body
SOIL_TOP = POT_TOP - 14.0
soil = cyl("soil", (potr(SOIL_TOP - POT_Z0) - w - 0.4) * MM, 10.0 * MM, x=PX * MM, z0=(SOIL_TOP - 10.0) * MM, verts=64)
smooth(soil); assign(soil, MT["soil"]); soil.parent = body
random.seed(D["pothos_seed"])
bm = bmesh.new()
for i in range(70):
    rr = math.sqrt(random.random()) * (potr(SOIL_TOP - POT_Z0) - 7)
    aa = random.uniform(0, 2 * math.pi); r_ = random.uniform(2.6, 4.2)
    add_sphere(bm, r_, c=(PX + rr * math.cos(aa), rr * math.sin(aa), SOIL_TOP + 0.6), seg=8, sz=random.uniform(0.7, 0.95))
leca = put("leca", to_mesh("m_leca", bm), MT["leca"], body)

def make_leaf_mesh(length):
    N_ = 40; pts = []
    for i in range(N_):
        t = 2 * math.pi * i / N_
        x = 16 * math.sin(t) ** 3; yv = 13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t)
        pts.append((0.66 * x, 5 - yv))
    s = length / 22.0; cen = (0.0, 9.0)
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
LEAF_ME = make_leaf_mesh(D["leaf_len"] * MM)
LEAF_ME.materials.append(MT["leaf"])

def place_leaf(pos, tip, normal_hint, size, name="leaf"):
    Y = Vector(tip).normalized(); Zr = Vector(normal_hint)
    Z = (Zr - Y * Zr.dot(Y))
    if Z.length < 1e-4: Z = Vector((0, 0, 1))
    Z.normalize(); X = Y.cross(Z)
    mtx = Matrix(((X.x, Y.x, Z.x), (X.y, Y.y, Z.y), (X.z, Y.z, Z.z))).to_4x4()
    o = bpy.data.objects.new(name, LEAF_ME); bpy.context.collection.objects.link(o)
    o.matrix_world = Matrix.Translation(pos) @ mtx @ Matrix.Scale(size, 4)
    return o

def bez(p0, p1, p2, t): return (1 - t) ** 2 * p0 + 2 * t * (1 - t) * p1 + t * t * p2
def sample_poly(ctrl, n):
    out = []
    for i in range(len(ctrl) - 1):
        p0 = ctrl[max(i - 1, 0)]; p1 = ctrl[i]; p2 = ctrl[i + 1]; p3 = ctrl[min(i + 2, len(ctrl) - 1)]
        for k in range(n):
            t = k / n
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3))
    out.append(ctrl[-1]); return out
plant = []
def add_stem(ctrl, r):
    pts = sample_poly(ctrl, 4)
    s = tube_curve("stem", pts, r, MT["stem"], res=2, order=4); plant.append(s); return pts
def leaf_on(p, tip, nh, size, petiole=0.013):
    tipv = Vector(tip).normalized(); base = Vector(p) + tipv * petiole
    c_ = cyl_between("petiole", p, base, 0.0009, 8); assign(c_, MT["stem"]); plant.append(c_)
    plant.append(place_leaf(base, tipv, nh, size))
V = lambda x, y, z: Vector((x, y, z)) * MM
centre = V(PX, 0, SOIL_TOP - 2)
for i in range(D["n_upright"]):
    a = 2 * math.pi * i / D["n_upright"] + random.uniform(-0.25, 0.25)
    out_ = Vector((math.cos(a), math.sin(a), 0))
    r0 = random.uniform(3, 16) * MM; h = random.uniform(48, 95) * MM; re = random.uniform(18, 42) * MM
    P0 = centre + out_ * r0
    P1 = P0 + Vector((0, 0, h * 0.75)) + out_ * (re * 0.35)
    P2 = P0 + Vector((0, 0, h)) + out_ * re
    add_stem([P0, bez(P0, P1, P2, 0.35), bez(P0, P1, P2, 0.7), P2], 0.0012)
    for k, t in enumerate((0.45, 0.68, 0.88, 1.0)):
        p = bez(P0, P1, P2, t); side = 1 if k % 2 == 0 else -1
        ang = a + side * random.uniform(0.5, 1.1) + (0 if k < 3 else random.uniform(-0.3, 0.3))
        if k < 3: d = Vector((math.cos(ang), math.sin(ang), random.uniform(-0.65, -0.05)))
        else: d = Vector((math.cos(ang) * 0.6, math.sin(ang) * 0.6, random.uniform(0.45, 0.9)))
        sz = random.uniform(0.70, 1.05) * (1.0 if k < 3 else 0.85)
        nh = Vector((0, 0, 1.0)) + Vector((math.cos(a), math.sin(a), 0)) * (0.6 if k < 3 else 0.15)
        leaf_on(p, d, nh, sz)

def ray_r(theta, d):
    """distance from the pot centre along azimuth theta to the carapace outline inset by d (mm)."""
    lo, hi = 0.0, 220.0
    for _ in range(40):
        mid = (lo + hi) / 2
        x = PX + mid * math.cos(theta); y = mid * math.sin(theta)
        f = (abs(x) / max(CA - d, 1e-3)) ** CN + (abs(y) / max(CB - d, 1e-3)) ** CN
        if f < 1: lo = mid
        else: hi = mid
    return lo
for j, thd in enumerate((-38.0, 4.0, 42.0)):
    th = math.radians(thd); o_ = Vector((math.cos(th), math.sin(th), 0)); ln = (0.9, 1.0, 0.75)[j]
    def pt(r, z): return V(PX + o_.x * r, o_.y * r, z)
    ctrl = [pt(12, SOIL_TOP + 2), pt(36, SOIL_TOP + 14), pt(potr(105) - 1.5, POT_TOP + 3.0), pt(potr(98) + 3.2, POT_TOP - 7),
            pt(potr(70) + 3.2, POT_Z0 + 70), pt(potr(46) + 3.4, CTOP + 3.5)]
    last_r = potr(46) + 3.4
    for dd in (40, 30, 20, 11, 5, 1.5):
        rr = ray_r(th, dd)
        if rr > last_r + 5:
            ctrl.append(pt(rr, CZ0 + z_surf(dd) + 3.0)); last_r = rr
    ro = ray_r(th, -3.4)
    ctrl += [pt(ro, CZ0 + 34), pt(ro + 0.5, CZ0 + 18), pt(ro + 0.5, CZ0 + 2), pt(ro + 0.5, CZ0 - 14 * ln), pt(ro + 0.5, CZ0 - 38 * ln)]
    pts = add_stem(ctrl, 0.0012)
    ncp = len(pts)
    for fr in (0.20, 0.33, 0.45, 0.56, 0.66, 0.76, 0.86, 0.95):
        p = pts[int(fr * (ncp - 1))]; q = pts[min(int(fr * (ncp - 1)) + 3, ncp - 1)]
        along = (q - p)
        if along.length < 1e-6: along = Vector((o_.x, o_.y, -1))
        along.normalize()
        radial = Vector((p.x - PX * MM, p.y, 0)).normalized()
        side = 1 if int(fr * 100) % 2 else -1
        z_mm = p.z / MM
        if z_mm > CTOP + 6 and fr < 0.35:
            tip = Vector((o_.x, o_.y, 0.15)) + Vector((-o_.y, o_.x, 0)) * side * 0.7; nh = (0, 0, 1)
        elif z_mm > CZ0 + 30:
            tip = along * 0.6 + radial * 0.5 + Vector((-radial.y, radial.x, 0)) * side * 0.6; nh = radial * 0.5 + Vector((0, 0, 1))
        else:
            tip = Vector((0, 0, -1)) + radial * 0.25 + Vector((-radial.y, radial.x, 0)) * side * 0.45; nh = radial
        leaf_on(p + radial * 0.002, tip, nh, random.uniform(0.7, 1.0) * (0.9 if fr > 0.5 else 1.0), petiole=0.011)
for o in plant: o.parent = body

# ----------------------------------------------------------------------------------------
# Dock pad (separate printed part) with two spring contacts and a cable
# ----------------------------------------------------------------------------------------
PW, PD, PH = D["pad"]
def rr_pts(hx, hy, r, n=10):
    pts = []
    for cx, cy, a0 in [(hx - r, hy - r, 0), (-hx + r, hy - r, 90), (-hx + r, -hy + r, 180), (hx - r, -hy + r, 270)]:
        for k in range(n + 1):
            a = math.radians(a0 + 90 * k / n); pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts
pad = put("dock_pad", mesh_prism("m_pad", rr_pts(PW / 2, PD / 2, D["pad_r"]), 0, PH), MT["shell"], None, smooth_it=False)
active(pad); bm_ = pad.modifiers.new("bev", "BEVEL"); bm_.width = 3.5 * MM; bm_.segments = 3; bm_.limit_method = "ANGLE"; bm_.angle_limit = math.radians(35)
bpy.ops.object.modifier_apply(modifier=bm_.name); smooth(pad, 40)
dock_extras = []
plate = put("dock_plate", mesh_prism("m_plate", rr_pts(46, 70, 10, 6), PH - 0.2, PH + 1.6), MT["shell"], pad, smooth_it=False)
dock_extras.append(plate)
for s in (1, -1):
    y = s * D["contact_y"]
    base_ = put("contact_housing", mesh_cyl("m_cb", 6.2, 2.0, "z", 28), MT["contact_base"], pad, loc=(0, y, PH + 1.6 + 1.0))
    bm = bmesh.new()
    for k in range(4):
        add_cyl(bm, 3.6, 0.9, c=(0, 0, PH + 1.6 + 2.5 + k * 1.1), mat=0, n=16)
    spring = put("spring_coil", to_mesh("m_spring", bm), MT["brass"], pad)
    spring.location = (0, y * MM, 0)
    tip_ = put("contact_tip", mesh_cyl("m_ct", 2.6, 2.2, "z", 18), MT["brass"], pad, loc=(0, y, PH + 1.6 + 7.0))
    dock_extras += [base_, spring, tip_]
cab = [Vector(p) * MM for p in [(70, -144, 6.0), (70, -156, 4.8), (76, -176, 3.4), (98, -212, 3.3), (150, -285, 3.3), (260, -345, 3.3), (420, -385, 3.3)]]
dock_cable = tube_curve("dock_cable", cab, 0.0033, MT["cable"], res=3)
dock_extras.append(dock_cable)
for o in dock_extras: o.parent = pad

# ----------------------------------------------------------------------------------------
# Scene dressing, lights, worlds (render-only; not in the GLB)
# ----------------------------------------------------------------------------------------
def area(name, loc, target, energy, size, color=(1, 1, 1)):
    bpy.ops.object.light_add(type="AREA", location=loc)
    l = bpy.context.active_object; l.name = name; l.data.energy = energy; l.data.size = size; l.data.color = color
    d = Vector(target) - Vector(loc); l.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    return l

bpy.ops.object.camera_add()
cam = bpy.context.active_object; cam.name = "camera"; scene.camera = cam
cam.data.lens = 50; cam.data.sensor_width = 36; cam.data.clip_end = 80; cam.data.clip_start = 0.01
def aim(loc, target, cam_=None):
    c = cam_ or cam
    c.location = loc
    c.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
def look_basis(loc, target):
    f = (Vector(target) - Vector(loc)).normalized()
    r = f.cross(Vector((0, 0, 1))).normalized()
    u = r.cross(f).normalized()
    return f, r, u

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

def big_plane(name, size, mat):
    bpy.ops.mesh.primitive_plane_add(size=size, location=(0, 0, 0))
    o = bpy.context.active_object; o.name = name; assign(o, mat); return o

bpy.ops.mesh.primitive_plane_add(size=40, location=(0, 0, 0))
ground = bpy.context.active_object; ground.name = "ground_studio"
assign(ground, make_mat("Studio_floor", srgb("#8C8D90"), 0.85, 0.0, 0.0))
W_STUDIO = world(gradient=[(0.0, (0.55, 0.57, 0.60)), (0.5, (0.34, 0.36, 0.40)), (1.0, (0.20, 0.22, 0.26))], strength=0.9)
L_STUDIO = [area("studio_key", (0.9, 1.1, 1.4), (0, 0, 0.18), 230, 0.9, (1.0, 0.96, 0.90)),
            area("studio_fill", (1.2, -1.1, 0.6), (0, 0, 0.18), 70, 1.6, (0.88, 0.93, 1.0)),
            area("studio_rim", (-1.2, 0.2, 1.0), (0, 0, 0.18), 120, 0.8, (1, 1, 1))]

MAT = dict(
    patio=tile_material("Patio_stone", 0.42, srgb("#6C675F"), srgb("#58534C"), srgb("#262420"), 0.82, 0.45, 0.012, 0.5),
    pavers=tile_material("Wet_pavers", 0.32, srgb("#8A8A87"), srgb("#6E6F70"), srgb("#222322"), 0.55, 0.5, 0.018, 0.35),
    lawn=noise_material("Lawn", [(0.25, srgb("#17380F")), (0.75, srgb("#5E9630"))], 22, 8, 0.95, 160, 0.8, 0.9),
    stucco=noise_material("Stucco", [(0.35, srgb("#C4BDAD")), (0.7, srgb("#E0DACB"))], 8, 6, 0.92, 700, 0.12, 1.2),
    fence=fence_material("Fence_boards"),
    frame=make_mat("Window_frame", (0.004, 0.004, 0.004), 0.9, 0.0, 0.0),
)
ENV = {k: [] for k in ("hero", "detail", "night", "dock")}
fence_o = box("fence_hero", 0.08, 40.0, 1.9, x=0, y=0, z0=0); assign(fence_o, MAT["fence"])
for n_ in MAT["fence"].node_tree.nodes:
    if n_.bl_idname == "ShaderNodeTexBrick":
        n_.inputs["Color1"].default_value = (0.036, 0.021, 0.013, 1); n_.inputs["Color2"].default_value = (0.022, 0.012, 0.008, 1)
        n_.inputs["Mortar"].default_value = (0.004, 0.003, 0.002, 1)
HERO_AZ = math.radians(36)
fence_o.location = (-1.55 * math.cos(HERO_AZ), -1.55 * math.sin(HERO_AZ), 0); fence_o.rotation_euler = (0, 0, HERO_AZ)
ENV["hero"] += [big_plane("patio_hero", 200, MAT["patio"]), fence_o]
ENV["detail"] += [big_plane("patio_detail", 200, MAT["patio"])]
ENV["night"] += [big_plane("lawn_night", 80, MAT["lawn"])]
ENV["dock"] += [big_plane("pavers_dock", 30, MAT["pavers"])]
wallA = box("wall_dock_a", 0.12, 3.0, 2.2, x=-0.66, y=0.3, z0=0)      # behind the robot (-X), front face at x=-0.60
wallB = box("wall_dock_b", 3.0, 0.12, 2.2, x=0.3, y=0.66, z0=0)       # to its left (+Y), front face at y=0.60
assign(wallA, MAT["stucco"])
assign(wallB, noise_material("Stucco_shade", [(0.35, srgb("#B3AC9D")), (0.7, srgb("#CFC9BA"))], 8, 6, 0.92, 700, 0.12, 1.2))
ENV["dock"] += [wallA, wallB]
LIGHTS = {k: [] for k in ("hero", "detail", "night", "dock")}
WORLDS = {
    "hero": world(strength=0.55, gradient=[(0.0, (0.34, 0.20, 0.17)), (0.10, (0.16, 0.18, 0.34)), (0.55, (0.035, 0.06, 0.20))]),
    "detail": world(color=(0.55, 0.62, 0.72), strength=0.9),
    "night": world(color=(0.02, 0.03, 0.07), strength=0.12),
    "dock": world(color=(0.72, 0.75, 0.80), strength=0.55),
}
def set_visible(shot):
    for k, objs in ENV.items():
        for o in objs: o.hide_render = (k != shot)
    for k, ls in LIGHTS.items():
        for l in ls: l.hide_render = (k != shot)
    studio = shot == "assembly"
    ground.hide_render = not studio
    for l in L_STUDIO: l.hide_render = not studio
    pad.hide_render = shot != "dock"
    for o in dock_extras: o.hide_render = shot != "dock"
    scene.world = WORLDS.get(shot, W_STUDIO)

def setup_engine():
    scene.render.engine = "CYCLES"
    c = scene.cycles; c.samples = SAMPLES; c.use_denoising = True; c.use_adaptive_sampling = True; c.max_bounces = 8
    try:
        pr = bpy.context.preferences.addons["cycles"].preferences
        pr.compute_device_type = "METAL"; pr.get_devices()
        for d in pr.devices: d.use = True
        c.device = "GPU"
    except Exception as e:
        print("GPU setup failed, CPU:", e)

def do_render(path, res, exposure=0.0):
    scene.render.resolution_x, scene.render.resolution_y = int(res[0] * RSCALE), int(res[1] * RSCALE)
    scene.view_settings.exposure = exposure
    scene.render.filepath = path
    r = time.time(); bpy.ops.render.render(write_still=True)
    print("RENDER %s %.1fs" % (os.path.basename(path), time.time() - r), flush=True)

def place_robot(loc=(0, 0, 0), yaw=0.0):
    root.location = loc; root.rotation_euler = (0, 0, math.radians(yaw))

def leg_world(name, which):
    L = LEGS[name]; bpy.context.view_layer.update()
    if which == "knee": return L["tibE"].matrix_world.translation.copy()
    if which == "hip": return L["hipE"].matrix_world.translation.copy()
    if which == "tip": return L["tibE"].matrix_world @ Vector((100 * MM, 0, 0))

os.makedirs(CAD, exist_ok=True); os.makedirs(BLEND, exist_ok=True); os.makedirs(SHOTS, exist_ok=True)
t0 = time.time()
STAND_SUM = None
if DO_RENDER:
    setup_engine()
    cam.data.dof.use_dof = False
    sfx = SUFFIX

    # ===== assembly-hero: neutral studio, standing, true 3/4 front-left =====
    if "assembly" in ONLY:
        set_visible("assembly"); pose_robot("standing"); place_robot()
        cam.data.lens = 50
        az = math.radians(40); dist = 0.98
        aim((dist * math.cos(az), dist * math.sin(az), 0.52), (0.0, 0.0, 0.17))
        do_render(os.path.join(RENDER, "assembly-hero%s.png" % sfx), D["asm_res"], -0.6)

    # ===== optional orthographic checks against the HexArth drawing (only with --only top,front,side) =====
    for nm, cl, up_ in (("top", (0, 0, 3.0), (0, 1, 0)), ("front", (3.0, 0, 0.15), (0, 0, 1)), ("side", (0, -3.0, 0.15), (0, 0, 1))):
        if nm in ONLY:
            set_visible("assembly"); pose_robot("sitting" if "sit" in ONLY else "standing", ground=0.0); place_robot()
            cam.data.type = "ORTHO"; cam.data.ortho_scale = 0.62 if nm != "front" else 0.62
            cam.location = cl
            tgt_ = Vector((0, 0, 0.15 if nm != "top" else 0.0))
            cam.rotation_euler = (tgt_ - Vector(cl)).to_track_quat("-Z", "Y").to_euler()
            do_render(os.path.join(RENDER, "check-%s.png" % nm), (1000, 1000), -0.6)
            cam.data.type = "PERSP"
    # ===== hero-blender: low 3/4 front-left, ~25 cm camera height, patio + fence, porch lamp =====
    if "hero" in ONLY:
        set_visible("hero"); pose_robot("standing"); place_robot()
        az = HERO_AZ; dist = 0.92
        loc = Vector((dist * math.cos(az), dist * math.sin(az), 0.25))
        f, r, u = look_basis(loc, (0, 0, 0.14))
        tgt = Vector((0, 0, 0.16)) - r * 0.13
        cam.data.lens = 32
        aim(loc, tgt)
        f, r, u = look_basis(loc, tgt)
        base = Vector((0, 0, 0.14))
        LIGHTS["hero"] = [
            area("porch_lamp", base - r * 1.1 + u * 0.3 - f * 0.1 + Vector((0, 0, 1.0)), base, 210, 0.4, (1.0, 0.64, 0.34)),
            area("dusk_fill", base + r * 1.6 + Vector((0, 0, 0.6)) + f * 0.4, base, 150, 1.8, (0.50, 0.64, 1.0)),
            area("hero_rim", base - f * 1.2 + Vector((0, 0, 0.9)) + r * 0.3, base, 70, 0.8, (1.0, 0.78, 0.55)),
        ]
        set_visible("hero")
        do_render(os.path.join(SHOTS, "hero-blender%s.png" % sfx), D["shot_res"], -0.55)

    # ===== detail-blender: front-left leg + carapace edge + pot, f/2.8 on the leg =====
    if "detail" in ONLY:
        set_visible("detail"); pose_robot("standing"); place_robot()
        knee = leg_world("FL", "knee"); tip = leg_world("FL", "tip"); hip = leg_world("FL", "hip")
        tgt = Vector((knee.x * 0.62 + tip.x * 0.38 - 0.03, knee.y * 0.62 + tip.y * 0.38 - 0.035, 0.125))
        az = math.radians(31 + 75)
        loc = tgt + Vector((math.cos(az), math.sin(az), 0)) * 0.50 + Vector((0, 0, -0.045))
        cam.data.lens = 38
        aim(loc, tgt)
        cam.data.dof.use_dof = True; cam.data.dof.aperture_fstop = 2.8
        cam.data.dof.focus_distance = (knee * 0.6 + tip * 0.4 - loc).length
        f, r, u = look_basis(loc, tgt)
        LIGHTS["detail"] = [
            area("morning_key", tgt - r * 0.6 + u * 0.7 - f * 0.1 + Vector((0, 0, 0.4)), tgt, 130, 0.5, (1.0, 0.90, 0.75)),
            area("detail_fill", tgt + r * 0.9 + Vector((0.4, 0, 0.1)), tgt, 36, 1.0, (0.85, 0.92, 1.0)),
        ]
        set_visible("detail")
        do_render(os.path.join(SHOTS, "detail-blender%s.png" % sfx), D["shot_res"], 0.0)
        cam.data.dof.use_dof = False

    # ===== night-blender: mid-step from a second-floor window, lawn, long shadow =====
    if "night" in ONLY:
        set_visible("night"); pose_robot("midstep"); place_robot((0, 0, 0), 18)
        az = math.radians(58)
        loc = Vector((math.cos(az), math.sin(az), 0)) * 5.0 + Vector((0, 0, 3.5))
        f, r, u = look_basis(loc, (0, 0, 0.12))
        tgt = Vector((0, 0, 0.12)) - r * 0.30 + u * 0.10
        cam.data.lens = 85
        aim(loc, tgt)
        f, r, u = look_basis(loc, tgt)
        shadow_dir = (-(f * 0.55 + r * 0.85)); shadow_dir.z = 0; shadow_dir.normalize()
        el = math.radians(12)
        ldir = Vector((shadow_dir.x * math.cos(el), shadow_dir.y * math.cos(el), -math.sin(el)))
        lpos = Vector((0, 0, 0.15)) - ldir * 7.0
        bpy.ops.object.light_add(type="SPOT", location=lpos)
        sun = bpy.context.active_object; sun.name = "night_light"; sun.data.energy = 34000.0; sun.data.color = (1.0, 0.88, 0.62)
        sun.data.spot_size = math.radians(38); sun.data.spot_blend = 1.0; sun.data.shadow_soft_size = 0.05
        sun.rotation_euler = ldir.to_track_quat("-Z", "Y").to_euler()
        glow = area("house_glow", loc * 0.55 + Vector((0, 0, -0.5)), (0, 0, 0.1), 30, 1.6, (1.0, 0.82, 0.55))
        LIGHTS["night"] = [sun, glow]
        fr1 = box("window_frame_v", 0.22, 1.6, 0.05); assign(fr1, MAT["frame"])
        fr1.parent = cam; fr1.location = (-0.244, 0.0, -0.75); fr1.rotation_euler = (0, 0, math.radians(1.5))
        ENV["night"] += [fr1]
        set_visible("night")
        do_render(os.path.join(SHOTS, "night-blender%s.png" % sfx), D["shot_res"], -0.7)
        fr1.hide_render = True

    # ===== dock-blender: sitting on the pad in a two-wall garden corner, overcast =====
    if "dock" in ONLY:
        set_visible("dock")
        pad.location = (0, 0, 0)
        pose_robot("sitting", ground=D["pad"][2]); place_robot()
        az = math.radians(-42); dist = 1.0
        loc = Vector((dist * math.cos(az), dist * math.sin(az), 0.34))
        f, r, u = look_basis(loc, (0, 0, 0.12))
        tgt = Vector((-0.02, 0.0, 0.13))
        cam.data.lens = 34
        aim(loc, tgt)
        base = Vector((0, 0, 0.12))
        LIGHTS["dock"] = [area("overcast_sky", Vector((0.0, 0.0, 2.4)), base, 520, 3.8, (0.92, 0.95, 1.0)),
                          area("dock_soft_fill", base + Vector((1.0, -0.8, 0.5)), base, 60, 2.0, (0.95, 0.97, 1.0))]
        set_visible("dock")
        do_render(os.path.join(SHOTS, "dock-blender%s.png" % sfx), D["shot_res"], 0.0)
print("RENDERS done t=%.1fs" % (time.time() - t0), flush=True)

# ----------------------------------------------------------------------------------------
# Save blend (standing, studio) and export the viewer GLB (robot only, flat materials)
# ----------------------------------------------------------------------------------------
set_visible("assembly"); pose_robot("standing"); place_robot()
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(BLEND, "walking-planter.blend"))

def flat(name, rgb, rough=0.6):
    return make_mat(name, rgb, rough)
leaf_f = flat("viewer_leaf", srgb("#3F7F2A"), 0.5)
dark_f = flat("viewer_carbon", srgb("#101012"), 0.45)
dome_f = flat("viewer_dome", srgb("#DDE3E6"), 0.4)
soil_f = flat("viewer_soil", srgb("#2F2219"), 0.95)
LEAF_ME.materials.clear(); LEAF_ME.materials.append(leaf_f)
for L_name in LEGS:
    ob = bpy.data.objects[L_name + "_foot_tube"]; ob.data.materials.clear(); ob.data.materials.append(dark_f)
bpy.data.objects["sensor_dome"].data.materials.clear(); bpy.data.objects["sensor_dome"].data.materials.append(dome_f)
soil.data.materials.clear(); soil.data.materials.append(soil_f)
def descendants(o):
    out = [o]
    for c in o.children: out += descendants(c)
    return out
bpy.ops.object.select_all(action="DESELECT")
sel = descendants(root)
for o in sel: o.select_set(True)
bpy.context.view_layer.objects.active = root
glb = os.path.join(BLEND, "walking-planter.glb")
bpy.ops.export_scene.gltf(filepath=glb, export_format="GLB", use_selection=True, export_apply=True,
                          export_draco_mesh_compression_enable=False, export_yup=True)
print("GLB %.2f MB, %d objects" % (os.path.getsize(glb) / 1e6, len(sel)))
print("DONE total %.1fs" % (time.time() - t0))
