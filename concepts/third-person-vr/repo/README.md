# Repo (stage 2)

- https://github.com/weeeha/third-person-vr, commit `f50bd98`, created 2026-11-06 **private**
  (flip with `gh repo edit weeeha/third-person-vr --visibility public --accept-visibility-change-consequences`).
- Local clone: `~/ClaudeCode Projects/third-person-vr`.

```
sender/capture.py        GStreamer: v4l2src MJPEG -> jpegdec -> scale -> x264enc zerolatency -> rtph264pay -> webrtcbin
sender/webrtc.py         send-only webrtcbin peer: offer, answer, ICE
sender/__main__.py       joins the signaling room, restarts the pipeline per headset join
signaling/server.py      aiohttp HTTPS: serves viewer/, relays SDP/ICE, /config.json
viewer/viewer.js         three.js WebXR: per-eye meshes on layers 1 and 2, curved screen, comfort dimming
viewer/lookaround.js     head yaw -> window offset, slow body-follower so real turns recentre
viewer/phone.html        path A sender: getUserMedia rear camera over WebRTC
config/rig.yaml          camera, encoder, network, viewer settings
docs/wiring.md           USB and power table
docs/latency.md          per-step targets (planned, not measured)
scripts/install.sh, systemd/   Pi setup and services
```

Python checked with `ast.parse`, YAML parsed, `lookaround.js` math run once in Node
(quick 30° glance pans, a held turn recentres). Nothing has run against hardware.
