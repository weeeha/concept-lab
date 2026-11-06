---
name: concept
description: Pretend it's built. Turn a raw project idea (voice dump is fine) into a concept piece for the vibefolio - brief, plausible untested repo on weeeha, FreeCAD/Blender 3D model, stills, Seedance video, and a /vibefolio case-study page. Use when Nick says "concept for X", "pretend it's done", "make a case study for the idea", "visualize this plan", "I need a case study now for something I'll build later", or dumps an idea and asks to see it as if finished.
---

# Concept

Nick has more ideas than build time. A concept piece shows one idea in execution before it is
built: it reads like a case study, looks like photos, moves like a video, and has a repo a
reader can open. It is scaffolding plus planning plus visualization. It is never a claim that
the thing shipped.

**Argument:** the idea, in whatever shape it arrives. If empty, ask for it in one line.

## Rules that never bend

1. **Say it once, where it counts.** The page's status reads "Concept, not built" and its
   first tag is "Concept"; the repo README ends with one status line. Nowhere else: no
   disclaimer in every docstring, caption, commit or file header. Captions describe the
   picture, not its provenance; one line in the page's closing note covers how the visuals
   were made. Nick asked for less of this after the first run.
2. **No invented facts about Nick.** No users, clients, metrics, launch dates, or "we tested".
   Specifications, parts and plans are fine; results are not. Where a number would usually go,
   write what is planned ("target: 4 h on one charge"), never what happened.
3. **One gate, after the brief.** Stage 1 ends with a numbered question. Nothing after it runs
   until Nick picks 1. After that, no more questions unless a tool fails.
4. **Real vendors, real parts.** A parts list names things that exist (RobotShop Canada, a
   specific Pi, a specific battery). Look them up; do not guess prices.
5. **Repo code reads real.** Structure, interfaces, a main loop, config, a README with a
   wiring table. No fake test suites, no fake CI badges, no claims that it ran.

## Where things go

