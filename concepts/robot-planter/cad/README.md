# Robot Planter: printed parts (Concept)

> **Concept.** Planned design, nothing printed or built. Geometry is generated from
> `build_robot_planter.py`; fit against the real Dagu chassis, Pi and battery is unchecked.

Four printed parts, all PETG. Sizes are as exported (STL in millimetres, z = 0 on the bed).
Dimensions live in the `D = dict(...)` block at the top of the script. Front of the robot (the sensor
eyes) faces +X in Blender; in the GLB it also faces +X (glTF is Y-up, so Blender +Y becomes glTF -Z).

| Part | STL | Size (mm, x y z) | What it does | Est. print (parts.md) |
|---|---|---|---|---|
| Shell (one body) | `shell-ring-cradle.stl` (name kept so links do not break) | 248 x 248 x 105 | Low tapered tub, 250 mm at the skirt, 225 mm at the flat top rim, 105 mm tall, soft fillets top and bottom, 3.5 mm walls, 12 mm lid. A 60 mm deep tapered pocket holds the 15 cm pot (1.5 mm clearance) so about 70 mm of the pot shows. Four small wheel arches, 10 mm ground gap, drain hole, shallow rounded recess in the front face for the two 16 mm ultrasonic transducers (26 mm apart), mast cable hole and four screw holes. | ~9 h |
| Sensor mast + hood | `sensor-mast.stl` | 53 x 50 x 202 | 16 mm OD tube, 28 mm flange, 200 mm tall above the rim, centre rod up through the dark light-sensor head (bought, ribbed) into a curved hood, 50 mm wide, bent forward. No cone. | ~2 h |
| Dock ramp | `dock-ramp.stl` | 120 x 230 x 90 | 25 mm rise wedge, rounded backrest 90 mm tall, two side wings, two 8 mm bores for the spring-contact posts, LED seat on top, cable exit. | ~5 h |
| Battery tray | `battery-tray.stl` | 183 x 56 x 25 | Pocket for a 155 x 48 x 40 mm pack (+1 mm clearance each side), 3 mm walls 22 mm high, two strap slots with underside channels, two finger scoops, two M3 ears. | ~2 h |

Not printed, modelled for the renders: terracotta pot, procedural pothos (heart-shaped leaf meshes on curved stems,
some trailing over the rim), two spring-contact posts with brass coils, dome LED, dock cable, chassis, Pi and battery stand-ins.

## Known fit issues, read before printing

- **Shell is 250 mm across at the skirt** (248 mm as exported with the bottom fillet). A 256 mm bed (Bambu class) takes it
  only just; otherwise split it. Print it rim-down (flipped) so the open skirt side is not bridged.
- **Pot pocket versus the stand-ins.** The pot sits 60 mm into the shell, so its bottom (z = 55 mm) is below the top of the
  battery (z = 79 mm) and the Pi. The stand-ins overlap the pocket tube in the model; the real pack (155 x 48 x 40 mm) does not
  fit under a 60 mm pot sink. Needs a flatter pack, a shallower sink, or the pack moved beside the pocket (the annulus is too narrow
  for the 155 mm length). Fit against the real chassis is unchecked.
- **Wheels** were moved inward to x = +/-48 mm, y = +/-80 mm (was 70 / 86.5) so they sit inside the new tub and show only
  through the small arches and the 10 mm skirt gap. Measure the real Dagu wheelbase before trusting this.
- Dock ramp is a solid wedge: use low infill. The contact posts, LED and cable are stand-ins; the robot has no rear contacts yet.

## Files

- `build_robot_planter.py`: builds the four parts, exports STLs, builds the assembly, saves the blend and GLB, renders the
  assembly, exploded view and four photo-shot scenes.
- `../blender/robot-planter.blend`, `../blender/robot-planter.glb` (robot and ramp, no Draco; procedural leaf and transducer
  materials fall back to flat colours in the GLB).
- `../render/assembly-hero.png`, `../render/parts-exploded.png` (1600 x 1200).
- `../render/shots/hero-blender.png`, `detail-blender.png`, `night-blender.png`, `dock-blender.png` (1672 x 941): Blender
  renders that the image model turns into photographs.

## Re-run

```
"/Applications/Blender.app/Contents/MacOS/Blender" -b -P build_robot_planter.py -- --engine cycles --samples 128
```

Options after `--`: `--engine cycles|eevee`, `--samples N`, `--no-render` (STL, blend, GLB only, about 4 s),
`--only assembly,exploded,hero,detail,night,dock` (render a subset).
Tested on Blender 5.1.1, macOS; Cycles uses Metal if available, 10 to 25 s per image at 128 samples (all six about 2 to 4 min).
No FreeCAD file: the parts are Blender meshes, not parametric solids (`.FCStd` not produced).
