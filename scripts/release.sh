#!/usr/bin/env bash
# =============================================================================
# Blacklist Release Automation
# =============================================================================
# Usage:
#   make release              # patch bump (3.6.1 -> 3.6.2)
#   make release TYPE=minor   # minor bump (3.6.1 -> 3.7.0)
#   make release TYPE=major   # major bump (3.6.1 -> 4.0.0)
#   make release-dry          # dry-run (show what would happen)
#   make release-dry TYPE=minor
#
# What it does:
#   1. Validate clean working tree and master branch
#   2. Bump VERSION file (semver)
#   3. Auto-generate CHANGELOG entry from git log
#   4. Commit version metadata, changelog, and release notes
#   5. Push the release commit and wait for its exact CI run
#   6. Create and push annotated tag v{VERSION}
#   7. Release pipeline auto-triggers (build → package → sign → GHCR)
# =============================================================================

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

info()  { echo -e "${CYAN}→${NC} $*"; }
ok()    { echo -e "${GREEN}✅${NC} $*"; }
warn()  { echo -e "${YELLOW}⚠️${NC}  $*"; }
error() { echo -e "${RED}❌${NC} $*" >&2; exit 1; }

# --- Configuration ---
BUMP_TYPE="${1:-auto}"
DRY_RUN="${2:-false}"
VERSION_FILE="VERSION"
CHANGELOG_FILE="CHANGELOG.md"
FRONTEND_PKG="frontend/package.json"
FRONTEND_LOCK="frontend/package-lock.json"
PDF_MANIFEST="docs/manual/pdf-sources.sha256"
PDF_OUTPUTS=(
  "docs/manual/blacklist-admin-guide.pdf"
  "docs/manual/blacklist-user-guide.pdf"
  "docs/manual/blacklist-offline-deployment-guide.pdf"
)
REPO_URL="$(git remote get-url origin 2>/dev/null | sed -e 's/\.git$//' -e 's|git@github.com:|https://github.com/|')"

# --- Validate ---
info "Validating release preconditions..."

# Check we're on master
BRANCH=$(git branch --show-current)
if [[ "$BRANCH" != "master" ]]; then
  error "Must be on master branch (current: ${BRANCH})"
fi

# Check clean working tree
if ! git diff-index --quiet HEAD -- 2>/dev/null; then
  error "Uncommitted changes detected. Commit or stash before releasing."
fi

# Check bump type
if [[ "$BUMP_TYPE" != "patch" && "$BUMP_TYPE" != "minor" && "$BUMP_TYPE" != "major" && "$BUMP_TYPE" != "current" && "$BUMP_TYPE" != "auto" ]]; then
  error "Invalid bump type: ${BUMP_TYPE}. Must be: auto, patch, minor, major, or current"
fi

# Read current version
if [[ ! -f "$VERSION_FILE" ]]; then
  error "VERSION file not found"
fi
CURRENT_VERSION=$(tr -d '[:space:]' < "$VERSION_FILE")

if [[ ! "$CURRENT_VERSION" =~ ^([0-9]+)\.([0-9]+)\.([0-9]+)$ ]]; then
  error "Invalid version format: ${CURRENT_VERSION} (expected MAJOR.MINOR.PATCH)"
