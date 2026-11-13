# Concept Lab

Give it a project idea; get back the project as if it were already built. A brief with real,
priced parts, a scaffold repo, a 3D model you can turn, photos of it where it would live, a
short video of it moving, and a page under **Concepts** on
[vyhouski.com/projects](https://vyhouski.com/projects).

It is for ideas Nick plans to build but has not yet: the page shows the plan in execution
before the build exists.

![Render on the left, photo on the right: the same robot in four shots](concepts/walking-planter/render/compare.png)

## Concepts

| Concept | Idea | Page | Code |
|---|---|---|---|
| Robot Planter | A plant pot on wheels that finds the sun and wanders the yard at night | [live](https://vyhouski.com/projects/robot-planter) | [weeeha/robot-planter](https://github.com/weeeha/robot-planter) |
| Walking Planter | The same idea on a Waveshare HexArth hexapod: sits all day, walks to follow the sun | [live](https://vyhouski.com/projects/walking-planter) | weeeha/walking-planter (private) |

Showcased with `showcase`: Photo Recreations (weeeha/photo-recreations, draft page).

## How a concept gets made

One command in Claude Code, with the idea in any shape (a voice dump, a product link, a
screenshot of a kit):

```
/concept-lab:concept a plant pot on six legs like the Waveshare HexArth
```

| Stage | What happens | Tool | Time, cost |
|---|---|---|---|
| 1. Brief | Pitch, how it works, diagram, real parts with prices, build plan, shot list. **Stops here for a go.** | Claude + a pricing agent | ~5 min |
| 2. Repo | Scaffold on `weeeha/<slug>`: real libraries and pins, the vendor's documented API, simulated once | Claude | ~10 min |
| 3. Model | Parametric Blender script, one camera per shot, viewer GLB | Blender headless, Sonnet agent | ~20 min |
| 4. Photos | Each shot's render made photographic, checked side by side against its render | Codex image (ChatGPT plan) | ~2 min, free |
| 5. Clip | 6 s image-to-video from the hero photo, checked frame by frame | Seedance 2.5 | ~5 min, ~$0.90 |
| 6. Page | Entry under Concepts, diagram, tests, PR, live check | Design Portfolio Site | ~15 min |

The rule that holds it together: **the Blender model is the only source of what the object
looks like.** Every photo starts as a render of it, the clip starts from a photo, and the 3D
viewer is its GLB. The first run generated photos from text and got four different robots.

The full pipeline, with every lesson from the first runs, is in
[`skills/concept/SKILL.md`](skills/concept/SKILL.md).

## Showcase: for prototypes that already exist

Quick creative builds pile up with open PRs, a template README and no screenshots, and quick
explorations end with no repo at all. One command takes a project from "works on my machine"
to a repo, a README, a findings doc and a page:

```
/concept-lab:showcase ~/ClaudeCode Projects/<project>
```

| Stage | What happens |
|---|---|
| 1. Audit | Repo or none, open PRs and their checks, unpushed work, bundled third-party material, how to run it, what is worth showing. Asks which code licence to add. **Stops here for a go.** |
| 2. Repo setup | Only when there is no repo: folder under `~/ClaudeCode Projects`, main starts with `.gitignore` alone, work on a branch, tracked files checked for private paths, names and credentials, private GitHub repo, PR |
| 3. Licences | Every bundled dataset, model, font, image, sound and copied file sorted by licence; what cannot be shared moves to an optional ignored file |
| 4. Merge | Approved PRs merged after green checks, confirmed on main |
| 5. Capture | Runs the app from main and takes real screenshots and a short screen clip in the Browser pane |
| 6. README | What it does, a screenshot at the top, commands that worked, sources and credits, an honest Status section |
| 7. Findings | `docs/FINDINGS.md`: what was explored and found, each decision with its why, what was dropped, what is open or unverified |
| 8. Hero (optional) | The real screenshot placed on a device in a setting, captioned as a mockup |
| 9. Page | A draft entry under "More from GitHub" on the site, with captures, a diagram and the clip |

Stages that do not apply are skipped. A new repo stays private until Nick says otherwise.

The difference from `concept`: the project exists, so every picture is a real capture of it
running. Details in [`skills/showcase/SKILL.md`](skills/showcase/SKILL.md).

## What is in this repo

| Path | What |
|---|---|
| `skills/concept/SKILL.md` | The pipeline Claude follows |
| `skills/showcase/SKILL.md` | The showcase pipeline; `scripts/private-check.sh` is its check before a first push |
| `hooks/` | Guards that run before every shell command in this repo (below) |
| `templates/` | Brief, parts, repo README and case-study skeletons |
| `concepts/<slug>/` | One folder per concept: brief, parts, `cad/` (Blender script, STLs), `blender/` (.blend, GLBs), `render/` (shot renders, photos, comparison sheet), `video/`, `log.md` |

### Hooks

`hooks/concept_guard.py` runs before every Bash command and acts only on Concept Lab work:

- **Blender first.** A `codex-image.sh` call without `-r <render>` is blocked, so a concept
  photo can't be generated from text alone.
- **Clean commits.** A `git add` or `git commit` that would stage another git repo (a sibling
  session's worktree once slipped in) or a file over 25 MB is blocked.

Each guard was tested against planted cases that must block and cases that must pass.

## Install

```bash
claude plugin marketplace add "$HOME/ClaudeCode Projects/Concept Lab"
```

```bash
claude plugin install concept-lab@concept-lab-marketplace
```

After changing the skill or hooks, bump `version` in `.claude-plugin/plugin.json`, then:

```bash
claude plugin marketplace update concept-lab-marketplace && claude plugin update concept-lab@concept-lab-marketplace
```

Restart Claude Code to load the new version.
