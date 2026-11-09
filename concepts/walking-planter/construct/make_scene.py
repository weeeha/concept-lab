"""Write walking-planter.scene.json (a Construct scene, construct-scene v2) from the same numbers
as ../cad/build_walking_planter.py, so the Blender model and the construct agree.

Run:  python3 make_scene.py   (standard library only)

Frames. The Blender script: millimetres, robot front +X, left +Y, up +Z.
Construct: metres, Y up, front +Z. Map (x_b, y_b, z_b) mm -> (y_b, z_b, x_b) / 1000, a proper rotation,
so robot-left is +X here and `mirror: "x"` makes the right side.
"""
import json, math, os

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "walking-planter.scene.json")

# ---- numbers copied from build_walking_planter.py (D dict), mm ----
D = dict(
    body_bottom=73.68, plate_top=154.88, plate_xy=(152.0, 136.4),
    hips=dict(F=(53.0, 48.0), M=(0.0, 78.1), R=(-53.0, 48.0)),
    leg_az=dict(F=31.0, M=90.0, R=149.0), hip_z=117.0, servo=(45.2, 24.7, 37.3),
    L1=98.0, L2=100.0, tip_r=10.6, reach_stand=127.0,
    car_a=100.0, car_b=85.0, car_n=2.6, car_z0=146.0, car_h=56.0, car_plateau_d=60.0,
    pot_top_d=120.0, pot_bot_d=95.0, pot_h=105.0, pot_sink=44.0, pot_x=-6.0,
    sensor_x=-83.0, sensor_d=22.0, contact_y=22.0,
)

def P(xb, yb, zb):
    """Blender mm -> Construct m."""
    return [round(yb / 1000, 5), round(zb / 1000, 5), round(xb / 1000, 5)]

def m(v):
    return round(v / 1000, 5)

def oct_profile(hx, hy, c):
    """Chamfered rectangle footprint in Construct's XZ (u = X = y_b, v = Z = x_b)."""
    pts = [(hx - c, hy), (hx, hy - c), (hx, -hy + c), (hx - c, -hy), (-hx + c, -hy), (-hx, -hy + c), (-hx, hy - c), (-hx + c, hy)]
    return [[m(y), m(x)] for (x, y) in pts]

# ---- leg IK, ported from solve_leg() for the standing pose ----
def leg_points(key):
    hx, hy = D["hips"][key]; az = math.radians(D["leg_az"][key]); hz = D["hip_z"]
    reach = D["reach_stand"]
    tx, ty, tz = hx + reach * math.cos(az), hy + reach * math.sin(az), D["tip_r"]
    R = math.hypot(tx - hx, ty - hy); H = tz - hz
    a, b = D["L1"], D["L2"]
    d = min(math.hypot(R, H), a + b - 0.5)
    x = (d * d + a * a - b * b) / (2 * d); h = math.sqrt(max(a * a - x * x, 0))
    dv = (R / math.hypot(R, H), H / math.hypot(R, H)); perp = (-dv[1], dv[0])
    K = (x * dv[0] + h * perp[0], x * dv[1] + h * perp[1])
    ux, uy = math.cos(az), math.sin(az)
    hip = (hx, hy, hz)
    knee = (hx + K[0] * ux, hy + K[0] * uy, hz + K[1])
    tip = (tx, ty, tz)
    return hip, knee, tip, az

parts = []
def part(**kw):
    kw.setdefault("certainty", "inferred")
    parts.append(kw)

# ===== HexArth body (bought; sizes from Waveshare's drawing) =====
bt = D["body_bottom"]
part(id="lower-plate", label="Lower plate", role="structure", stage=0, basis=["hexarth.body-bottom"],
     shape={"type": "extrude", "profile": oct_profile(70, 62, 20), "height": m(2.6), "axis": "y"}, at=[0, m(bt), 0])
part(id="body-core", label="Body core (ESP32 driver, 3s2p 18650 pack)", role="mass", stage=0, basis=["hexarth.body-bottom", "hexarth.cells"],
     shape={"type": "extrude", "profile": oct_profile(50, 42, 12), "height": m(126.0 - bt - 2.6), "axis": "y"}, at=[0, m(bt + 2.6), 0],
     look={"fill": "dark"})
part(id="deck", label="Deck plate", role="structure", stage=1, basis=["hexarth.body-bottom"],
     shape={"type": "extrude", "profile": oct_profile(70, 62, 20), "height": m(2.6), "axis": "y"}, at=[0, m(126.0), 0])