fi
MAJOR=$((10#${BASH_REMATCH[1]}))
MINOR=$((10#${BASH_REMATCH[2]}))
PATCH=$((10#${BASH_REMATCH[3]}))

# Calculate new version
case "$BUMP_TYPE" in
  major) NEW_VERSION="$((MAJOR + 1)).0.0" ;;
  minor) NEW_VERSION="${MAJOR}.$((MINOR + 1)).0" ;;
  patch) NEW_VERSION="${MAJOR}.${MINOR}.$((PATCH + 1))" ;;
  current) NEW_VERSION="$CURRENT_VERSION" ;;
  auto) NEW_VERSION="$CURRENT_VERSION" ;;
esac

RELEASE_NOTES_FILE="docs/manual/blacklist-${NEW_VERSION}-release-notes.md"
if [[ ! -f "$RELEASE_NOTES_FILE" ]]; then
  error "Release notes file not found: ${RELEASE_NOTES_FILE}. Create it before releasing."
fi
if [[ ! -s "$RELEASE_NOTES_FILE" ]]; then
  error "Release notes file is empty: ${RELEASE_NOTES_FILE}. Add release details before releasing."
fi
if ! git ls-files --error-unmatch "$RELEASE_NOTES_FILE" >/dev/null 2>&1; then
  error "Release notes file must be tracked: ${RELEASE_NOTES_FILE}. Add and commit it before releasing."
fi
if [[ "$BUMP_TYPE" == "current" || "$BUMP_TYPE" == "auto" ]] && ! grep -Fq "## [${NEW_VERSION}]" "$CHANGELOG_FILE"; then
  error "CHANGELOG entry not found for current version: ${NEW_VERSION}"
fi

# Check tag doesn't already exist
if git tag -l "v${NEW_VERSION}" | grep -q .; then
  error "Tag v${NEW_VERSION} already exists"
fi

ok "Validation passed"

# --- Summary ---
echo ""
echo -e "${BOLD}Release Plan${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "  Bump type:       ${CYAN}${BUMP_TYPE}${NC}"
echo -e "  Current version: ${YELLOW}${CURRENT_VERSION}${NC}"
echo -e "  New version:     ${GREEN}${NEW_VERSION}${NC}"
echo -e "  Branch:          ${CYAN}${BRANCH}${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# --- Generate changelog entry ---
if [[ "$BUMP_TYPE" != "current" && "$BUMP_TYPE" != "auto" ]]; then
info "Generating changelog from git log..."

# Get last tag
LAST_TAG=$(git describe --tags --abbrev=0 2>/dev/null || echo "")
if [[ -n "$LAST_TAG" ]]; then
  COMMIT_RANGE="${LAST_TAG}..HEAD"
  info "Changes since ${LAST_TAG}:"
else
  COMMIT_RANGE="HEAD"
  info "All commits (no previous tag found):"
fi

# Collect commits
ADDED=""
BREAKING=""
FIXED=""
CHANGED=""
CICD=""
OTHER=""

while IFS= read -r line; do
  [[ -z "$line" ]] && continue
  # Skip merge commits and retrigger commits
  [[ "$line" =~ ^Merge\ |^ci:\ retrigger ]] && continue

  # Extract prefix: "fix(scope): message" -> "fix"
  PREFIX=$(echo "$line" | sed -n 's/^\([a-z]*\)[\(:].*$/\1/p')

  case "$PREFIX" in
    feat)      ADDED="${ADDED}\n- ${line}" ;;
    fix)       FIXED="${FIXED}\n- ${line}" ;;
    refactor|perf|style) CHANGED="${CHANGED}\n- ${line}" ;;
    ci|build)  CICD="${CICD}\n- ${line}" ;;
    docs)      OTHER="${OTHER}\n- ${line}" ;;
    test)      OTHER="${OTHER}\n- ${line}" ;;
    chore)     ;; # Skip chore commits (version bumps, etc.)
    *)         OTHER="${OTHER}\n- ${line}" ;;
  esac
done < <(git log "$COMMIT_RANGE" --pretty=format:"%s" --no-merges 2>/dev/null)

