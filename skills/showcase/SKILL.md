---
name: showcase
description: Turn a quick creative project, prototype or exploration that already exists into a finished-looking showcase - set up its repo if it has none, check the licences of bundled third-party material, merge its open PRs, run it and capture real screenshots, write a README and a findings and decisions doc, then build its page on vyhouski.com/projects with real captures, a how-it-works diagram, a short screen clip and a hero shot. Use when Nick says "showcase this", "wrap up this prototype", "wrap up this exploration", "make a repo and README for this", "write up findings and decisions", "make this project presentable", "merge the PRs and add a readme with screenshots", "put this on my site", "make a page for this project", or finishes a quick creative build and wants it shown. For ideas that are not built yet, use concept-lab:concept instead.
---

# Showcase

Nick builds quick creative prototypes faster than he presents them: PRs sit open, the README
is the template's, there are no screenshots, and the project is invisible on his site. This
skill takes one existing project from "works on my machine" to a page a client can open, and
wraps up a quick exploration end to end: a repo, a README, a findings doc, clean licences.

It is the sibling of `concept-lab:concept`. The difference is evidence: **the thing exists,
so every picture is a real capture of it running.** Generated imagery is allowed only as a
clearly separate hero shot made from a real capture (rule 3).

**Argument:** a project path, a repo name, or nothing (use the current folder). Say the target
in the first line: repo, local path, GitHub account, and whether it has a live URL. When there
is no repo yet, say that instead, with the name and folder stage 2 will create.

Every stage is skippable when it does not apply (a repo that exists skips stage 2, a project
with nothing bundled skips stage 3, an exploration with no page skips stages 8 and 9). The log
line for a skipped stage says why.

## Rules that never bend

1. **Client repos are off limits.** Ten8, PermitNav, KnockPro and Pegbo repos are read-only
   (see `~/.claude/CLAUDE.md`). If the target is one, stop and say so.
2. **Nothing invented.** Every claim on the README and the page traces to the code, the running
   app or Nick. What is stubbed, sample data or unverified is said once, in `currentState` and
   the README's Status section. No users, metrics or clients.
3. **Sensitive subjects stay out of generated images.** When a project depicts real events
   with victims or identifiable private people, generated or photoreal versions of those never
   go on the page; pick neutral examples and say in the evidence row how they were chosen.
   (Photo Recreations: American Gothic, a 1942 portrait of a real woman, was left out.)
4. **Captures are real.** Screenshots and clips come from the app running (locally or its live
   URL). A hero "in context" image (the app on a laptop on a desk, the game on a phone) may be
   made with `codex-image -r <real screenshot>`, and its caption says it is a mockup of the real
   screen. No generated interface.
5. **One gate, after the audit.** Stage 1 ends with what will be created, merged, captured and
   published, and asks go. Merges that deploy and the portfolio merge each need Nick's yes
   (auto mode blocks them anyway); ask once per list, not per PR. The code licence is asked at
   the same gate, once.
6. **Branch per change, never push to main.** README and findings work on `docs/showcase`,
   portfolio work in a worktree off `origin/main`. The one exception is a new repo's first
   commit, which holds only `.gitignore` (stage 2).
7. **Private until Nick says public.** A new repo is created private. It goes public only on
   Nick's word, after its PR is merged, the contents are checked and stage 3 has passed. A
   "just make it public" said before those checks is not that word: finish them, then ask.
8. **Other people's material keeps its licence.** Nothing non-commercial, no-derivatives or of
   unknown licence is tracked in a repo that will be public (stage 3).

## Pipeline

Each stage logs one line to `docs/showcase-log.md` in the project (what ran, what it found).
Long runs (dev server boot, clip generation) get a progress line: what runs, what it waits on,
about how long.

### Stage 1: Audit (gate)

- Repo: remote, account (`weeeha` or other), default branch, live URL if any (README, Vercel
  project, `vercel ls`). Visibility. No git repo, or no GitHub remote: stage 2 runs, and the
  gate names the repo and folder it will create.
- Third-party material: anything in the tree that Nick did not make (datasets, models, fonts,
  images, audio, copied code). Look up each licence now (stage 3, steps 1 and 2) so the gate
  can say what will stay and what will leave the tracked tree.
- Open work: `gh pr list --state open` with checks and mergeability; local branches ahead of
  main and uncommitted trees (`me:stranded --fetch` from inside the repo). A PR with red checks
  or a red-phase test is reported, not merged (the `me:stranded` rescue rules apply).
