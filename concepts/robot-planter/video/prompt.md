# Video (Concept: robot-planter)

- Mode: I2V, first frame = render/hero.png
- Model: Seedance 2.5 (dreamina-seedance-2-5-260628) via Video Generation Pileline/pipeline/seedance.py
- Settings: 10 s, 720p, ratio adaptive (1280x720 out), no audio, no watermark
- Task: cgt-20261107051849-duh0c, one generation only
- Billed: 216,900 completion tokens. Ledger USD column is blank (2.5 not in pricing.json); at the 2.0 list rate of 7.0 USD/M that is about 1.52 USD (estimate).
- Files: robot-planter-night.mp4 (full 10 s), robot-planter-night-trim4.7s.mp4 (clean part only)

## Prompt
Starting from the first frame, a plant pot in a smooth matte white shell on a low wheeled robot base, with a slim sensor mast and tiny rain hood beside the pot, rolls slowly and steadily from left to right across wet patio stones in a Montreal backyard at dusk. One warm porch light glows on the brick wall behind. Static locked-off camera, 35 mm, shallow depth of field, calm and quiet, no people, no faces. The pot glides smoothly at walking-cat speed, leaves of the pothos plant swaying gently, then slows, stops, and settles with a tiny rock on its suspension. A beat later the small LED on the mast blinks once, a soft single pulse of light, and the shot holds still. Natural photographic color, warm porch light against cool blue dusk.

## Review of the result
- Pot rolls left to right across the patio, background stable, no people, mast and shell consistent.
- Defect: at about 4.8 s the pot jumps back to the left of frame and slightly larger, then rolls right again (no hard cut detected, but a visible discontinuity). The 0 to 4.7 s part is clean.
- The stop/settle and the single LED blink are not clearly visible. Not regenerated (one-generation rule); a second run is allowed if the jump is judged unusable.