BREAKING=$(awk '
  $0 == "## Breaking Changes" { found=1; next }
  /^## / { if (found) exit }
  found && /^- / { print }
' "$RELEASE_NOTES_FILE")

# Build changelog section
TODAY=$(date +%Y-%m-%d)
CHANGELOG_ENTRY="## [${NEW_VERSION}] - ${TODAY}"

[[ -n "$BREAKING" ]] && CHANGELOG_ENTRY="${CHANGELOG_ENTRY}\n\n### Breaking\n${BREAKING}"
[[ -n "$ADDED" ]]   && CHANGELOG_ENTRY="${CHANGELOG_ENTRY}\n\n### Added${ADDED}"
[[ -n "$CHANGED" ]]  && CHANGELOG_ENTRY="${CHANGELOG_ENTRY}\n\n### Changed${CHANGED}"
[[ -n "$FIXED" ]]   && CHANGELOG_ENTRY="${CHANGELOG_ENTRY}\n\n### Fixed${FIXED}"
[[ -n "$CICD" ]]    && CHANGELOG_ENTRY="${CHANGELOG_ENTRY}\n\n### CI/CD${CICD}"
[[ -n "$OTHER" ]]   && CHANGELOG_ENTRY="${CHANGELOG_ENTRY}\n\n### Other${OTHER}"

# If no categorized commits, add a generic entry
if [[ -z "$ADDED" && -z "$CHANGED" && -z "$FIXED" && -z "$CICD" && -z "$OTHER" ]]; then
  CHANGELOG_ENTRY="${CHANGELOG_ENTRY}\n\n### Changed\n- Release ${NEW_VERSION}"
fi

echo ""
echo -e "${BOLD}Changelog Preview:${NC}"
echo "─────────────────────────────────────"
echo -e "$CHANGELOG_ENTRY"
echo "─────────────────────────────────────"
else
  ok "Using existing VERSION, CHANGELOG, and release notes for v${NEW_VERSION}"
fi

# --- Dry Run Exit ---
if [[ "$DRY_RUN" == "true" ]]; then
  echo ""
  warn "DRY RUN — no changes made"
  echo ""
  echo "To execute this release, run:"
  echo -e "  ${CYAN}make release TYPE=${BUMP_TYPE}${NC}"
  exit 0
fi

if ! command -v gh &>/dev/null || ! gh auth status &>/dev/null 2>&1; then
  error "Authenticated gh CLI is required to verify the release commit CI before tagging."
fi

# --- Execute Release ---
echo ""
info "Executing release..."

if [[ "$BUMP_TYPE" != "current" && "$BUMP_TYPE" != "auto" ]]; then
echo "${NEW_VERSION}" > "$VERSION_FILE"
ok "VERSION bumped: ${CURRENT_VERSION} → ${NEW_VERSION}"

if [[ -f "$FRONTEND_PKG" ]]; then
  (cd frontend && npm version "$NEW_VERSION" --no-git-tag-version --allow-same-version > /dev/null)
  ok "frontend package metadata synced to ${NEW_VERSION}"
fi

make docs-pdf
ok "Guide PDFs regenerated for ${NEW_VERSION}"


# 2. Update CHANGELOG
# Insert new entry after [Unreleased] section
TMPFILE=$(mktemp)
ENTRY_WRITTEN=false

while IFS= read -r line; do
  echo "$line" >> "$TMPFILE"
  # Insert after the "---" that follows [Unreleased]
  if [[ "$ENTRY_WRITTEN" == "false" && "$line" == "---" ]]; then
    # Check if previous line area was [Unreleased]
    PREV=$(tail -3 "$TMPFILE" | head -1)
    if [[ "$PREV" =~ \[Unreleased\] ]]; then
      {
        echo ""
        echo -e "$CHANGELOG_ENTRY"
        echo ""
        echo "---"
      } >> "$TMPFILE"
      ENTRY_WRITTEN=true
    fi
  fi
done < "$CHANGELOG_FILE"

if [[ "$ENTRY_WRITTEN" == "true" ]]; then
  mv "$TMPFILE" "$CHANGELOG_FILE"
  ok "CHANGELOG updated with [${NEW_VERSION}] entry"
else
  rm -f "$TMPFILE"
  warn "Could not auto-insert CHANGELOG entry (manual edit may be needed)"
fi

# 3. Commit
git add "$VERSION_FILE" "$CHANGELOG_FILE" "$FRONTEND_PKG" "$FRONTEND_LOCK" "$RELEASE_NOTES_FILE" "$PDF_MANIFEST" "${PDF_OUTPUTS[@]}"
git commit -m "chore(release): v${NEW_VERSION}

Automated release: ${BUMP_TYPE} bump ${CURRENT_VERSION} → ${NEW_VERSION}"
ok "Changes committed"
else
  ok "Current version metadata already committed; skipping release metadata commit"
fi

info "Pushing release commit to origin..."
git push origin master
HEAD_SHA=$(git rev-parse HEAD)
CI_WORKFLOW="CI"
CI_RUN_ID=""
for attempt in $(seq 1 30); do
  CI_RUN_ID=$(gh run list --workflow "$CI_WORKFLOW" --commit "$HEAD_SHA" --event push --limit 1 --json databaseId --jq '.[0].databaseId // empty' 2>/dev/null || true)
  [[ -n "$CI_RUN_ID" ]] && break
  info "Waiting for the release commit CI run to start (attempt ${attempt}/30)..."
  sleep 10
done
if [[ -z "$CI_RUN_ID" ]]; then
  error "No CI run found for release commit ($HEAD_SHA). No tag was created."
fi
if ! gh run watch "$CI_RUN_ID" --exit-status; then
  error "CI failed on release commit ($HEAD_SHA). No tag was created."
fi
ok "CI passed on release commit ($HEAD_SHA)"

REMOTE_MASTER_SHA=$(git ls-remote origin refs/heads/master | cut -f1)
[[ "$REMOTE_MASTER_SHA" == "$HEAD_SHA" ]] || error "origin/master moved after CI verification. No tag was created."
git tag -a "v${NEW_VERSION}" "$HEAD_SHA" -m "v${NEW_VERSION}"
ok "Tag v${NEW_VERSION} created"
git push origin "v${NEW_VERSION}"
ok "Pushed tag v${NEW_VERSION} to origin"

# --- Done ---
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "${GREEN}${BOLD}🚀 Release v${NEW_VERSION} initiated!${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Release pipeline will now:"
echo "  1. Validate VERSION == tag"
  echo "  2. Build 5 Docker images (frontend, app, collector, postgres, redis)"
  echo "  3. Package release bundle with ${RELEASE_NOTES_FILE}"
echo "  4. Create GitHub Release with assets"
echo "  5. Push images to GHCR"
echo "  6. Send Slack notification"
echo ""
echo -e "Monitor: ${CYAN}${REPO_URL}/actions${NC}"
echo -e "Release: ${CYAN}${REPO_URL}/releases/tag/v${NEW_VERSION}${NC}"
