# concepts/

One folder per concept, named by slug. The pipeline creates:

```
<slug>/
  brief.md            stage 1, Nick approves this before anything else runs
  parts.md            bill of materials with real vendors and rough CAD prices
  repo/               notes on what went to weeeha/<slug> (the code lives there, not here)
  cad/                FreeCAD sources (.FCStd) and exported STL for printable parts
  blender/            assembly .blend, exported .glb for the site's ModelViewer
  render/             picked stills (raw generations are gitignored)
  video/              picked clip + the Seedance prompt that made it
  case-study.md       the vibefolio page source, copied into the portfolio repo by stage 6
  log.md              what ran, what it cost, what was skipped
```
