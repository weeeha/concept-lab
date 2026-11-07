# log

- 2026-11-06 stage 1 brief: Claude (Fable) + one Sonnet parts agent (web search, 429s on 3 vendors). Cost: session tokens only.
- 2026-11-06 stage 2 repo: done in-session (subagent and public create both refused by auto mode); repo is private until Nick flips it. Cost: session tokens.
- Stage 4 stills: codex-image, 4 landscape images (hero, detail, night, dock), 1 take each, all picked, ChatGPT plan tokens ~35-62k each, no API cost.
- Stage 5 video: Seedance 2.5 I2V from hero.png, 10 s 720p no audio, ~1.52 USD est (216,900 tokens). Mid-clip jump at ~4.8 s; trimmed 4.7 s copy saved. Not regenerated.
- Stage 3 (3D): Blender 5.1.1 headless, cad/build_robot_planter.py. 4 STL, .blend, .glb, 2 Cycles renders (128 samples, ~15 s each). No FreeCAD (.FCStd skipped, MCP not open). Cost 0.
- 2026-11-06 stage 6 page: worktree `robot-planter-concept` in Design Portfolio Site, branch `vibefolio/robot-planter`. Entry in `candidatePages.ts` as a draft (homepage list test allows exactly 22 in projectPages); GitHub links left out until both repos are public and in the audit TSV. Diagram rendered from `docs/case-studies/robot-planter/diagrams.html` with headless Chrome. Tests 49/49.
- 2026-11-07 v2 visuals: Blender model redesigned (Sonnet agent, ~21 min), 4 shot cameras rendered, each turned photographic with codex-image -r (detail re-run once: mast drift). Seedance clip v2 from the new hero, 6 s, clean 0 to 3 s (~$0.91). Viewer GLB robot-only via cad/export_viewer_glb.py. Portfolio PR 128.
- 2026-11-07 mast removed: light sensor under a dome in the rim (Sonnet agent, same cameras), 4 photos redone (all clean first try), clip v3 clean 0 to 3 s (~$0.9). Portfolio PR 131.