part(id="side-rail", label="Side rail", role="structure", stage=3, basis=["hexarth.body-bottom"],
     shape={"type": "box", "size": [m(3.0), m(40.0), m(96.0)]}, at=P(0, 49.0, 98.0), mirror="x")
part(id="standoff", label="Standoffs", role="detail", stage=1, basis=["hexarth.top-plate"],
     shape={"type": "cylinder", "radius": m(3.4), "height": m(23.8), "segments": 10},
     at=P(-50, 38, 128.6), repeat={"count": 3, "step": {"at": [0, 0, m(50)]}}, mirror="x")
part(id="pi-5", label="Raspberry Pi 5 (host)", role="identity", stage=2, basis=["brief.pi"],
     shape={"type": "box", "size": [m(56), m(16), m(86)], "anchor": "base"}, at=P(-4, 0, 137.0))
part(id="top-plate", label="Top plate", role="structure", stage=2, basis=["hexarth.top-plate", "hexarth.height"],
     certainty="verified", source="waveshare-drawing",
     shape={"type": "extrude", "profile": oct_profile(76, 68, 22), "height": m(D["plate_top"] - 152.4), "axis": "y"}, at=[0, m(152.4), 0])
part(id="oled-window", label="OLED window", role="detail", stage=1, basis=["hexarth.oled"],
     shape={"type": "plane", "size": [m(30), m(12)]}, at=P(50.1, 0, 100.0), look={"fill": "glass"})  # Blender script has 70.4: in front of the 50 mm core face, floating
part(id="belly-contact", label="Belly charge contact", role="data", stage=1, basis=["brief.dock"],
     shape={"type": "cylinder", "radius": m(5.5), "height": m(1.6), "segments": 20}, at=P(0, D["contact_y"], bt - 1.6), mirror="x")

# ===== legs: three on the left, mirrored =====
for key, name in (("F", "front"), ("M", "middle"), ("R", "rear")):
    hip, knee, tip, az = leg_points(key)
    ux, uy = math.cos(az), math.sin(az)
    yaw_c = round(math.degrees(math.atan2(uy, ux)), 2)  # direction in Construct XZ, for box rotation about Y
    # coxa servo: fixed to the body, inboard of the hip axis
    cx, cy = hip[0] - 23 * ux, hip[1] - 23 * uy
    part(id=f"coxa-servo-{name}", label=f"Coxa servo ({name})", role="structure", stage=2,
         basis=["hexarth.servo-size", "hexarth.hips"], mirror="x",
         shape={"type": "box", "size": [m(D["servo"][0]), m(D["servo"][2]), m(D["servo"][1])], "anchor": "center"},
         at=P(cx, cy, hip[2] - 2.5 - D["servo"][2] / 2), rotate=[0, round(90 - yaw_c + 90, 2), 0])
    part(id=f"hip-bracket-{name}", label=f"Hip bracket ({name})", role="structure", stage=3,
         basis=["hexarth.hips"], mirror="x",
         shape={"type": "box", "size": [m(27), m(36), m(22)]}, at=P(hip[0] + ux, hip[1] + uy, hip[2] - 2), rotate=[0, round(90 - yaw_c, 2), 0])
    # femur: servo + arm, hip to knee
    part(id=f"femur-{name}", label=f"Femur servo and arm ({name})", role="mass", stage=3,
         basis=["hexarth.L1", "hexarth.servo-size"], mirror="x",
         shape={"type": "tube", "path": [P(*hip), P(*knee)], "radius": m(17.0), "sides": 4, "caps": True})
    part(id=f"knee-{name}", label=f"Knee block ({name})", role="structure", stage=4,
         basis=["hexarth.L1"], mirror="x",
         shape={"type": "sphere", "radius": m(15.0), "lat": 4, "lon": 8}, at=P(*knee))
    # tibia: servo near the knee, then the carbon tube to the rubber tip
    kt = [knee[i] + (tip[i] - knee[i]) * 0.42 for i in range(3)]
    part(id=f"tibia-servo-{name}", label=f"Tibia servo ({name})", role="mass", stage=4,
         basis=["hexarth.L2", "hexarth.servo-size"], mirror="x",
         shape={"type": "tube", "path": [P(*knee), P(*kt)], "radius": m(16.0), "sides": 4, "caps": True})
    tip_top = (tip[0], tip[1], tip[2] + 4)
    part(id=f"foot-tube-{name}", label=f"Carbon foot tube ({name})", role="structure", stage=5,
         basis=["hexarth.L2", "hexarth.foot-tube"], mirror="x",
         shape={"type": "tube", "path": [P(*kt), P(*tip_top)], "radius": m(10.0), "sides": 10, "caps": True})
    part(id=f"foot-tip-{name}", label=f"Rubber foot tip ({name})", role="identity", stage=5,
         basis=["hexarth.foot-tube"], mirror="x",
         shape={"type": "sphere", "radius": m(D["tip_r"]), "lat": 6, "lon": 12}, at=P(*tip))

