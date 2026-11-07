# Third Person: concept case study

**Page:** `/projects/third-person-vr`, badge **Concept**.
**Written:** 2026-11-06, drafted by Claude from `concepts/third-person-vr/brief.md`. Nick hand-edits before it goes live.
**Assets:** `public/vibefolio/third-person-vr/` (hero, pov, detail, cover, assembly, render-to-photo, diagram, `model.glb`, hover clip).
**Code:** https://github.com/weeeha/third-person-vr (scaffold, untested, private for now).

TL;DR: A concept for a third-person view of yourself in real life. A stereo camera on a pole behind your head streams to a Quest 3 over a phone hotspot, so you walk your own street seeing yourself from behind, like in a game. Cheap parts, an old phone to start.

---

## The idea

I wanted the third-person experience from games, but walking around for real: a camera attached on a stick to my back, a metre behind and above my head, showing me in the headset as I walk.

## How it would work

Capture, encode, send, show, steer. A synced dual-lens camera grabs both eyes in one frame. A Pi 5 in the backpack encodes it in software (the Pi 5 has no hardware encoder), WebRTC carries it over a phone hotspot, and a WebXR page in the Quest 3 browser shows each half to its eye on a curved screen. Target: under 200 ms glass to eye.

![Architecture](/vibefolio/third-person-vr/diagram-loop.png)

## What gets built

Bought: ELP 960P synced stereo board, Raspberry Pi 5 with active cooler, 20,000 mAh USB-C power bank, Insta360 third-person backpack mount. Printed: camera pod, Pi and battery sled, cable clips. Written: GStreamer to WebRTC sender, signaling server, WebXR viewer with a look-around crop, phone sender page. Parts and prices: `third-person-vr/parts.md`.

## The printed parts

The pod holds the camera board with its lenses 60 mm apart and screws onto the pole tip through a 1/4" insert. The sled straps through the backpack mount and holds the Pi and battery, so the mount cannot twist. Six clips keep the cable on the pole.

## Seeing it

Hero on a Montreal sidewalk at dusk, the headset view from the pod, the pod close-up, the 3D model, and an 8 s clip of the view following the walker.

## Build plan

| Phase | Work | Done when |
|---|---|---|
| 1 | Phone path: one page with send and view modes | Walking a hallway slowly without bumping into anything |
| 2 | Stereo path: ELP camera, Pi 5, GStreamer, stereo split | Depth reads on stairs and kerbs; delay measured |
| 3 | Print pod and sled, route the cable | Rig on and off in under a minute, nothing rattles |
| 4 | Look-around crop, comfort settings | A 10-minute walk in a park without nausea |

## What I would learn

Whether 200 ms is walkable. Whether a fixed camera with a free head is fun or nauseating, and whether the look-around window helps. Whether a backpack mount holds the pole steady at walking pace.

---

*Concept piece. Nothing here has been built or tested yet; the repo is a scaffold. When it gets built, this page is rewritten from what actually happened.*
