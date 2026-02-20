#!/usr/bin/env bash
# wiki-sync.sh — Sync docs/wiki/ to the GitHub Wiki repository
#
# Prerequisites:
#   1. Create the first wiki page via GitHub web UI:
#      https://github.com/qws941/blacklist/wiki/_new
#      (This bootstraps the wiki git repo — required one-time step)
#   2. Ensure 'gh' CLI is authenticated: gh auth status
#
# Usage:
#   ./scripts/wiki-sync.sh          # Sync docs/wiki/ -> GitHub Wiki
#   ./scripts/wiki-sync.sh --dry-run  # Preview without pushing

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
WIKI_SRC="${REPO_ROOT}/docs/wiki"
WIKI_REPO_URL="https://github.com/qws941/blacklist.wiki.git"
WORK_DIR=$(mktemp -d)

DRY_RUN=false
if [[ "${1:-}" == "--dry-run" ]]; then
    DRY_RUN=true
fi

cleanup() {
    rm -rf "${WORK_DIR}"
}
trap cleanup EXIT

echo "=== Wiki Sync ==="
echo "Source: ${WIKI_SRC}"
echo "Target: ${WIKI_REPO_URL}"
echo ""

# Verify source exists
if [[ ! -d "${WIKI_SRC}" ]]; then
    echo "ERROR: ${WIKI_SRC} does not exist"
    exit 1
fi

# Clone the wiki repo
echo "[1/4] Cloning wiki repository..."
if ! git clone "${WIKI_REPO_URL}" "${WORK_DIR}/wiki" 2>/dev/null; then
    echo ""
    echo "ERROR: Wiki repository not found."
    echo ""
    echo "The GitHub Wiki git repo doesn't exist yet."
    echo "You must create the first page via the web UI to bootstrap it:"
    echo ""
    echo "  1. Go to: https://github.com/qws941/blacklist/wiki/_new"
    echo "  2. Enter any title and body (will be overwritten)"
    echo "  3. Click 'Save Page'"
    echo "  4. Re-run this script"
    echo ""
    exit 1
fi

# Copy wiki content
echo "[2/4] Copying wiki pages..."
rm -f "${WORK_DIR}/wiki/"*.md
cp "${WIKI_SRC}/"*.md "${WORK_DIR}/wiki/"
echo "  Copied $(ls "${WIKI_SRC}/"*.md | wc -l) pages"

# Check for changes
cd "${WORK_DIR}/wiki"
if git diff --quiet && [[ -z "$(git ls-files --others --exclude-standard)" ]]; then
    echo "[3/4] No changes detected. Wiki is up to date."
    exit 0
fi

# Stage and commit
echo "[3/4] Committing changes..."
git add -A
COMMIT_MSG="docs(wiki): sync from docs/wiki/ ($(date +%Y-%m-%d))"
git commit -m "${COMMIT_MSG}"

# Push
if [[ "${DRY_RUN}" == true ]]; then
    echo "[4/4] DRY RUN — would push the following:"
    git log --oneline -1
    git diff --stat HEAD~1
else
    echo "[4/4] Pushing to wiki..."
    git push origin master
    echo ""
    echo "Wiki updated successfully!"
    echo "View at: https://github.com/qws941/blacklist/wiki"
fi
