---
name: concept
description: Pretend it's built. Turn a raw project idea (voice dump is fine) into a concept piece on vyhouski.com - brief with real priced parts, a scaffold repo on weeeha, a Blender model, photos made from its renders, a Seedance clip, and a page under Concepts on /projects. Use when Nick says "concept for X", "pretend it's done", "make a case study for the idea", "visualize this plan", "create a page with a robot like this", "I need a case study now for something I'll build later", or dumps an idea and asks to see it as if finished.
---

# Concept

Nick has more ideas than build time. A concept piece shows one idea in execution before it is
built: it reads like a case study, looks like photos, moves like a video, has a model you can
turn, and has a repo a reader can open. Scaffolding plus planning plus visualization.

**Argument:** the idea, in whatever shape it arrives (voice dump, a product link, screenshots
of a robot kit). If empty, ask for it in one line. Mistyped words are normal: "6 digits" meant
six legs. Read the intent, say your reading in one line, and go.

Live examples: https://vyhouski.com/projects/robot-planter and
https://vyhouski.com/projects/walking-planter. Their folders in `concepts/` are the reference
for every stage.

## Rules that never bend

1. **The Blender model is the only source of what the object looks like.** Every photo is a
   render of it made photographic; the clip starts from one of those photos; the 3D viewer is
   its GLB. Never generate a still from text alone: the first run did and its four photos
   showed four different robots. The plugin's hook blocks `codex-image.sh` without `-r`.
2. **Say it once.** Page status "Concept, not built", first tag "Concept", one `## Status` line
   at the end of the repo README. No disclaimer in docstrings, file headers, captions, commit
   messages or repo descriptions. Captions describe the picture. Nick asked for this.
3. **No invented facts about Nick.** No users, clients, metrics, launch dates, "we tested".
   Plans and specs are fine; results are not. Never feeds the CV side (`me:apply`, nicks-bio).
4. **One gate, after the brief.** Stage 1 ends with a question; nothing after it runs until
   Nick says go. After that, no questions unless a tool fails or a merge needs him.
5. **Real parts, looked up.** Vendor pages fetched, not guessed; mark snippet-only prices.
   Read the kit's own docs (the HexArth docs gave payload, battery, servo and API facts that
   reshaped the brief).
6. **Every protrusion earns its place.** Nick rejected the robot planter's sensor mast as "a
   stick". Sensors sit flush or under a small dome unless the brief says why they cannot.

## Where things go

| Piece | Path |
|---|---|
| Working folder | `concepts/<slug>/` here, branch `concept/<slug>`, PR to `main` |
| Code | `weeeha/<slug>`, local `~/ClaudeCode Projects/<slug>`, commit email `1083934+weeeha@users.noreply.github.com` (GitHub rejects the gmail) |
| Page | `https://vyhouski.com/projects/<slug>`, under Concepts, never on the homepage |
| Page data | one entry in `src/data/conceptPages.ts` of `~/ClaudeCode Projects/Design Portfolio Site` |
| Page assets | `public/vibefolio/<slug>/`; sources in `docs/case-studies/<slug>/` |

Slug: lowercase, hyphens, two or three words.

## Pipeline

Each stage appends one line to `concepts/<slug>/log.md`: what ran, tool, cost, what was
skipped and why. After the gate: stages 2 and 3 run together (repo in the session, model in a
background Sonnet agent); 4 and 5 wait for 3; then 6. Say what runs in the background and
roughly how long, and end every reply that leaves something running with that line.

### Stage 1: Brief (gate)

`templates/brief.md` → `concepts/<slug>/brief.md`, `templates/parts.md` → `parts.md`. Keep
Nick's words where they carry the idea. Pitch, how it works (the loop a reader can picture),
a Mermaid diagram (≤12 nodes), bought / printed / written, build plan with done checks, the
shot list, open questions. Price parts with a background Sonnet agent while you write.
Constraints that bite go up front (the HexArth's 1 kg payload set the pot size).

End with the gate: what the brief says, the cost, what "go" produces, then ask go / change /
stop. Wait.

### Stage 2: Repo (in the session)

Write it yourself: a subagent cannot create the repo (auto mode). Plausible layout for the
stack, real library names, real pins from the parts list, a main loop, a config file, and only
API calls the vendor docs show (no invented command codes). End the README with `## Status`:
`Planned build; the code has not run on hardware yet. Plan and visuals: <page url>`.

Run it once in simulation (no hardware libraries present) and drive the move paths, not just
the idle one: the walking planter's first sim walk ended 1 m off target (heading not tracked
without an IMU, walk bursts overshooting) and both bugs were fixed before push.

`gh repo create weeeha/<slug> --private --source=. --push`; auto mode refuses public. Nick
flips it with `gh repo edit weeeha/<slug> --visibility public --accept-visibility-change-consequences`.

### Stage 3: Model and shot renders (background Sonnet agent)

Brief the agent with: the brief, real dimensions (from the vendor drawing; give it the
reference images by path), the look ("one designed product, not a kit with parts glued on"),
and the shot list. It writes `cad/build_<slug>.py`: one parametric script, a `D = dict(...)` of
millimetres at the top, poses as a parameter, run headless with
`/Applications/Blender.app/Contents/MacOS/Blender -b -P cad/build_<slug>.py -- [--only hero,...]`
(Cycles on Metal, 128 samples, about 2 to 3 minutes for everything). Reuse code from the two
existing scripts: the pothos, materials, sets and cameras in robot-planter, the HexArth legs,
IK poses and sensor dome in walking-planter.

