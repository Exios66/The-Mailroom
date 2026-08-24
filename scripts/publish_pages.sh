#!/usr/bin/env bash
# Build + publish the static site to the `gh-pages` branch — NO GitHub Actions.
#
# GitHub Pages serves it via the native "Deploy from a branch" mode, which is
# configured ONCE in the GitHub UI (Settings → Pages → Source: "Deploy from a
# branch", branch: gh-pages, folder: /docs) and never touches Actions.
#
# Site layout produced (under docs/ on the gh-pages branch):
#   docs/index.html       SPA shell (relative asset paths)
#   docs/static/{css,js}  pixel-engine assets
#   docs/.nojekyll        disable Jekyll processing
#   docs/data/*.json      snapshot exported from the trace source
#                         (Langfuse / Phoenix / both) by export_snapshot.py
#   docs/debug/build-info.json  provenance for agents (git sha, counts)
#
# Anything else already on the branch root is left untouched; legacy root-
# level site files from older publishes are cleaned up.
#
# Usage:
#   scripts/publish_pages.sh [--source langfuse|phoenix|both] [--since-hours N]
#                            [--limit N] [--skip-export] [--dry-run]
# Env overrides: PAGES_BRANCH (default gh-pages), PAGES_REMOTE (default origin).
set -euo pipefail

cd "$(dirname "$0")/.."

SOURCE="auto"
SINCE_HOURS="24"
LIMIT="200"
SKIP_EXPORT=0
DRY_RUN=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --source)      SOURCE="$2"; shift 2 ;;
    --since-hours) SINCE_HOURS="$2"; shift 2 ;;
    --limit)       LIMIT="$2"; shift 2 ;;
    --skip-export) SKIP_EXPORT=1; shift ;;
    --dry-run)     DRY_RUN=1; shift ;;
    *) echo "unknown arg: $1" >&2; exit 2 ;;
  esac
done

BRANCH="${PAGES_BRANCH:-gh-pages}"
REMOTE="${PAGES_REMOTE:-origin}"
REPO_URL="$(git remote get-url "$REMOTE")"
HEAD_SHA="$(git rev-parse --short HEAD)"
DIRTY=$(git status --porcelain | head -1)

if [[ -n "$DIRTY" ]]; then
  echo "note: working tree has uncommitted changes; build-info records HEAD ${HEAD_SHA} anyway"
fi

echo "== staging site shell =="
rm -rf site
mkdir -p site/static
cp -R web/css web/js site/static/
cp web/index.html site/
touch site/.nojekyll

if [[ "$SKIP_EXPORT" -ne 1 ]]; then
  echo "== exporting snapshot (source=${SOURCE} since=${SINCE_HOURS}h limit=${LIMIT}) =="
  python scripts/export_snapshot.py \
    --source "$SOURCE" --out site/data \
    --since-hours "$SINCE_HOURS" --limit "$LIMIT"
else
  echo "== skipping export (--skip-export): reusing existing site/data =="
fi

echo "== verifying snapshot =="
python scripts/export_snapshot.py --check --out site/data

if [[ "$DRY_RUN" -eq 1 ]]; then
  echo "== dry run: site/ built, nothing pushed =="
  find site -type f | sort | sed 's/^/  /'
  exit 0
fi

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
CLONE="$TMP/pages"

if git ls-remote --heads "$REMOTE" "refs/heads/$BRANCH" | grep -q .; then
  echo "== publishing to existing $BRANCH (docs/ folder) =="
  git clone --quiet --depth 1 --branch "$BRANCH" "$REPO_URL" "$CLONE"
else
  echo "== creating orphan $BRANCH (first publish) =="
  git clone --quiet --depth 1 "$REPO_URL" "$CLONE"
  (cd "$CLONE" && git checkout --orphan "$BRANCH" && git rm -rf --quiet .)
fi

# Site root on the branch is docs/. Clean legacy root-level site files from
# older publishes; leave anything else at the branch root untouched.
for legacy in index.html .nojekyll static data debug; do
  rm -rf "$CLONE/$legacy"
done
rm -rf "$CLONE/docs"
mkdir -p "$CLONE/docs"
rsync -a --exclude '.git' site/ "$CLONE/docs/"

(
  cd "$CLONE"
  git add -A
  if git diff --cached --quiet; then
    echo "no site changes to publish"
    exit 0
  fi
  git commit --quiet -m "PUBLISH: pages snapshot $(date '+%Y-%m-%d %H:%M %Z') (${HEAD_SHA})"
  if git rev-parse --abbrev-ref HEAD | grep -q "^$BRANCH$"; then
    git push --quiet origin "$BRANCH"
  else
    git push --quiet origin HEAD:"refs/heads/$BRANCH"
  fi
)

echo "published -> $REMOTE@$BRANCH:/docs"
echo "Pages source must be: Deploy from a branch -> $BRANCH -> /docs"
