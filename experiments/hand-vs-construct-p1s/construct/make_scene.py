"""Bambu Lab P1S as a Construct scene (the 'construct' half of ../BRIEF.md). Writes p1s.scene.json.
Construct frame: metres, Y up, front +Z, viewer's right +X. Sizes in mm here, converted by m()."""
import json, os

HERE = os.path.dirname(os.path.abspath(__file__))
def m(v): return round(v / 1000, 5)

W, D, H = 389.0, 389.0, 458.0
BUILD, POST, BASE_Z, RIM, GLASS = 256.0, 22.0, 90.0, 22.0, 4.0
hx, hz = W / 2, D / 2
ph = H - RIM - BASE_Z

parts = []
def part(id, label, role, stage, shape, at, basis=("estimate",), **kw):
    p = dict(id=id, label=label, role=role, certainty=kw.pop("certainty", "inferred"), stage=stage,
             basis=list(basis), shape=shape, at=at); p.update(kw); parts.append(p)

def box(sx, sy, sz, anchor="base"): return {"type": "box", "size": [m(sx), m(sy), m(sz)], "anchor": anchor}

# base and feet
part("foot", "Foot", "structure", 0, {"type": "cylinder", "radius": m(16), "height": m(10), "segments": 24},
     [m(hx - 35), 0, m(hz - 35)], mirror="x", repeat={"count": 2, "step": {"at": [0, 0, m(-(D - 70))]}})
part("base", "Base (electronics, PSU)", "mass", 0, box(W, BASE_Z - 10, D), [0, m(10), 0], basis=["size.outer"],
     certainty={"size": "verified", "shape": "inferred"}, source="listing-dims")
part("screen", "Front screen", "identity", 1, {"type": "plane", "size": [m(62), m(34)]}, [m(-hx + 75), m(52), m(hz + 0.5)], look={"fill": "dark"})
part("button", "Button", "detail", 1, {"type": "cylinder", "radius": m(4.5), "height": m(3), "segments": 16},
     [m(-hx + 125), m(52), m(hz)], rotate=[90, 0, 0], repeat={"count": 5, "step": {"at": [m(13), 0, 0]}})

# frame
part("post", "Corner post", "mass", 1, box(POST, ph + RIM, POST), [m(hx - POST / 2), m(BASE_Z), m(hz - POST / 2)],
     basis=["size.outer"], mirror="x", repeat={"count": 2, "step": {"at": [0, 0, m(-(D - POST))]}})
part("rim-front", "Top rim, front", "structure", 2, box(W - 2 * POST, RIM, POST), [0, m(H - RIM), m(hz - POST / 2)], basis=["size.outer"])
part("rim-back", "Top rim, back", "structure", 2, box(W - 2 * POST, RIM, POST), [0, m(H - RIM), m(-hz + POST / 2)], basis=["size.outer"])
part("rim-side", "Top rim, side", "structure", 2, box(POST, RIM, D - 2 * POST), [m(hx - POST / 2), m(H - RIM), 0], basis=["size.outer"], mirror="x")
part("side-glass", "Side glass", "structure", 2, box(GLASS, ph, D - 2 * POST), [m(hx - POST / 2), m(BASE_Z), 0], look={"fill": "glass"}, mirror="x")
part("back-panel", "Back panel", "structure", 2, box(W - 2 * POST, ph, 3), [0, m(BASE_Z), m(-hz + 3)])

# door and lid
door_w, door_h = W - 2 * POST + 10, ph + 10
part("door-glass", "Front door glass", "identity", 3, box(door_w, door_h, GLASS), [m(-hx + POST - 5 + door_w / 2), m(BASE_Z - 5), m(hz + GLASS / 2 + 1)], look={"fill": "glass"})
part("door-handle", "Door handle", "detail", 3, box(10, 120, 14), [m(-hx + POST - 5 + door_w - 22), m(BASE_Z + ph / 2 - 60), m(hz + GLASS + 8)])
lid_w, lid_d = W - 2 * POST + 6, D - 2 * POST + 6
part("lid-glass", "Top lid glass", "identity", 3, box(lid_w, GLASS, lid_d), [0, m(H), 0], look={"fill": "glass"})

# bed on two Z screws at the back corners
bed_z = 260.0
part("z-screw", "Z lead screw", "structure", 2, {"type": "cylinder", "radius": m(4), "height": m(ph - 10), "segments": 12},
     [m(140), m(BASE_Z), m(-150)], mirror="x")
