---
name: showcase
description: Turn a quick creative project or prototype that already exists into a finished-looking showcase - merge its open PRs, run it and capture real screenshots, write a README with them, then build its page on vyhouski.com/projects with real captures, a how-it-works diagram, a short screen clip and a hero shot. Use when Nick says "showcase this", "wrap up this prototype", "make this project presentable", "merge the PRs and add a readme with screenshots", "put this on my site", "make a page for this project", or finishes a quick creative build and wants it shown. For ideas that are not built yet, use concept-lab:concept instead.
---

# Showcase

Nick builds quick creative prototypes faster than he presents them: PRs sit open, the README
is the template's, there are no screenshots, and the project is invisible on his site. This
skill takes one existing project from "works on my machine" to a page a client can open.

It is the sibling of `concept-lab:concept`. The difference is evidence: **the thing exists,
so every picture is a real capture of it running.** Generated imagery is allowed only as a
clearly separate hero shot made from a real capture (rule 3).

**Argument:** a project path, a repo name, or nothing (use the current folder). Say the target
in the first line: repo, local path, GitHub account, and whether it has a live URL.

## Rules that never bend

1. **Client repos are off limits.** Ten8, PermitNav, KnockPro and Pegbo repos are read-only
   (see `~/.claude/CLAUDE.md`). If the target is one, stop and say so.
2. **Nothing invented.** Every claim on the README and the page traces to the code, the running
   app or Nick. What is stubbed, sample data or unverified is said once, in `currentState` and
   the README's Status section. No users, metrics or clients.
3. **Captures are real.** Screenshots and clips come from the app running (locally or its live
   URL). A hero "in context" image (the app on a laptop on a desk, the game on a phone) may be
   made with `codex-image -r <real screenshot>`, and its caption says it is a mockup of the real
   screen. No generated interface.
4. **One gate, after the audit.** Stage 1 ends with what will be merged, captured and published,
   and asks go. Merges that deploy and the portfolio merge each need Nick's yes (auto mode
   blocks them anyway); ask once per list, not per PR.
5. **Branch per change, never push to main.** README work on `docs/showcase`, portfolio work
   in a worktree off `origin/main`.

## Pipeline

Each stage logs one line to `docs/showcase-log.md` in the project (what ran, what it found).
Long runs (dev server boot, clip generation) get a progress line: what runs, what it waits on,
about how long.

### Stage 1: Audit (gate)

- Repo: remote, account (`weeeha` or other), default branch, live URL if any (README, Vercel
  project, `vercel ls`). Visibility.
- Open work: `gh pr list --state open` with checks and mergeability; local branches ahead of
  main and uncommitted trees (`me:stranded --fetch` from inside the repo). A PR with red checks
  or a red-phase test is reported, not merged (the `me:stranded` rescue rules apply).
- How to run it: `package.json` scripts, `.claude/launch.json`, a Makefile, the `run` skill.
  Try it. If it does not start, that is the first finding: fix only if trivial, otherwise say
  so and plan captures from the live URL or stop.
- What it does, from the code and a short session using it: the three or four moments worth a
  screenshot, and the one motion worth a clip.
- Portfolio: does a page exist already (`grep -rn "<repo>" src/data/` in the Design Portfolio
  Site)? If yes, this run updates it instead of adding one.

End with the gate: PRs to merge (number, title, checks), what you will capture, where the page
goes, cost (usually zero; a hero mockup is free on the ChatGPT plan). Ask go / change / stop.

### Stage 2: Merge

For each approved PR: `gh pr checks <n> --watch`, then merge, then
`git merge-base --is-ancestor <head> origin/main`. Conflicts go to `me:untangle`. A stacked PR
is retargeted to main before its base merges. If the repo deploys on merge, check the live
URL afterwards; a failed production build is reported with its log, and a transient one
(fonts, network) gets one `vercel redeploy`.

### Stage 3: Run and capture

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

Look at every capture before using it: a spinner, an error toast or a half-loaded state is a
retake, not a picture.

### Stage 4: README

On branch `docs/showcase` in the project:

```
# <Name>
<One sentence: what it does for whom.>

![<what the screenshot shows>](docs/screenshots/02-in-use.png)

## What it does       three to five lines, the moments from the captures
## Run it             the exact commands that worked in stage 3
## How it works       stack, the one idea that makes it interesting, a small diagram if useful
## Status             what works, what is stubbed or sample, what is next (one short list)
```

Keep anything accurate the old README had (licences, credits, API notes). Commit, PR, merge
(no deploy usually; if the repo deploys docs, it is still harmless). Prose rules from
`~/.claude/packs/modules/writing-full.md`: no em dashes, no exclamation marks.

### Stage 5: Hero shot (optional)

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

### Stage 6: Page

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
- **Evidence:** add a row to `docs/vibefolio-evidence.md`: source inspected, which captures are
  fresh, what is sample data.

## Closing message

The preview link first, then: PRs merged, README PR, captures taken, page entry and where it
sits, what is still a draft or unverified, and the one decision left for Nick (usually: promote
it to the live list?).

## Done check

- [ ] Target named in the first line; not a client repo
- [ ] Gate passed; every merge confirmed on main by ancestry, not by label
- [ ] App ran from main after the merges; every capture looked at, no error states
- [ ] README has a screenshot near the top, commands that actually worked, a Status section
- [ ] Hero mockup (if any) keeps the real screen and is captioned as a mockup
- [ ] Page entry is a draft in candidatePages (or an update to an existing page)
- [ ] Evidence row added; tests pass or a red test is shown to be red on main too
- [ ] Preview link checked in the Browser pane
