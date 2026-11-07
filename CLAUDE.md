# Concept Lab

Idea in, concept piece out. A concept piece is a case study for something Nick plans to build
but has not built yet: a brief, a repo with plausible untested code, a 3D model, stills, a short
video and a page under Concepts on vyhouski.com/projects. Nick's global rules apply (`~/.claude/CLAUDE.md`).

## The one rule that matters

**A concept says so once.** The page status ("Concept, not built") and one README status
line; no disclaimer in every file, caption and commit. Never invent facts about Nick: no
clients, no metrics, no "shipped", no "in production", no "users". A concept piece never feeds the CV side (`me:apply`, `me:company`,
nicks-bio). If a concept later gets built for real, the case study is rewritten from repo
evidence, not promoted in place.

## Layout

- `skills/concept/SKILL.md`: the pipeline. Invoke as `concept-lab:concept`.
- `templates/`: skeletons the pipeline fills. Change the template, not the skill, to change the shape.
- `concepts/<slug>/`: one folder per concept (brief, parts, 3D sources, picked renders, video, case-study draft).
  Raw generation output stays out of git (`.gitignore`).
- Published targets live elsewhere: code repo `weeeha/<slug>` (GitHub), page `/projects/<slug>`
  in `~/ClaudeCode Projects/Design Portfolio Site`.

## Working here

- Branch per concept: `concept/<slug>`. Never push to `main`. Stage `concepts/<slug>/` by path,
  never `git add -A` at the root (the hook blocks nested repos and files over 25 MB).
- Paid generation (Seedance video) only after Nick approved the brief. Codex images are free on his plan.
- The Blender model is the only source of what the object looks like: Blender headless for the
  model, shot renders and GLB; `codex-image -r <render>` for photos (the hook blocks it without
  `-r`); Seedance from the hero photo for the clip. Details in `skills/concept/SKILL.md`.
- No stray protrusions: sensors flush or under a dome unless the brief says why not.
- Prose a client could read follows `~/.claude/packs/modules/writing-full.md`: no em dashes, no
  exclamation marks, TL;DR first, Nick hand-edits before it goes live.