part("bed-frame", "Bed rear crossbar", "structure", 3, box(BUILD + 30, 14, 24), [0, m(bed_z - 14), m(-(BUILD / 2 + 10))])
part("bed-arm", "Bed arm", "structure", 3, box(20, 10, BUILD - 20), [m(120), m(bed_z - 12), m(-20)], mirror="x")
part("bed-plate", "Heated bed, 256 mm", "identity", 4, box(BUILD + 10, 6, BUILD + 10), [0, m(bed_z), m(8)], basis=["build.volume"],
     certainty={"size": "verified", "shape": "inferred"}, source="listing-build")

# CoreXY gantry
gz = H - RIM - 40
part("y-rail", "Y rail", "structure", 5, box(14, 14, D - 2 * POST), [m(hx - POST - 7), m(gz), 0], mirror="x")   # against the posts' inner faces
tx, tz = 40.0, 30.0
part("x-rail", "X rail", "structure", 6, box(W - 2 * POST - 24, 18, 16), [0, m(gz - 2), m(tz)])
part("toolhead", "Toolhead", "identity", 7, box(58, 72, 52), [m(tx), m(gz - 52), m(tz + 26)])
part("toolhead-fan", "Part-cooling fan", "detail", 7, box(40, 40, 4), [m(tx), m(gz - 40), m(tz + 54)])
part("nozzle", "Nozzle", "data", 7, {"type": "cone", "radius_bottom": m(0.6), "radius_top": m(3), "height": m(8), "segments": 12}, [m(tx), m(gz - 60), m(tz + 26)])

# spool and PTFE tube
sy = 300.0
part("spool-arm", "Spool holder arm", "structure", 3, {"type": "cylinder", "radius": m(8), "height": m(80), "segments": 16}, [m(60), m(sy), m(-hz)], rotate=[-90, 0, 0])
part("spool", "Filament spool", "identity", 4, {"type": "cylinder", "radius": m(100), "height": m(66), "segments": 48, "rings": 3}, [m(60), m(sy), m(-hz - 17)], rotate=[-90, 0, 0])
part("ptfe-tube", "PTFE tube", "detail", 5, {"type": "tube", "path": [[m(60), m(sy + 100), m(-hz - 50)], [m(60), m(sy + 190), m(-hz - 40)], [m(60), m(H + 2), m(-hz + 10)]], "radius": m(2), "sides": 8}, [0, 0, 0])

scene = {
    "format": "construct-scene", "version": 2, "id": "bambu-p1s", "title": "Bambu Lab P1S",
    "subject": {"category": "machine", "accuracy": "approximate", "synthetic": False,
                "summary": "An enclosed CoreXY 3D printer. Outer size and build volume from retailer listings; every other size estimated from general knowledge of the machine."},
    "units": "m", "seed": 3,
    "sources": [
        {"id": "request", "kind": "user_request", "title": "Shared brief (experiments/hand-vs-construct-p1s/BRIEF.md)", "rights": "user_private"},
        {"id": "listing-dims", "kind": "document", "title": "Cartridge World AU and MatterHackers P1S listings", "rights": "reference_only"},
        {"id": "listing-build", "kind": "document", "title": "Makerpoint and printer-hub.ru P1S listings", "rights": "reference_only"},
    ],
    "facts": [
        {"key": "size.outer", "value": "389 x 389 x 458 mm", "certainty": "verified", "source": "listing-dims"},
        {"key": "build.volume", "value": "256 x 256 x 256 mm", "certainty": "verified", "source": "listing-build"},
        {"key": "weight", "value": 12.95, "unit": "kg", "certainty": "verified", "source": "listing-dims"},
        {"key": "estimate", "value": "post, rim, base, bed and gantry sizes estimated", "certainty": "inferred", "source": "request"},
    ],
    "assets": [], "parts": parts,
    "articulations": [
        {"id": "door-open", "type": "hinge", "parts": ["door-glass", "door-handle"], "axis": [0, -1, 0], "pivot": [m(-hx + POST - 5), m(BASE_Z), m(hz + GLASS / 2 + 1)], "amount": 100, "order": 0},
        {"id": "lid-open", "type": "hinge", "parts": ["lid-glass"], "axis": [-1, 0, 0], "pivot": [0, m(H), m(-hz + POST - 3)], "amount": 60, "order": 1},
    ],
    "presentation": {"framing": {"yaw": 30, "pitch": 20}, "views": [{"id": "open", "label": "Door and lid open", "yaw": 35, "pitch": 25, "distance": 1.1}],
                     "atmosphere": {"haze": 0.7, "grid": True}, "still_pose": "closed"},
    "animation": {"assembly": {"style": "build", "seconds": 7.0, "interference": True}, "camera": {"drift": 6, "breathe": 0.03}},
    "authoring": {"tier": "standard", "research": "done", "sources": ["listing-dims", "listing-build"]},
}
json.dump(scene, open(os.path.join(HERE, "p1s.scene.json"), "w"), indent=1)
print(len(parts), "parts")