- How to run it: `package.json` scripts, `.claude/launch.json`, a Makefile, the `run` skill.
  Look in `tools/` for a capture script first: Photo Recreations had `tools/shot.mjs` (waits for
  the scene to be ready, WebKit renders in seconds where software Chromium takes ~45 s). Use the
  project's own tool over a new one.
  Try it. If it does not start, that is the first finding: fix only if trivial, otherwise say
  so and plan captures from the live URL or stop.
- What it does, from the code and a short session using it: the three or four moments worth a
  screenshot, and the one motion worth a clip.
- Portfolio: does a page exist already (`grep -rn "<repo>" src/data/` in the Design Portfolio
  Site)? If yes, this run updates it instead of adding one.

End with the gate: the repo to create (stage 2), PRs to merge (number, title, checks), what you
will capture, where the page goes, cost (usually zero; a hero mockup is free on the ChatGPT
plan). If the repo has no `LICENSE`, ask which code licence to add in the same message, MIT
offered first: 1. MIT, 2. another he names, 3. none for now. Never pick one silently; no
answer means no `LICENSE` file and a line in the closing message. Ask go / change / stop.

### Stage 2: Repo setup (skip when the project has a GitHub remote)

For an exploration with no git repo or no GitHub remote. It runs before the README so the
README has somewhere to land.

1. **Folder.** The project lives in `~/ClaudeCode Projects/<Name>`; the repo slug is the name
   in lowercase with hyphens, and `gh repo view weeeha/<slug>` must fail (no clash). If it sits in a temporary
   or session folder, move it there first: those are deleted with the session.
2. **Init.** `git init -b main`, then, before any commit,
   `git config --local user.email 1083934+weeeha@users.noreply.github.com` and read it back
   with `git config --local user.email` (the value is from `me:new-project`; the global email
   is the private gmail and GitHub rejects a push that exposes it).
3. **First commit on main holds only `.gitignore`.** Dependencies, build output, `.env*`, OS
   files, raw generation output. Nothing else goes on main directly.
4. **The work goes on a branch** (`explore/<slug>`). Before staging it, run stage 3 if anything
   third-party is bundled, so material that cannot be shared is never committed.
5. **Licence file.** With Nick's answer from the gate, add `LICENSE` on the branch (year, his
   name). It covers his code only; bundled material keeps its own licence (stage 3).
6. **Check what is tracked before the first push.** Stage the work, then run the script that
   ships in this skill's folder (`<skill>` is the base directory shown when the skill loads):

   ```bash
   bash "<skill>/scripts/private-check.sh" --self-test
   ```

   ```bash
   bash "<skill>/scripts/private-check.sh" .
   ```

   The first plants a home path, a client name, a token and a `.env` in a throwaway repo and
   must report all four caught; a check that has not caught a planted example proves nothing.
   The second scans this repo's tracked files for private paths, private names (clients, the
   login name, the private email; add project-specific ones with `PRIVATE_EXTRA='a|b'`) and
   credentials. Show Nick both outputs. Each hit is fixed, or reported with why it stays.
7. **Create it private and open the PR.** Commit the work on the branch, switch to `main`,
   `gh repo create weeeha/<slug> --private --source=. --push` (this pushes the `.gitignore`
   commit), then push the branch and `gh pr create`. Stage 4 merges it and confirms the PR's
   commit is on `origin/main` with `git merge-base --is-ancestor`, like any other PR. A new repo
   has no checks, so `gh pr checks` reports none; say so and merge on the gate's go.
8. **Public, later, on Nick's word.** After the merge is confirmed, rerun the check from step 6
   on `main`, confirm stage 3 passed, and tell Nick the repo is ready to flip. He says so,
   then: `gh repo edit weeeha/<slug> --visibility public --accept-visibility-change-consequences`.

### Stage 3: Third-party licences (skip when nothing is bundled)

Before a repo goes public, and for a new repo before the work is first committed.

1. **List every third-party asset** in the tree: datasets, models, fonts, images, audio,
   copied code. For each: what it is, where it came from, which files hold it.
2. **Find each licence at its source** (the dataset's page, the repo's `LICENSE`, the font's
   licence file). Fetch it; do not answer from memory. One that cannot be found is "unknown".
3. **Sort into three:**

   | Group | Licences | What happens |
   |---|---|---|
   | Fine to share | public domain, CC0, OFL fonts | stays, listed in the sources table |
   | Fine with credit | CC BY, MIT, BSD, Apache | stays, with its credit or copyright notice kept |
   | Not shareable | non-commercial (NC), no-derivatives (ND), unknown | leaves the tracked tree |