| Piece | Path |
|---|---|
| Working folder | `concepts/<slug>/` in this repo, branch `concept/<slug>` |
| Code | GitHub `weeeha/<slug>` (public, personal account `weeeha`, commit email `1083934+weeeha@users.noreply.github.com`; the gmail address is rejected by GitHub's email-privacy rule) |
| Page | `/projects/<slug>` in `~/ClaudeCode Projects/Design Portfolio Site` (`/vibefolio` redirects there), on a branch, PR via `me:ship` |
| Page source | `docs/case-studies/<slug>-<date>.md` in the portfolio repo, assets in `public/vibefolio/<slug>/` |
| Page data | a short-page entry in `src/data/projectPages.ts` (read an existing entry first; `vibeCases.ts` is the legacy fallback, do not add there) |

Slug: lowercase, hyphens, two or three words (`robot-planter`).

## Pipeline

Run stages in order. Each stage appends one line to `concepts/<slug>/log.md`: what ran, tool,
cost, skipped-and-why. Order after the brief: stage 2 (repo, in the session) runs alongside
stage 3 (3D, a Sonnet subagent). Stages 4 and 5 wait for stage 3, because **the Blender model is
the single source of truth for what the object looks like**: every still is a Blender render
turned into a photo, and the clip starts from one of those stills. Then stage 6.

### Stage 1: Brief (gate)

Fill `templates/brief.md` into `concepts/<slug>/brief.md`. Keep Nick's own words where they
carry the idea (the robot pot "walking around occasionally, maybe at night when nobody is
looking" is the pitch). Contents:

- Pitch, three lines.
- How it works: the loop a reader can picture (sense, decide, move, charge).
- Architecture diagram in Mermaid, no more than 12 nodes.
- Parts list with vendor, part, approximate CAD price, link. Fill `templates/parts.md`.
- What gets 3D printed, what gets bought, what gets written.
- Build plan in phases, each with a done check.
- What the case study will show: which stills, which video shot, which diagram.

End with:

```
Brief at concepts/<slug>/brief.md. Next: repo, 3D, stills, video, page (about N min, video ~$1).
1. Go
2. Change the brief first (say what)
3. Brief only, stop here
```

Wait. Do not continue on silence.

### Stage 2: Repo

`gh repo create weeeha/<slug> --private --description "<pitch line>"` (auto mode
refuses to create a public repo, from a subagent or the session; Nick flips it with
`gh repo edit weeeha/<slug> --visibility public --accept-visibility-change-consequences`).
Do this stage in the session, not a subagent, for the same reason. Build from
`templates/repo-README.md` plus a plausible layout for the stack in the brief (a Pi robot gets
`firmware/`, `brain/`, `config/`, `docs/wiring.md`; a web idea gets the usual app skeleton).
Write the core modules so an engineer reading them nods: real library names, real pin
numbers from the parts list, a main loop, a config file. End the README with `## Status` and one line: `Planned build; the code has not run on
hardware yet. Plan and visuals: <page url>`. Commit as `initial scaffold`. Push `main` of that repo only, it is new and empty.
Record the URL in `concepts/<slug>/repo/README.md`.

### Stage 3: 3D

Two outputs, both into `concepts/<slug>/`. The Blender and FreeCAD apps are usually not open,
so drive Blender headless (`/Applications/Blender.app/Contents/MacOS/Blender -b -P
cad/build_<slug>.py`, one script with a dimensions dict at the top that builds parts, exports
STLs, assembles, saves the .blend and .glb and renders). Cycles on Metal does 1600x1200 at 128
samples in about 20 s. FreeCAD only when it is open; otherwise note "meshes, not parametric
solids" in `cad/README.md`.

- **Printable parts** with `parametric-3d-printing` and the FreeCAD MCP: the covers or
  enclosures from the brief, dimensioned around the real bought parts (chassis footprint,
  Pi board, battery). Save `.FCStd` and export STL into `cad/`.
- **Assembly render and GLB** with the Blender MCP: import the STLs, add simple stand-ins for
  bought parts (chassis as a box with wheels, the plant as a sphere on a cylinder), a neutral
  material, three-point light, one hero angle. Render PNG into `render/`, export `.glb` into
  `blender/` for the site's `ModelViewer`.

If a tool is not reachable, write the model description into `cad/README.md` and continue.

Design the model to look like the finished product, not a stand-in kit: one designed body,
the sensors where a reader expects them, real-looking plant or contents. It is what the
reader turns in the 3D viewer and what every photo shows. For each shot in the brief's shot
list, add a camera and a rough set (ground plane, a wall, key light direction) to the same
script and render `render/shots/<shot>-blender.png` at 1672x941.

### Stage 4: Stills (Blender render → photo)

Never generate a still from text alone: the first robot-planter run did, and the four stills
and the 3D viewer showed four different objects. For each `render/shots/<shot>-blender.png`:

```bash
bash ~/.claude/skills/codex-image/scripts/codex-image.sh -s landscape \
  -r render/shots/<shot>-blender.png -o render/raw/<shot>-v1.png \
  "Turn this 3D render into a real photograph. Keep the object's exact shape, proportions, \
parts, placement and the camera angle unchanged; change only materials, lighting and \
surroundings: <setting from the brief>. Photographic, <lens>, no text." 2> render/raw/<shot>.log
```

Bash `timeout: 300000`, about 40k plan tokens each, free on the ChatGPT plan. Then compare
each photo with its render side by side (`render/compare.png`, a 2-up per shot) and check the
object matches: body shape, sensor placement, mast and hood, wheel count. A drifted image is
re-run once with the drift named in the prompt ("the mast is at the rear right, not the
front"); a second drift means the render needs a clearer camera, not more prompts. Keep picks
in `render/`, prompts in `render/prompts.md`.

### Stage 5: Video

`seedance-prompt`, one clip, 8 to 10 s, from the hero still (I2V). The shot is the idea's
signature motion (the pot rolling across a dark yard, a sensor sweeping). Write the prompt to
`video/prompt.md`, the clip to `video/`. One generation; a second only if the first is unusable.
Log the cost. Client: `pipeline/seedance.py` in `~/ClaudeCode Projects/Video Generation
Pileline` (key falls back to `~/Documents/Claude/Projects/SeedDance/.env`; needs `requests`
in a venv). Seedance 2.5 I2V, 10 s 720p, about $1.50 at the 2.0 rate. Pull frames and look for
a seam; trim to the clean part rather than regenerate. The first frame is the stage-4 hero
photo, so the clip shows the same object as the model.

### Stage 6: Page

Fill `templates/case-study.md` into `concepts/<slug>/case-study.md`, then in the portfolio repo
take a worktree off `origin/main` (`.claude/worktrees/<slug>-concept`, branch
`vibefolio/<slug>`; the main checkout sits on an old branch) and:

1. Copy the case study to `docs/case-studies/<slug>-<date>.md`, the brief and parts to
   `docs/case-studies/<slug>/`, picked assets to `public/vibefolio/<slug>/` (stills as jpg q85,
   cover 4:3 crop of the hero, `model.glb`, `assembly.jpg` as its poster).
2. Diagram: write `docs/case-studies/<slug>/diagrams.html` in the house device (copy the head of
   `docs/case-studies/vr-museum/diagrams.html`: soft panel, white cards, one dark card, dashed
   card for the least certain part) and render it with a copy of its `render-diagrams.sh`
   (headless Chrome at 2x, crop the panel). 2400 px wide.
3. Data: the entry goes in **`src/data/conceptPages.ts`** (group `concepts`, shown under
   "Concepts" on /projects, never on the homepage), never `projectPages.ts` (homepage list
   pinned at 22) or `candidatePages.ts` (must stay drafts). Set `draft: true` until Nick says
   publish. A test enforces the labels below; it caught an unlabeled diagram caption once.
   `status: "Concept, not built"`, `tags` start with `"Concept"`; captions describe the picture
   or rendered, `currentState` carries the full disclosure. `model` replaces `loop` on the page,
   so the clip goes on the card: crop it to 4:3 and set `hoverVideo`. No GitHub `links` until the
   repos are public and listed in `docs/vibefolio-visual-audit-2026-11-01.tsv` (a test checks).
4. Append a row and a paragraph to `docs/vibefolio-evidence.md`.
5. `npm ci && npm test && npm run build`, then `next dev -p 31xx` and open
   `/projects/<slug>` and `/projects` in the Browser pane: model loads, diagram shows, no
   console errors. Stop the server.
6. Commit, push, `gh pr create`; the Vercel preview comes from the PR's checks or the bot
   comment (`nick-v-portfolio-git-<branch>-...vercel.app/projects/<slug>`). Add the row to this
   repo's README table, commit `concepts/<slug>/` on `concept/<slug>`, PR it here too, and log
   decisions with `bin/board decision design-portfolio-site ...`.

Nick publishes by flipping `draft` to false and, for the links, making the repos public and
adding them to the audit TSV. After merge, check vyhouski.com itself: the first production
build of PR 126 failed on a transient `next/font/google` fetch while its preview passed; one
`vercel redeploy` of the failed URL fixed it.

## Closing line

```
Concept <slug>: brief, repo <url>, 3D (<n> parts), <n> stills, <n> clip, page preview <url>.
Not in CV material. Hand-edit the case study before sharing.
```

## Done check

- [ ] Brief approved by a "1" before stages 2 to 6 ran
- [ ] Page status "Concept, not built" and first tag "Concept"; README status line; no disclaimer anywhere else
- [ ] No result claims anywhere (grep the case study for "users", "shipped", "launched", "tested")
- [ ] Parts list names real vendors and parts with prices checked
- [ ] Repo pushed and public; page PR open with a preview link
- [ ] `log.md` lists every stage with tool and cost
- [ ] README table in this repo has the row