# ===== printed carapace (original design) =====
CA, CB, CN, CZ0, CH = D["car_a"], D["car_b"], D["car_n"], D["car_z0"], D["car_h"]
def car_top(frac_in):
    """Carapace top height (mm above its bottom) by how far in from the rim (0 rim .. 1 plateau)."""
    return CH * math.sin(min(max(frac_in, 0.0), 1.0) * math.pi / 2) ** 0.7
sections = []
N = 17
for i in range(N):
    t = -1 + 2 * i / (N - 1)                       # along x_b (front +), -1..1
    t = math.copysign(abs(t) ** 0.8, t)
    x = CA * t * 0.995
    hw = CB * (1 - abs(x / CA) ** CN) ** (1 / CN)
    inset = min(CA - abs(x), hw)                   # distance to the rim along this section's axis, roughly
    top = CZ0 + max(car_top(inset / 40.0), 6.0)
    sections.append([m(x), m(hw), m(CZ0), m(top)])
part(id="carapace", label="Printed carapace, PETG ribbed thin wall", role="mass", stage=6,
     basis=["req.carapace", "hexarth.top-plate", "req.payload"],
     shape={"type": "loft", "sections": sections, "round": 0.85})
part(id="carapace-skirt", label="Carapace skirt edge", role="identity", stage=6, basis=["req.carapace"],
     shape={"type": "curve", "closed": True, "smooth": True,
            "points": [[m(CB * math.copysign(abs(math.sin(a)) ** (2 / CN), math.sin(a))), m(CZ0),
                        m(CA * math.copysign(abs(math.cos(a)) ** (2 / CN), math.cos(a)))] for a in [2 * math.pi * k / 48 for k in range(48)]]})

# ===== pot, cradled in the carapace =====
POT_Z0 = CZ0 + CH - D["pot_sink"]
rb, rt, ph = D["pot_bot_d"] / 2, D["pot_top_d"] / 2, D["pot_h"]
part(id="grower-pot", label="12 cm thin grower pot", role="identity", stage=7, basis=["req.pot", "pot.size"],
     shape={"type": "lathe", "profile": [[0, 0], [m(rb), 0], [m(rt), m(ph)], [m(rt + 2.4), m(ph)], [m(rt + 2.4), m(ph - 13)], [m(rt - 1.6), m(ph - 13)], [0, m(ph - 13)]], "segments": 48, "meridians": 12},
     at=P(D["pot_x"], 0, POT_Z0))
part(id="soil", label="LECA and light mix", role="detail", stage=7, basis=["req.payload"],
     shape={"type": "cylinder", "radius": m(rt - 4), "height": m(2), "segments": 36}, at=P(D["pot_x"], 0, POT_Z0 + ph - 12))

# ===== pothos (decorative: no real plant was measured) =====
top_y = POT_Z0 + ph - 10
stems = [  # (azimuth deg, rise mm, out mm, droop)
    (10, 120, 40, False), (75, 105, 55, False), (140, 125, 35, False), (200, 110, 50, False), (265, 130, 30, False), (320, 100, 60, False),
    (40, 30, 95, True), (170, 25, 100, True), (290, 35, 90, True),
]
for i, (azd, rise, out, droop) in enumerate(stems):
    a = math.radians(azd); cx, cy = D["pot_x"] + 18 * math.cos(a), 18 * math.sin(a)
    if droop:
        pts = [(cx, cy, top_y), (cx + out * 0.6 * math.cos(a), cy + out * 0.6 * math.sin(a), top_y + rise),
               (cx + out * math.cos(a), cy + out * math.sin(a), top_y - 20), (cx + out * 1.05 * math.cos(a), cy + out * 1.05 * math.sin(a), top_y - 90)]
    else:
        pts = [(cx, cy, top_y), (cx + out * 0.4 * math.cos(a), cy + out * 0.4 * math.sin(a), top_y + rise * 0.6),
               (cx + out * math.cos(a), cy + out * math.sin(a), top_y + rise)]
    part(id=f"pothos-stem-{i}", label="Pothos stem", role="ornament", certainty="decorative", stage=7, basis=[],
         shape={"type": "tube", "path": [P(*p) for p in pts], "radius": m(1.6), "sides": 5})
    for j, p in enumerate(pts[1:]):
        part(id=f"pothos-leaf-{i}-{j}", label="Pothos leaf", role="ornament", certainty="decorative", stage=7, basis=[],
             shape={"type": "sphere", "radii": [m(22), m(5), m(28)], "lat": 4, "lon": 8},
             at=P(*p), rotate=[25, round(-azd + 90, 1), 0])

