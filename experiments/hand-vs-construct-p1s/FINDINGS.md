# Construct: findings from two tests (2026-11-08)

**TL;DR.** Construct (github.com/rtmandreyev/construct, Apache-2.0, v1.2.1) is worth using as a
blockout and checker before the hand-built Blender model, not instead of it. Its check caught a
floating part in each test that the hand build missed. It cannot make photo-grade looks or cut holes.
Construct itself costs no tokens and runs offline; the cost is the agent writing the scene.

## What it is

An agent writes a scene (JSON: named parts from a fixed set of shapes, real sizes, joints, and how
each size is known). Construct checks it, then builds a hologram web page, a GLB with named parts and
an open animation, a Blender model (its add-on), STL/3MF print sizes, a model kit, and FreeCAD/STEP.
Python standard library only; network use is a local headless Chrome for review stills, and model
calls only when given `--base-url`.

- Clone: `~/ClaudeCode Projects/construct` (cloned 2026-11-08 at 24a1bc8).
- CLI: `python3 -I ~/ClaudeCode\ Projects/construct/skills/construct/scripts/cli.py check|build|review|export|print|kit ...`
- Blender add-on without installing it: build the zip (`scripts/build_blender_extension.py`), unzip as
  `construct_blender`, import it headless and call `import_construct()`; see
  `concepts/walking-planter/construct/make_blend.py`.

## Test 1: walking planter (Concept Lab)

Scene generated from the numbers in `concepts/walking-planter/cad/build_walking_planter.py`
(65 parts). Check found the OLED window and two buttons floating 20 mm in front of the body core,
a defect also present in the hand-built Blender script; fixed there too (core face is x = 50 mm).
It also showed the carapace cannot have its pot cradle cut (no booleans).

## Test 2: Bambu Lab P1S, hand vs Construct

Same brief (`BRIEF.md`), same facts, rendered from one camera (`side-by-side.png`).

| | Hand (bpy) | Construct |
|---|---|---|
| Tokens added to the session | 23.3k | 17.0k |
| Lines written | 157 | 110 (96 scene + 14 materials) |
| Wall time (machine clock) | about 3 min | about 2 min |
| Found before shipping | opaque glass, lid hinge sign (render); bed gap (manual probe) | floating gantry, missing source field (check) |
| Shipped with | floating gantry (rails 5 mm inside the posts) | bed 1 to 2 mm gap (under the check's tolerance) |
| Door and lid | lid hinge wrong on the first try | right on the first try |
| Extra outputs | .blend, GLB | hologram page, provenance view, print sizes, add-on .blend with Build/Open/Metal/Finish sliders |

Caveats: Construct was built second, from numbers already worked out; the tokens spent learning it
(about 30 to 40k) are not counted; token figures are context added, and each tool call also re-reads
the conversation.

## Where it fits

1. Write the Construct scene first: sizes, joints, check to zero, hologram page for the concept.
2. Build the parts that must look good by hand in Blender (glass, cut shells, plants) for the photos.
3. Use its print/kit outputs for desk models on the P1S (the "cube" printer class).
