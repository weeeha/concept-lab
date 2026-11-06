# Repo (stage 2)

- https://github.com/weeeha/robot-planter, commit `007cf78`, created 2026-11-06 **private**
  (auto mode refused to create a public repo; flip it with
  `gh repo edit weeeha/robot-planter --visibility public --accept-visibility-change-consequences`).
- Local clone: `~/ClaudeCode Projects/robot-planter`.
- README line 1: `> **Concept.** Planned build, code untested.`

```
main.py                 ten-minute loop, writes log.jsonl
brain/scheduler.py      rule list: battery → rain → sun → wander → sleep
brain/geofence.py       dead-reckoned pose, square fence, bearing math
brain/docking.py        beacon seek, reverse until charging
firmware/motors.py      TB6612FNG HAT over I2C, two channels per side, encoders
firmware/sensors.py     light (I2C), moisture + pack volts (ADS1115), HC-SR04
config/config.yaml      fence, quiet hours, thresholds, pins
docs/wiring.md          pin table from the real parts
docs/parts.md           priced parts
```

Python syntax-checked with `ast.parse`; nothing has been run against hardware.