Outputs: `render/shots/<shot>-blender.png` at 1672x941 for each shot (each with its own camera,
a rough set and a key-light direction), `render/assembly-hero.png`, the `.blend`, STLs for
printed parts, and the viewer GLB via `cad/export_viewer_glb.py`: the object only (no dock,
ground, cables), flat glTF materials (procedural ones export white), under 3 MB. Front faces
+X; the page's `view: [1, 0.3, -0.6]` then starts at the front-left.

Look at every render yourself (tile them into one image) before stage 4. A design change later
means re-rendering every shot with the same cameras; keep the old set in `render/shots/<tag>/`.

### Stage 4: Photos (render → photo)

All four at once, in parallel, Bash `timeout: 600000`:

```bash
bash ~/.claude/skills/codex-image/scripts/codex-image.sh -s landscape \
  -r render/shots/<shot>-blender.png -o render/raw/<shot>.png \
  "Turn this 3D render into a real photograph. Keep the object exactly as rendered: <name every \
part>, the same camera angle, framing and object position. Do not redesign, add or remove any \
part; there is no <pole/mast/antenna>. Change only materials, lighting, surface detail and \
surroundings: <setting>. No text." 2> render/raw/<shot>.log
```

Then a comparison sheet (render left, photo right, one row per shot) and look at it. If a photo
drifts, re-run that one once with the drift named ("the mast is a plain tube, no sensor head");
a second drift means the render needs a clearer camera. Picks go to `render/<shot>.png`.

### Stage 5: Clip

Seedance 2.5 image-to-video from the hero photo, 6 s, 720p, no audio, one generation:

```bash
cd "$HOME/ClaudeCode Projects/Video Generation Pileline" && <venv>/bin/python pipeline/seedance.py \
  generate --prompt-file <concept>/video/prompt.txt --name <slug>-hero \
  --first-frame <concept>/render/hero.png --duration 6 --resolution 720p --no-audio
```

The client needs `requests` (a venv in the scratchpad works); the key falls back to
`~/Documents/Claude/Projects/SeedDance/.env`. Runs in the background, about 5 minutes,
about $0.90. The prompt names every part again and says "one continuous shot, no cuts".

Pull frames at 0.2 s steps and look for a seam. All three rolling-planter clips jumped back to
the start pose at about 3.1 s; the walking clip had none. Use the clean part, crop to 4:3 for
the card (`ffmpeg -t <clean> -vf crop=960:720:<x>:0`), and write what you saw to
`video/prompt.md`.

### Stage 6: Page

In the portfolio repo, work in a worktree off `origin/main` (the main checkout sits on an old
branch). If a related PR is still open, stack on its branch and retarget to `main` before
merging.

1. Assets into `public/vibefolio/<slug>/`: photos as jpg q85, `cover-4x3.jpg` cropped from the
   hero around the object, `model.glb`, `assembly.jpg` as the viewer poster,
   `render-to-photo.jpg` (the comparison sheet), `hover-4x3.mp4`, `diagram-loop.png`.
2. Diagram: copy `docs/case-studies/walking-planter/diagrams.html` and its
   `render-diagrams.sh` (headless Chrome, 2400 px). Look at the result: a copied card title
   ("Back onto the ramp" on a walker) slipped through once.
3. Entry in `conceptPages.ts`: copy the walking-planter entry's shape. Status, first tag,
   captions that describe the picture, a "One model, every picture" decision with the
   comparison sheet, `related` to sibling concepts. `hoverVideo` carries the clip (the `model`
   takes the page slot). GitHub `links` only once the repo is public and listed in
   `docs/vibefolio-visual-audit-2026-11-01.tsv` (a test checks).
4. Copy brief and parts to `docs/case-studies/<slug>/`.
5. `npm ci` (first time), `npm test`, then `next dev -p 31xx` and open `/projects/<slug>` in the
   Browser pane: the viewer shows the object from the front, photos load, no console errors.
   If a test fails, check whether `main` fails it too before blaming your change (the homepage
   list test broke on `main` from another session's page).
6. Commit, push, `gh pr create`, wait for `gh pr checks --watch`. Merging deploys to
   vyhouski.com and auto mode blocks it: ask Nick, merge on his yes, confirm with
   `git merge-base --is-ancestor <head> origin/main`.
7. Verify live: poll until an asset's md5 matches the local file, then check every asset and
   grep the page HTML for leftovers. A production build once failed on a transient
   `next/font/google` fetch while the preview passed; `vercel redeploy <failed url>` fixed it.

Then here: add the row to the README's concept table, stage `concepts/<slug>/` by path (never
`git add -A` at the root; the hook blocks nested repos and files over 25 MB), PR, merge. Log
decisions with `"$HOME/ClaudeCode Projects/My Projects Dashboard/bin/board" decision design-portfolio-site ...`.

## Closing message

Page URL first, then what is on it, what was checked live, what is still open (Safari, private
repo, anything unmerged), and the cost of the run.

## Done check

- [ ] Gate passed before stages 2 to 6
- [ ] Every photo has a render beside it in the comparison sheet, same object in all
- [ ] Viewer GLB shows the object alone, from the front, with colors
- [ ] Clip checked frame by frame; only the clean part used
- [ ] Status and first tag say Concept; nowhere else does
- [ ] No result claims; parts and prices real, snippets marked
- [ ] Repo simulated on its move paths; README ends with the status line
- [ ] Page checked live by checksum, not just HTTP 200
- [ ] `log.md` has every stage with tool and cost; README table has the row
