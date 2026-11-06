# Robot Planter: concept case study

**Page:** `/projects/robot-planter`, status **Concept, not built**.
**Written:** 2026-11-06, drafted by Claude from `brief.md`. Nick hand-edits before it goes live.
**Assets:** `public/vibefolio/robot-planter/` (cover 4:3 from the hero still, detail, night, dock, assembly render, `model.glb`, `night.mp4` + poster, `diagram.svg`).
**Code:** https://github.com/weeeha/robot-planter (scaffold, untested; private until Nick flips it).

TL;DR: a concept for a plant pot on wheels that lives outside, sits still all day, and walks around at night when nobody is looking. It would find the sun, roll home to charge, and never be quite where you left it. This page shows the plan, the parts, the printed shell and what it would look like. Nothing here has been built yet.

---

## The idea

A pot that moves is funny for about three seconds, and then it is interesting. If it moves only
when you are not watching, the joke becomes a small mystery in the yard: the pot was by the
fence yesterday and it is by the steps today. I wanted that, and I wanted it to be an honest
machine underneath: a cheap chassis, a Raspberry Pi, a battery, three sensors, a printed shell,
and a rule list short enough to read on one screen.

## How it would work

Every ten minutes the Pi takes a reading: light, soil moisture, pack voltage, time. Then it
asks four rules in order and the first one that answers wins. Battery under 30 %: go home.
Moisture just jumped: it is raining, stay. Midday and dim here, but yesterday this hour was
brighter two metres over: go there. Quiet hours and a 30 % coin flip: wander inside the fence.
Otherwise sleep, which is what it does almost all day.

Moving is walking-cat speed on four small wheels, an ultrasonic sensor stops it at 25 cm, and a
dead-reckoned pose keeps it inside a square set in config. Home is a printed ramp with two
spring contacts and a blinking LED; the pot turns until the blink is strongest, backs on, and
sleeps until morning.

## What gets built

Bought: a $50 aluminium 4WD chassis with four 48:1 gearmotors, a Pi 5, a TB6612FNG motor HAT,
a 3S 5000 mAh pack with a balance charger, capacitive moisture, ambient light and HC-SR04
sensors, a 15 cm plastic pot. About $477 CAD at today's prices, parts list in the repo.

Printed in PETG: a shell ring with a pot cradle that hides the chassis and lets the wheels
peek out, a sensor mast with a rain hood, the dock ramp with contact holders, a battery tray.
About 18 hours of printing.

Written: `brain/` (scheduler, geofence, docking), `firmware/` (motors, sensors, power),
one config file, a main loop that logs every decision to `log.jsonl`.

## The printed parts

The shell is the whole look. It is a 240 mm ring that drops over the chassis and carries the
pot in a tapered cradle, so from a metre away it reads as a slightly tall white pot. The mast
grows out of the ring beside the pot and carries the light sensor under a small hood. The ramp
is the only part that lives apart from the robot.

## Seeing it

Hero still: concept render, generated. Night clip: concept, generated from the hero still.
Assembly viewer: the Blender model, drag to turn it.

## Build plan

| Phase | Work | Done when |
|---|---|---|
| 1 | Order parts. Print a test shell ring sized to the chassis footprint. | Parts on the desk, ring fits with 2 mm clearance |
| 2 | Pi drives the motors from a script, encoders count, ultrasonic stops it. | Rolls 2 m on the floor and stops at a shoe |
| 3 | Scheduler with rules and a geofence, runs for a day on the balcony with a log. | Log shows one sun move and one home move |
| 4 | Dock: ramp, contacts, beacon. Pot finds it from 1 m. | Three docks out of three, battery rising in the log |
| 5 | Full shell and mast, real pot and plant, two weeks outside. | Plant alive, pot inside the fence, a real video of a night wander |

## What I would learn

- Whether a $50 chassis moves 2 kg of pot and wet soil on grass. Pricing says probably not;
  tracks cost ten times more. The first prototype may be a patio-only pot.
- How far dead reckoning drifts over a night of wandering, and whether the dock seek covers it.
- Whether the pot being somewhere new each morning stays delightful or becomes a thing you
  trip over in the dark.

---

*Concept piece. Nothing here has been built or tested yet; the repo is a scaffold and every image is generated. When it gets built, this page is rewritten from what actually happened.*