4. **Not-shareable material moves to an optional file** that is listed in `.gitignore` and
   that the app loads only when it is present. Run the app with the file absent: it must start
   and work on the public material alone. The README says where to get the material and what
   to name the file; for an unknown licence it says "source licence not found, not included".
5. **README gets a sources table** (asset, source link, licence, in the repo or optional) and
   a credits section with the attribution each licence asks for (stage 6).

Worked example, Walk Study: two takes came from Ubisoft's LAFAN1 dataset (CC BY-NC-ND 4.0).
They were split out of `clips.json` into `clips.ubisoft.json`, which is in `.gitignore` and
loaded only when present. The 100STYLE (CC BY 4.0) and CMU takes stayed in the public
`clips.json`, with credits.

In a repo that already has history, moving a file out of the tree leaves it in old commits.
Say so and let Nick choose (keep the repo private, or rewrite history) before it goes public.

### Stage 4: Merge

For each approved PR: `gh pr checks <n> --watch`, then merge, then
`git merge-base --is-ancestor <head> origin/main`. Conflicts go to `me:untangle`. A stacked PR
is retargeted to main before its base merges. If the repo deploys on merge, check the live
URL afterwards; a failed production build is reported with its log, and a transient one
(fonts, network) gets one `vercel redeploy`.

### Stage 5: Run and capture

Start it from `main` after the merges, on its own port (`.claude/launch.json` with
`autoPort`, or `next dev -p 31xx`), and drive it in the Browser pane:

- **Screenshots** into `docs/screenshots/` at 1440x900 desktop (2x where the pane allows) and
  one at 390x844 mobile if the app is responsive. Name by moment: `01-empty.png`,
  `02-in-use.png`, `03-result.png`. Use sample data that ships with the repo; never type real
  credentials. Close modals and dev overlays first.
- **Clip**: a 4 to 8 s screen recording of the signature motion (Browser pane `gif_creator` or a
  frame sequence through `ffmpeg`), as `docs/screenshots/clip.mp4` and a 4:3 crop for the card.
- **Non-web projects**: CLIs get a terminal capture (font 16, dark theme); iOS apps go through
  the iOS Simulator tool's screenshots; hardware gets Nick's photos, or, if none exist, a
  Blender render of its real design files with the concept pipeline's render-to-photo stage,
  captioned as a render.

