# Robot Planter: printed parts (Concept)

> **Concept.** Planned design, nothing printed or built. Geometry is generated from
> `build_robot_planter.py`; fit against the real Dagu chassis, Pi and battery is unchecked.

Four printed parts, all PETG. Sizes are as exported (STL in millimetres, z = 0 on the bed).
Dimensions live in the `D = dict(...)` block at the top of the script.

| Part | STL | Size (mm, x y z) | What it does | Est. print (parts.md) |
|---|---|---|---|---|
| Shell ring + pot cradle | `shell-ring-cradle.stl` | 240 x 240 x 152 | 110 mm tall, 3 mm wall ring around the chassis, 6 mm deck, 40 mm tapered collar gripping a 150/110 x 130 mm pot (1.5 mm clearance). Four wheel arches, four 2.5 mm screw posts down to the chassis, 56 mm drain opening, cable hole and four screw holes for the mast, four rain slots in the deck. | ~9 h |
| Sensor mast + rain hood | `sensor-mast.stl` | 51 x 50 x 194 | 20 mm OD tube (2 mm wall), 180 mm tall, 50 mm hollow cone hood on top (hood adds 14 mm), 40 mm flange, HC-SR04 head with two 16 mm eyes facing forward, light-sensor window. Sits at the front of the deck. | ~2 h |
| Dock ramp | `dock-ramp.stl` | 120 x 220 x 39 | 220 mm wide, 120 mm long, 25 mm rise, side rails, backstop (the extra 14 mm), two contact holders 60 mm apart with 8 mm spring-pin bores and M3 clamp holes. | ~5 h |
| Battery tray | `battery-tray.stl` | 183 x 56 x 25 | Pocket for a 155 x 48 x 40 mm pack (+1 mm clearance each side), 3 mm walls 22 mm high, two 4 x 36 mm strap slots with underside channels, two finger scoops, two M3 ears. | ~2 h |

Total about 18 h of print time. Mesh check on the STLs: 0 non-manifold edges each (Blender bmesh).

## Known fit issues, read before printing

- **Shell is 240 mm across.** It does not fit a 220 mm bed. A 256 mm bed (Bambu class) takes it,
  otherwise split it in two halves. Print it deck-down (flipped) so the deck needs no bridging.
- **Chassis corners.** A 200 x 150 mm box has a 250 mm diagonal; inside a 234 mm ring it only fits
  because the stand-in chassis has 30 mm rounded corners. The real Dagu plate has square corners,
  so measure it, then raise `shell_od` or trim the plate.
- **Wheels** are placed at x = +/-70 mm, wheel width 26 mm, from the spec, not measured.
- Dock ramp is a solid wedge (about 410 cm3): use low infill. Contact positions are placeholders
  until the pot's rear contacts are designed.
- Battery sits on the tray at y = +40 mm, the Pi at y = -45 mm, both under the deck with about 3 mm
  to spare over the pack; the Pi and pack are stand-in boxes.

## Files

- `build_robot_planter.py`: builds the four parts, exports STLs, builds the assembly, saves the
  blend and GLB, renders both images.
- `../blender/robot-planter.blend`, `../blender/robot-planter.glb` (whole assembly, no Draco).
- `../render/assembly-hero.png`, `../render/parts-exploded.png` (1600 x 1200).

## Re-run

```
"/Applications/Blender.app/Contents/MacOS/Blender" -b -P build_robot_planter.py -- --engine cycles --samples 128
```

Options after `--`: `--engine cycles|eevee`, `--samples N`, `--no-render` (STL, blend, GLB only, about 4 s).
Tested on Blender 5.1.1, macOS; Cycles uses Metal if available, about 15 s per image at 128 samples.
No FreeCAD file: the parts are Blender meshes, not parametric solids (`.FCStd` not produced).
