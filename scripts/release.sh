#!/usr/bin/env bash
set -euo pipefail

PART="${1:?Usage: $0 <major|minor|patch>}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if ! command -v gh &>/dev/null; then
    echo "Error: gh CLI is not installed. Install it: https://cli.github.com" >&2
    exit 1
fi

if ! gh auth status &>/dev/null; then
    echo "Error: not logged in to GitHub. Run: gh auth login" >&2
    exit 1
fi

if [[ -n "$(git status --porcelain)" ]]; then
    echo "Error: working tree is dirty. Commit or stash changes first." >&2
    exit 1
fi

BRANCH="$(git branch --show-current)"
if [[ "$BRANCH" != "main" ]]; then
    echo "Error: must be on main branch (currently on '$BRANCH')." >&2
    exit 1
fi

git pull --ff-only origin main

VERSION="$(uv run python scripts/bump_version.py "$PART")"
echo "Bumped to: v${VERSION}"

uv lock

git add pyproject.toml uv.lock
git commit -m "release: v${VERSION}"

TAG="v${VERSION}"

if git rev-parse "$TAG" >/dev/null 2>&1; then
    echo "Error: tag $TAG already exists." >&2
    exit 1
fi

git tag "$TAG"
git push origin main "$TAG"

gh release create "$TAG" \
    --title "$TAG" \
    --generate-notes

echo ""
echo "Release $TAG created. GitHub Actions will publish to PyPI."
echo "Track progress: https://github.com/russellsch/some_obsidian_some_mcp/actions"
