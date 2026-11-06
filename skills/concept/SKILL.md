---
name: concept
description: Pretend it's built. Turn a raw project idea (voice dump is fine) into a labeled concept piece for the vibefolio - brief, plausible untested repo on weeeha, FreeCAD/Blender 3D model, stills, Seedance video, and a /vibefolio case-study page. Use when Nick says "concept for X", "pretend it's done", "make a case study for the idea", "visualize this plan", "I need a case study now for something I'll build later", or dumps an idea and asks to see it as if finished.
---

# Concept

Nick has more ideas than build time. A concept piece shows one idea in execution before it is
built: it reads like a case study, looks like photos, moves like a video, and has a repo a
reader can open. It is scaffolding plus planning plus visualization. It is never a claim that
the thing shipped.

**Argument:** the idea, in whatever shape it arrives. If empty, ask for it in one line.

## Rules that never bend

1. **Label everything "Concept".** README first line, case-study badge, image captions, video
   caption, commit messages. The reader must know within two seconds.
2. **No invented facts about Nick.** No users, clients, metrics, launch dates, or "we tested".
   Specifications, parts and plans are fine; results are not. Where a number would usually go,
   write what is planned ("target: 4 h on one charge"), never what happened.
3. **One gate, after the brief.** Stage 1 ends with a numbered question. Nothing after it runs
   until Nick picks 1. After that, no more questions unless a tool fails.
4. **Real vendors, real parts.** A parts list names things that exist (RobotShop Canada, a
   specific Pi, a specific battery). Look them up; do not guess prices.
5. **Repo code reads real and says it is untested.** Structure, interfaces, a main loop,
   config, a README with a wiring table. No fake test suites, no fake CI badges.

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
cost, skipped-and-why. Stages 2 to 5 are independent once the brief is approved: dispatch them
as subagents in parallel (Sonnet for 2 and 4, the session model for 3 and 5 since those drive
MCP tools), then run 6 when all four are back.

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

`gh repo create weeeha/<slug> --public --description "Concept: <pitch line>"`. Build from
`templates/repo-README.md` plus a plausible layout for the stack in the brief (a Pi robot gets
`firmware/`, `brain/`, `config/`, `docs/wiring.md`; a web idea gets the usual app skeleton).
Write the core modules so an engineer reading them nods: real library names, real pin
numbers from the parts list, a main loop, a config file. Mark the README: first line
`> **Concept.** Planned build, code untested. See the case study: <page url>`. Commit as
`concept: initial scaffold (untested)`. Push `main` of that repo only, it is new and empty.
Record the URL in `concepts/<slug>/repo/README.md`.

### Stage 3: 3D

Two outputs, both into `concepts/<slug>/`:

- **Printable parts** with `parametric-3d-printing` and the FreeCAD MCP: the covers or
  enclosures from the brief, dimensioned around the real bought parts (chassis footprint,
  Pi board, battery). Save `.FCStd` and export STL into `cad/`.
- **Assembly render and GLB** with the Blender MCP: import the STLs, add simple stand-ins for
  bought parts (chassis as a box with wheels, the plant as a sphere on a cylinder), a neutral
  material, three-point light, one hero angle. Render PNG into `render/`, export `.glb` into
  `blender/` for the site's `ModelViewer`.

If a tool is not reachable, write the model description into `cad/README.md` and continue.

### Stage 4: Stills

`codex-image`, three to four images, prompts in `render/prompts.md`. Shot list: hero in the
place it would live (Nick's balcony, a Montreal sidewalk at night, a yard), a detail of the
printed part, one "caught in the act" shot. Match the brief's materials and the Blender hero
angle so the stills and the render agree. Keep picks in `render/`, raw in `render/raw/`.

### Stage 5: Video

`seedance-prompt`, one clip, 8 to 10 s, from the hero still (I2V). The shot is the idea's
signature motion (the pot rolling across a dark yard, a sensor sweeping). Write the prompt to
`video/prompt.md`, the clip to `video/`. One generation; a second only if the first is unusable.
Log the cost.

### Stage 6: Page

Fill `templates/case-study.md` into `concepts/<slug>/case-study.md`, then in the portfolio repo
(branch `vibefolio/<slug>`): copy it to `docs/case-studies/<slug>-<date>.md`, copy picked
assets to `public/vibefolio/<slug>/`, add the `projectPages.ts` entry with `concept: true` (or
the badge field the existing vibefolio entries use; read one first). Run `me:ship` for the PR
and preview. Add the row to this repo's README table and commit `concepts/<slug>/` on
`concept/<slug>`, then PR it here too.

## Closing line

```
Concept <slug>: brief, repo <url>, 3D (<n> parts), <n> stills, <n> clip, page preview <url>.
Labeled Concept everywhere. Not in CV material. Hand-edit the case study before sharing.
```

## Done check

- [ ] Brief approved by a "1" before stages 2 to 6 ran
- [ ] "Concept" visible in README line 1, page badge, video caption
- [ ] No result claims anywhere (grep the case study for "users", "shipped", "launched", "tested")
- [ ] Parts list names real vendors and parts with prices checked
- [ ] Repo pushed and public; page PR open with a preview link
- [ ] `log.md` lists every stage with tool and cost
- [ ] README table in this repo has the row