A hidden Browser pane does not run animation or draw WebGL, so a 3D stage comes back blank
with no console error. Before trusting a blank capture, check whether the pane is hidden
(`tabs_context` says so). If it is, ask Nick to show it, or fall back to a headless Chrome
render (the project's capture tool or its playwright, as in stage 1) and look at the result.

Look at every capture before using it: a spinner, an error toast or a half-loaded state is a
retake, not a picture. Any loop or glob in the capture commands goes in a bash script
(`bash file.sh`): in zsh, `set -- $s` does not split and an empty glob aborts the chain, and both
broke captures in the first run.

A clip of a 3D or canvas app: drive it with the project's playwright (WebKit), take one
screenshot per mouse step into a frame folder, then
`ffmpeg -framerate 24 -i f%03d.png -c:v libx264 -crf 22 -pix_fmt yuv420p orbit.mp4`. 132 frames
gave a smooth 5.5 s orbit.

### Stage 6: README

On branch `docs/showcase` in the project:

```
# <Name>
<One sentence: what it does for whom.>

![<what the screenshot shows>](docs/screenshots/02-in-use.png)

## What it does       three to five lines, the moments from the captures
## Run it             the exact commands that worked in stage 5
## How it works       stack, the one idea that makes it interesting, a small diagram if useful
## Findings           two lines and a link to docs/FINDINGS.md (stage 7)
## Sources            table: asset, source, licence, in the repo or optional (stage 3)
## Credits            the attribution each licence asks for; the code licence in one line
## Status             what works, what is stubbed or sample, what is next (one short list)
```

Findings, Sources and Credits appear only when their stage ran.

Keep anything accurate the old README had (licences, credits, API notes). Commit, PR, merge
(no deploy usually; if the repo deploys docs, it is still harmless). Prose rules from
`~/.claude/packs/modules/writing-full.md`: no em dashes, no exclamation marks.

### Stage 7: Findings and decisions

`docs/FINDINGS.md`, on the same `docs/showcase` branch, linked from the README. It keeps what
the chat would otherwise lose: why each choice was made.

```
# Findings and decisions
TL;DR                 three lines at most
## What was explored  the question, and what was built to answer it
## What was found     each finding, with the number or capture behind it
## Decisions          each decision, then one sentence of why
## Tried and dropped  what, and why it went
## Open questions     what Nick still has to decide
## Unverified         what was not checked, and how it could be
```

Sources are the session conversation and the git history (`git log`, PR bodies,
`docs/showcase-log.md`). When the exploration happened in another session, find it with
`me:stranded` and read it. Invent nothing: a finding or a why with no source is left out, or
goes under Unverified or Open questions. An empty section stays, with "None".

### Stage 8: Hero shot (optional)

One image that shows the project in the world: the real screenshot on a laptop on a desk, the
game on a phone in a hand, the poster printed on a wall.

```bash
bash ~/.claude/skills/codex-image/scripts/codex-image.sh -s landscape \
  -r docs/screenshots/02-in-use.png -o docs/screenshots/hero.png \
  "Put this exact screen, unchanged, on <device> in <setting>. Keep every element of the screen \
as is; do not redraw the interface. Photographic, soft light, no text added." 2> /tmp/hero.log
```

Compare it with the screenshot: if the interface on the device was redrawn (changed labels,
layout, colors), drop it and use the plain screenshot as the cover. Caption: "Mockup of the
real screen on <device>."

### Stage 9: Page

Same mechanics as `concept-lab:concept` stage 6 (worktree off `origin/main`, assets in
`public/vibefolio/<slug>/`, diagram from `docs/case-studies/walking-planter/diagrams.html` and
`render-diagrams.sh`, tests, local check in the Browser pane, PR, Nick's yes to merge, live
checksum check). Differences:

- **Where:** a new entry goes in `src/data/candidatePages.ts` (group `candidates`, `draft: true`,
  shown on previews under "More from GitHub (drafts)"). A test keeps every candidate a draft.
  Promoting a page to the live site is Nick's decision: it moves to `projectPages.ts` (the
  homepage list, pinned by a test) or a new group, in its own change. If the project already
  has a page, update that entry.
- **Shape:** copy an existing candidate (Frontline, Agent Channels): `status` says what it is
  and where it runs ("Working editor, live", "Runs in the simulator"), `cover` is a real
  screenshot (or the hero mockup, captioned as such), `summary` from the README, two or three
  `decisions` that came from the code, `hoverVideo` from the clip, `links` to the repo and live
  URL (public repos only, listed in `docs/vibefolio-visual-audit-2026-11-01.tsv`), and an
  honest `currentState`.
- **Limits (a test enforces them):** a short page has at most 3 decisions, at most 2 of them
  with a `screen`, at most 2 diagrams, and every image needs alt and caption. A `loop` (the
  capture clip, 16:9) shows on the page; `hoverVideo` (4:3 crop) on the card.
- **Evidence:** add a row to `docs/vibefolio-evidence.md`: source inspected, which captures are
  fresh, what is sample data, how generated examples were chosen.

## Closing message

The preview link first, then: the repo created and its visibility, PRs merged, README and
findings PR, licence results (what stayed, what moved to an optional file), captures taken,
page entry and where it sits, what is still a draft or unverified, and the one decision left
for Nick (usually: promote it to the live list, or make the repo public?).

## Done check

- [ ] Target named in the first line; not a client repo
- [ ] Gate passed; every merge confirmed on main by ancestry, not by label
- [ ] New repo: under `~/ClaudeCode Projects`, no-reply commit email, main started with only
      `.gitignore`, private, self-test caught its planted examples before the first push
- [ ] Code licence was Nick's answer, or there is no `LICENSE` and the closing message says so
- [ ] Every third-party asset has a licence found at its source; nothing NC, ND or unknown is
      tracked; the app runs without the optional file
- [ ] App ran from main after the merges; every capture looked at, no error states
- [ ] README has a screenshot near the top, commands that actually worked, a Status section,
      and (when they apply) the findings link, sources table and credits
- [ ] `docs/FINDINGS.md` traces to the conversation and git history; unverified items listed
- [ ] Hero mockup (if any) keeps the real screen and is captioned as a mockup
- [ ] Page entry is a draft in candidatePages (or an update to an existing page)
- [ ] Evidence row added; tests pass or a red test is shown to be red on main too
- [ ] Preview link checked in the Browser pane
