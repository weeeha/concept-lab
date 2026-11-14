#!/usr/bin/env bash
# private-check.sh: before a first push, scan the files git tracks (the index) for
# private paths, private names and credentials.
#
#   bash private-check.sh [repo-dir]     exit 0 = clean, 1 = hits (listed), 2 = not a repo
#   bash private-check.sh --self-test    plants one example of each kind in a throwaway
#                                        repo and proves the check catches all of them
#
# Extra names to look for (a person, a client, a codename), as an extended regex:
#   PRIVATE_EXTRA='acme|jane doe' bash private-check.sh
#
# Hits are a review list, not a verdict: fix each one or tell Nick why it stays.
set -u

check() {
  local repo="$1" hits=0 out
  git -C "$repo" rev-parse --git-dir >/dev/null 2>&1 || { echo "not a git repo: $repo"; return 2; }

  # 1. Private paths: a home folder baked into a tracked file.
  out=$(git -C "$repo" grep --cached -nIE '/Users/[A-Za-z0-9._-]+/|/home/[A-Za-z0-9._-]+/|[A-Z]:\\Users\\' 2>/dev/null)
  [ -n "$out" ] && { echo "== private paths"; echo "$out"; hits=1; }

  # 2. Private names: client names, the login name, the private git email, anything in PRIVATE_EXTRA.
  local names='ten8|permitnav|knockpro|pegbo' email
  names="$names|$(id -un)"
  email=$(git config --global user.email 2>/dev/null || true)
  case "$email" in ''|*noreply*) ;; *) names="$names|${email//./\\.}" ;; esac
  [ -n "${PRIVATE_EXTRA:-}" ] && names="$names|$PRIVATE_EXTRA"
  out=$(git -C "$repo" grep --cached -nIiE "$names" 2>/dev/null)
  [ -n "$out" ] && { echo "== private names"; echo "$out"; hits=1; }

  # 3. Credentials: key formats, quoted secrets assigned to a secret-looking name, key files.
  # AWS and Google keys are made only of base64 characters, so a run inside packed binary data
  # can look like one. A real key is a whole token: require a non-base64 character (or the line
  # edge) on both sides. "=" may come before a key (KEY=AKIA...) but not after it (padding).
  local b='(^|[^A-Za-z0-9+/_-])' e='([^A-Za-z0-9+/=_-]|$)'
  local creds='-----BEGIN [A-Z ]*PRIVATE KEY-----|ghp_[A-Za-z0-9]{36}|github_pat_[A-Za-z0-9_]{22,}|sk-[A-Za-z0-9_-]{20,}|'"$b"'AKIA[0-9A-Z]{16}'"$e"'|xox[baprs]-[A-Za-z0-9-]{10,}|'"$b"'AIza[0-9A-Za-z_-]{35}'"$e"
  local assign='(api[_-]?key|secret|token|passwd|password)["'"'"']?[[:space:]]*[:=][[:space:]]*["'"'"'][^"'"'"']{12,}["'"'"']'
  out=$(git -C "$repo" grep --cached -nIE -e "$creds" 2>/dev/null; git -C "$repo" grep --cached -nIiE -e "$assign" 2>/dev/null)
  [ -n "$out" ] && { echo "== credentials"; echo "$out"; hits=1; }

  local f files=""
  while IFS= read -r f; do
    case "$f" in *.example|*.sample|*.template) ;; *) files="$files$f"$'\n' ;; esac
  done < <(git -C "$repo" ls-files -- '.env' '.env.*' '**/.env' '**/.env.*' '*.pem' '*.p12' '*.key' '*id_rsa*' '*id_ed25519*')
  [ -n "$files" ] && { echo "== credential files tracked"; printf '%s' "$files"; hits=1; }

  [ "$hits" -eq 0 ] && echo "clean: $(git -C "$repo" ls-files | wc -l | tr -d ' ') tracked files, no private paths, names or credentials"
  return "$hits"
}

self_test() {
  local t fail=0 out
  t=$(mktemp -d) || exit 2
  git -C "$t" init -q -b main
  printf 'node_modules/\n' > "$t/.gitignore"
  printf 'export const title = "walk study";\n' > "$t/app.js"
  # Packed binary data must not read as a key. Base64 of small 16-bit numbers is full of
  # capital-letter runs, and one can start with the fixed prefix of an AWS or Google key
  # (seen in Walk Study's clips.json). Assembled here so this script holds no key-shaped string.
  printf '{"pos":"AAEAAgAD%s%sAAQABQAG%s%sAAcACAAJ"}\n' \
    'AKIA' 'IABLAPAAVQBOABMB' 'AIza' 'AAEAAgADAAQABQAGAAcACAAJAAoACwAMAA0' > "$t/packed-data.json"
  git -C "$t" add -A
  if out=$(check "$t"); then echo "self-test: clean repo with packed data passes"; else echo "self-test FAILED: clean repo reported hits"; echo "$out" | cut -c1-200; fail=1; fi

  # Planted examples. The tokens are assembled here so this script holds no token-shaped string.
  printf 'const data = "/Users/someone/Desktop/takes.json";\n' > "$t/planted-path.js"
  printf 'Built for the PermitNav demo.\n' > "$t/planted-name.md"
  printf 'const k = "%s%s";\n' 'ghp_' 'abcdefghijklmnopqrstuvwxyz0123456789' > "$t/planted-cred.js"
  printf 'aws_access_key_id=%s%s\n' 'AKIA' 'ABCDEFGHIJKLMNOP' > "$t/planted-aws.ini"
  printf 'const g = "%s%s";\n' 'AIza' 'abcdefghijklmnopqrstuvwxyz012345678' > "$t/planted-google.js"
  printf 'KEY=value\n' > "$t/.env"
  git -C "$t" add -A -f
  out=$(check "$t"); local code=$?
  [ "$code" -eq 1 ] || { echo "self-test FAILED: planted repo exited $code, expected 1"; fail=1; }
  if printf '%s\n' "$out" | grep -q 'packed-data.json'; then echo "self-test FAILED: packed data reported as a hit"; fail=1; fi
  local want n=0
  for want in 'planted-path.js' 'planted-name.md' 'planted-cred.js' 'planted-aws.ini' 'planted-google.js' '^\.env$'; do
    n=$((n+1))
    if printf '%s\n' "$out" | grep -qE -- "$want"; then echo "self-test: caught ${want}"; else echo "self-test FAILED: missed ${want}"; fail=1; fi
  done
  rm -rf "$t"
  [ "$fail" -eq 0 ] && echo "self-test: $n of $n planted examples caught, packed data left alone" || echo "self-test: FAILED"
  return "$fail"
}

case "${1:-.}" in
  --self-test) self_test ;;
  *) check "${1:-.}" ;;
esac
