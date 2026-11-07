#!/usr/bin/env python3
"""Concept Lab guard, run before every Bash call (PreToolUse).

Acts only on Concept Lab work: the command or the working directory mentions the
Concept Lab folder or a concepts/<slug>/ path. Everything else passes untouched.

1. Blender first. A codex-image.sh call must attach a reference render with -r.
   The first robot-planter run generated stills from text and the four photos showed
   four different robots; a render as reference is what keeps one object across them.
2. Commit guard. Before `git add` or `git commit` in the Concept Lab repo, block if what
   would be staged contains another git repo (a sibling session's worktree once got
   committed as an embedded repo) or a file over 25 MB.

Exit 2 with a message on stderr blocks the call and tells Claude why.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys

LAB = "Concept Lab"
MAX_BYTES = 25 * 1024 * 1024


def block(msg: str) -> None:
    print(f"concept-lab guard: {msg}", file=sys.stderr)
    sys.exit(2)


def codex_calls(cmd: str) -> list[str]:
    """Each codex-image.sh invocation's own arguments, up to the next shell separator."""
    parts = cmd.split("codex-image.sh")[1:]
    return [re.split(r"&&|\|\||;|\n|(?<![<>2])&(?!&)|\|", p, maxsplit=1)[0] for p in parts]


def repo_dir(cmd: str, cwd: str) -> str:
    m = re.findall(r'cd\s+"([^"]+)"|cd\s+(\S+)', cmd)
    for quoted, bare in reversed(m):
        d = os.path.expanduser((quoted or bare).replace("$HOME", os.path.expanduser("~")))
        if os.path.isdir(d):
            return d
    return cwd


def git(d: str, *args: str) -> str:
    r = subprocess.run(["git", "-C", d, *args], capture_output=True, text=True, timeout=8)
    return r.stdout if r.returncode == 0 else ""


def would_stage(d: str, cmd: str) -> list[str]:
    """Paths a `git add -A`/`.` would pick up plus what is already staged."""
    paths = set(git(d, "diff", "--cached", "--name-only").split())
    if re.search(r"git\s+add\s+(-A|--all|\.)(\s|$)|git\s+commit\s+[^|;&]*-a", cmd):
        for line in git(d, "status", "--porcelain", "--untracked-files=all").splitlines():
            if len(line) > 3:
                paths.add(line[3:].strip().strip('"'))
    return sorted(paths)


def check_commit(d: str, cmd: str) -> None:
    top = git(d, "rev-parse", "--show-toplevel").strip()
    if not top or os.path.basename(top) != LAB:
        return
    nested, big = [], []
    for raw in git(top, "diff", "--cached", "--raw").splitlines():
        if " 160000 " in raw:
            nested.append(raw.split("\t")[-1])
    for p in would_stage(top, cmd):
        full = os.path.join(top, p)
        if os.path.isdir(full) and os.path.exists(os.path.join(full.rstrip("/"), ".git")):
            nested.append(p)
        elif os.path.isfile(full) and os.path.getsize(full) > MAX_BYTES:
            big.append(f"{p} ({os.path.getsize(full) // (1024 * 1024)} MB)")
    if nested:
        block("this would commit another git repo or worktree: " + ", ".join(sorted(set(nested)))
              + ". Stage concepts/<slug>/ explicitly instead of `git add -A`, and keep worktrees out (.gitignore has .claude/worktrees/).")
    if big:
        block("file over 25 MB: " + ", ".join(big)
              + ". Keep raw renders and clips in render/raw/ or video/raw/ (gitignored); commit the picks only.")


def main() -> None:
    try:
        data = json.load(sys.stdin)
    except ValueError:
        return
    if data.get("tool_name") != "Bash":
        return
    cmd = (data.get("tool_input") or {}).get("command", "")
    cwd = data.get("cwd", "")
    in_lab = LAB in cwd or LAB in cmd or "/concepts/" in cmd
    if not in_lab:
        return

    if "codex-image.sh" in cmd:
        for args in codex_calls(cmd):
            if "-n" in args.split():
                continue  # dry run
            if not re.search(r"(^|\s)-r\s+\S", args):
                block("codex-image without a reference render. Concept stills are a Blender render "
                      "made photographic: add -r render/shots/<shot>-blender.png (stage 3 renders it).")

    if re.search(r"\bgit\b[^|;&\n]*\b(add|commit)\b", cmd):
        check_commit(repo_dir(cmd, cwd), cmd)


if __name__ == "__main__":
    main()
