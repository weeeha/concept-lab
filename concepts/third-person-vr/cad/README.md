# Third Person VR: printable parts and 3D model

Everything here comes from one script, `build_third_person_vr.py`, run headless in Blender 5.1.
The parts are polygon meshes made with Blender booleans, not parametric solids (FreeCAD is not open, so there is no STEP file and no sketch history).
Dimensions sit in the `D` dict at the top of the script; change a number and rebuild. STLs are written in millimetres, the scene is in metres.
None of the parts has been printed or test-fitted. Fit allowances (lens hole, pole clip, pockets) are first guesses to check against the real parts.

## Parts

| File | What it is | Size (mm) | Notes |
|---|---|---|---|
| `camera-pod.stl` | Rounded housing for the ELP dual-lens stereo board | 86 x 40 x 44.5 (with boss) | Two 13 mm lens holes 60 mm apart, open back (board slides in), 4 mm walls, 19 mm boss underneath with a 6.4 mm bore for a 1/4"-20 heat-set insert, 10 mm deep |
| `camera-pod-lid.stl` | Back cover for the pod | 86 x 34 x 4 | 11 mm cable hole low on the lid. Fourth file, not in the original list: the pod needs a lid |
| `pi-battery-sled.stl` | Tray for a Raspberry Pi 5 with Active Cooler and a 20,000 mAh power bank, side by side | 164 x 164 x 12 | Pi pocket 60 x 90, power bank pocket 74 x 154, four 4 x 30 strap slots, 34 mm vent hole under the cooler, cable notches in the pocket walls. Prints flat, pockets up |
| `cable-clip.stl` | C-clip for the 25 mm pole with an eyelet for one USB cable | 33.8 x 39.7 x 10 | 25.8 mm bore (0.4 mm clearance per side), 19 mm snap opening, 5.6 mm eyelet. Print six |

Print notes (untested): PETG, 0.2 mm layers, 3 walls. Clip: lay it on its side so the C is not printed across layers. Pod: print open side up, the boss needs support or print it boss-down on a brim.

The mesh check in the script reports zero non-manifold edges for all four files.

## Other files in this folder

- `../blender/third-person-vr.blend`: the full scene (mannequin, rig, street set, lights, cameras).
- `../blender/model.glb`: the rig and mannequin for the web viewer, about 1.2 MB, metres, modifiers applied. Materials are flat colours (procedural bumps do not survive glTF).
- `../render/assembly-hero.png` and `../render/shots/*.png`: Cycles renders (Metal GPU, 128 samples, denoised).

## Rebuild

```
/Applications/Blender.app/Contents/MacOS/Blender -b -P "<path to this folder>/build_third_person_vr.py"
```

Options after `--`: `--samples 32 --scale 0.5` for quick previews, `--only hero,a,b,c` to render some shots (`hero` is the studio assembly, `a` the street hero, `b` the headset POV, `c` the pod detail), `--no-render` to rebuild only the STLs, blend and GLB, `--hide <object name>` to hide an object in the render.
A full run takes about one minute on an Apple Silicon Mac.