# ===== light sensor under a clear dome, behind the pot =====
sx = D["sensor_x"]
sx_hw = CB * (1 - abs(sx / CA) ** CN) ** (1 / CN)
sens_top = CZ0 + max(car_top(min(CA - abs(sx), sx_hw) / 40.0), 6.0)
part(id="light-sensor-dome", label="Light sensor under a clear dome", role="data", stage=7, basis=["req.no-mast", "sensor.size"],
     shape={"type": "sphere", "radius": m(D["sensor_d"] / 2), "lat": 6, "lon": 16, "anchor": "center"},
     at=P(sx, 0, sens_top - 4), look={"fill": "glass"})

# sizes read off Waveshare's drawing are verified; the simplified shapes are ours
SIZED = {"lower-plate", "deck", "side-rail", "standoff", "oled-window"} | {f"coxa-servo-{n}" for n in ("front", "middle", "rear")}
for p_ in parts:
    if p_["id"] in SIZED:
        p_["certainty"] = {"size": "verified", "shape": "inferred"}; p_["source"] = "waveshare-drawing"

scene = {
    "format": "construct-scene", "version": 2,
    "id": "walking-planter", "title": "Walking Planter",
    "subject": {"category": "machine", "accuracy": "original", "synthetic": False,
                "summary": "A bought Waveshare HexArth hexapod carrying a printed carapace and a 12 cm pothos pot: it walks a few slow steps to follow the sun and sits the rest of the day. Robot sizes from Waveshare's drawing; carapace, pot cradle and sensor dome are a new design; the plant is decoration."},
    "units": "m", "seed": 7,
    "sources": [
        {"id": "request", "kind": "user_request", "title": "Nick's walking-planter idea and brief (concepts/walking-planter/brief.md)", "rights": "user_private"},
        {"id": "waveshare-drawing", "kind": "drawing", "title": "Waveshare HexArth dimension drawing, as transcribed in cad/build_walking_planter.py", "rights": "reference_only", "ref": "docs.waveshare.com/HexArth"},
        {"id": "waveshare-page", "kind": "document", "title": "Waveshare HexArth product page", "rights": "reference_only", "ref": "https://www.waveshare.com/hexarth.htm"},
        {"id": "parts-list", "kind": "document", "title": "Walking planter parts list, checked 2026-11-07 (concepts/walking-planter/parts.md)", "rights": "user_private"},
    ],
    "facts": [
        {"key": "hexarth.height", "value": 0.15488, "unit": "m", "certainty": "verified", "source": "waveshare-drawing", "note": "standing height, top plate"},
        {"key": "hexarth.length", "value": 0.42859, "unit": "m", "certainty": "verified", "source": "waveshare-drawing", "note": "standing, foot to foot"},
        {"key": "hexarth.width", "value": 0.3443, "unit": "m", "certainty": "verified", "source": "waveshare-drawing"},
        {"key": "hexarth.body-bottom", "value": 0.07368, "unit": "m", "certainty": "verified", "source": "waveshare-drawing", "note": "body line above ground, standing"},
        {"key": "hexarth.top-plate", "value": "152.01 x 136.41 mm", "certainty": "verified", "source": "waveshare-drawing"},
        {"key": "hexarth.hips", "value": "(+-53, +-48) front and rear, (0, +-78) middle, mm", "certainty": "verified", "source": "waveshare-drawing"},
        {"key": "hexarth.servo-size", "value": "45.2 x 24.7 x 37.3 mm", "certainty": "verified", "source": "waveshare-drawing"},
        {"key": "hexarth.L1", "value": 0.098, "unit": "m", "certainty": "inferred", "source": "waveshare-drawing", "note": "femur axis length, read off the drawing"},
        {"key": "hexarth.L2", "value": 0.1, "unit": "m", "certainty": "inferred", "source": "waveshare-drawing", "note": "knee to tip-sphere centre, read off the drawing"},
        {"key": "hexarth.foot-tube", "value": "about 20 mm carbon tube, rubber tip", "certainty": "inferred", "source": "waveshare-drawing"},
        {"key": "hexarth.mass", "value": 2.1, "unit": "kg", "certainty": "verified", "source": "waveshare-page"},
        {"key": "hexarth.payload", "value": 1.0, "unit": "kg", "certainty": "verified", "source": "waveshare-page", "note": "dynamic"},
        {"key": "hexarth.cells", "value": "3s2p 18650, 10C or better (not included)", "certainty": "verified", "source": "waveshare-page"},
        {"key": "hexarth.oled", "value": "small OLED on the driver board", "certainty": "verified", "source": "waveshare-page"},
        {"key": "brief.pi", "value": "Raspberry Pi 5 on the top plate over the 40-pin UART", "certainty": "user_supplied", "source": "request"},
        {"key": "brief.dock", "value": "dock pad with two spring contacts under the belly", "certainty": "user_supplied", "source": "request"},
        {"key": "pot.size", "value": "12 cm thin grower pot", "certainty": "user_supplied", "source": "parts-list"},
        {"key": "sensor.size", "value": "DFRobot 0-200 klx ambient light sensor", "certainty": "user_supplied", "source": "parts-list"},
        {"key": "req.payload", "value": "carapace, Pi, sensors and planted pot together under 1 kg", "certainty": "user_supplied", "source": "request", "requirement": True},
        {"key": "req.carapace", "value": "a printed shell that bolts to the top plate, hides the Pi and cells and cradles the pot", "certainty": "user_supplied", "source": "request", "requirement": True},
        {"key": "req.pot", "value": "a light 12 cm plastic pot, not terracotta", "certainty": "user_supplied", "source": "request", "requirement": True},
        {"key": "req.no-mast", "value": "no sensor mast: the light sensor sits under a small clear dome behind the pot", "certainty": "user_supplied", "source": "request", "requirement": True},
    ],
    "assets": [],
    "parts": parts,
    "articulations": [
        {"id": "pot-lift", "type": "lift", "parts": ["grower-pot", "soil"] + [p["id"] for p in parts if p["id"].startswith("pothos-")],
         "axis": [0, 1, 0], "amount": 0.11, "order": 0},
    ],
    "annotations": [
        {"id": "a-carapace", "text": "Printed carapace (original design)", "part": "carapace", "offset": [0.09, 0.03, 0]},
        {"id": "a-pot", "text": "12 cm grower pot, under 1 kg payload", "part": "grower-pot", "offset": [0, 0.02, 0]},
        {"id": "a-sensor", "text": "Light sensor dome, no mast", "part": "light-sensor-dome", "offset": [0, 0.04, -0.03]},
        {"id": "a-legs", "text": "HexArth legs, 3 servos each", "part": "foot-tip-front", "offset": [0.03, 0.05, 0]},
        {"id": "a-plant", "text": "Pothos (decorative)", "part": "pothos-stem-4", "offset": [0, 0.02, 0]},
    ],
    "presentation": {
        "framing": {"yaw": 35, "pitch": 20},
        "views": [
            {"id": "open", "label": "Pot lifted from its cradle", "yaw": 30, "pitch": 28, "distance": 1.1},
            {"id": "leg", "label": "Front leg", "yaw": 50, "pitch": 6, "distance": 2.2, "target": "femur-front"},
        ],
        "atmosphere": {"haze": 0.7, "grid": True, "projector": False},
        "still_pose": "closed",
    },
    "animation": {
        "assembly": {"style": "build", "seconds": 7.0, "interference": True},
        "idle": {"life": "calm", "events": ["scan", "shimmer"], "cadence": [6, 12], "strength": 0.5},
        "camera": {"drift": 6, "breathe": 0.03},
    },
    "authoring": {"tier": "quick", "research": "not_needed"},  # numbers come from the Blender script, brief and parts list
}

with open(OUT, "w") as f:
    json.dump(scene, f, indent=1)
print(OUT, len(parts), "parts")
