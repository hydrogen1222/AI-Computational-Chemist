#!/usr/bin/env sh
# Install the AICC skills for Claude Code and/or Codex.
set -eu

usage() {
  cat <<'USAGE'
Usage: ./install.sh [--harness claude|codex|both] [--project DIR] [--force] [--dry-run]

Copies the collection, rewrites tools/... knowledge/... procedures/... references
in the copy to absolute paths, then symlinks every skill into the harness's
skills folder. Re-run after `git pull` to update (use --force).

  global (default)      copy -> ~/.local/share/aicc
                        claude -> ~/.claude/skills    codex -> ${CODEX_HOME:-~/.codex}/skills
  --project DIR         copy -> DIR/.aicc
                        claude -> DIR/.claude/skills + DIR/CLAUDE.md
                        codex  -> DIR/.agents/skills + DIR/AGENTS.md

  --harness   claude, codex or both (default: both)
  --force     replace an existing copy and existing skill links of the same name
  --dry-run   print what would happen

Does not install VASP, CP2K, Multiwfn, Chargemol, licensed POTCARs or any binary.
USAGE
}

die() { printf 'install.sh: %s\n' "$*" >&2; exit 1; }
run() { printf '  %s\n' "$*"; [ "$DRY_RUN" -eq 1 ] || "$@"; }

HARNESS=both PROJECT="" FORCE=0 DRY_RUN=0
while [ "$#" -gt 0 ]; do
  case "$1" in
    --harness) [ "$#" -ge 2 ] || die "--harness needs a value"; HARNESS="$2"; shift 2 ;;
    --project) [ "$#" -ge 2 ] || die "--project needs a directory"; PROJECT="$2"; shift 2 ;;
    --force) FORCE=1; shift ;;
    --dry-run) DRY_RUN=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) die "unknown option: $1 (see --help)" ;;
  esac
done
case "$HARNESS" in claude|codex|both) ;; *) die "--harness must be claude, codex or both" ;; esac
wants() { [ "$HARNESS" = both ] || [ "$HARNESS" = "$1" ]; }

REPO="$(cd "$(dirname "$0")" && pwd -P)"
[ -d "$REPO/tools" ] && [ -d "$REPO/procedures" ] || die "run from an AICC checkout"

if [ -n "$PROJECT" ]; then
  [ -d "$PROJECT" ] || die "project directory does not exist: $PROJECT"
  PROJECT="$(cd "$PROJECT" && pwd -P)"
  COPY="$PROJECT/.aicc"
  CLAUDE_SKILLS="$PROJECT/.claude/skills"
  CODEX_SKILLS="$PROJECT/.agents/skills"
else
  COPY="${XDG_DATA_HOME:-$HOME/.local/share}/aicc"
  CLAUDE_SKILLS="$HOME/.claude/skills"
  CODEX_SKILLS="${CODEX_HOME:-$HOME/.codex}/skills"
fi

# 1. Copy the collection.
printf 'Collection copy: %s\n' "$COPY"
if [ -e "$COPY" ]; then
  [ "$FORCE" -eq 1 ] || die "$COPY exists; re-run with --force to refresh it"
  run rm -rf "$COPY"
fi
run mkdir -p "$COPY"
for item in procedures tools knowledge AGENTS.md; do
  run cp -R "$REPO/$item" "$COPY/$item"
done
run find "$COPY" -name __pycache__ -type d -prune -exec rm -rf {} +

# 2. Make cross-references absolute so they resolve from any working directory.
if [ "$DRY_RUN" -eq 0 ]; then
  command -v python3 >/dev/null 2>&1 || die "python3 is required to rewrite references"
  python3 - "$COPY" <<'PY'
import os, re, sys
base = os.path.realpath(sys.argv[1])
pat = re.compile(r'(?<![\w./-])(knowledge|tools|procedures)/')
n = 0
for root, _, files in os.walk(base):
    for f in files:
        if f.endswith(".md"):
            p = os.path.join(root, f)
            s = open(p, encoding="utf-8").read()
            t = pat.sub(lambda m: base + "/" + m.group(1) + "/", s)
            if t != s:
                open(p, "w", encoding="utf-8").write(t)
                n += 1
print("  rewrote references in %d files" % n)
PY
fi

# 3. Symlink each skill.
link_skills() {
  dest="$1"
  printf 'Skills -> %s\n' "$dest"
  run mkdir -p "$dest"
  for src in "$REPO"/procedures/* "$REPO"/tools/*; do
    [ -f "$src/SKILL.md" ] || continue
    skill="$COPY/${src#"$REPO"/}"
    target="$dest/$(basename "$src")"
    if [ -e "$target" ] || [ -L "$target" ]; then
      if [ "$FORCE" -eq 1 ]; then run rm -rf "$target"
      else printf '  skip existing %s (use --force)\n' "$target"; continue; fi
    fi
    run ln -s "$skill" "$target"
  done
}
link_instructions() {  # link_instructions <file name>
  target="$PROJECT/$1"
  if [ -e "$target" ] || [ -L "$target" ]; then
    printf '  skip existing %s\n' "$target"
  else
    run ln -s "$COPY/AGENTS.md" "$target"
  fi
}

wants claude && link_skills "$CLAUDE_SKILLS"
wants codex && link_skills "$CODEX_SKILLS"
if [ -n "$PROJECT" ]; then
  wants claude && link_instructions CLAUDE.md
  wants codex && link_instructions AGENTS.md
fi

printf '\nDone. Restart the agent so it reloads skills.\n'
printf 'For figures, also install Stormy-drawing: https://github.com/hydrogen1222/Stormy-drawing\n'
