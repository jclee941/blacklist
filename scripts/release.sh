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
#   4. Commit VERSION + CHANGELOG
#   5. Create annotated tag v{VERSION}
#   6. Push to master + push tag
#   7. Release pipeline auto-triggers (build → package → GHCR)
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
BUMP_TYPE="${1:-patch}"
DRY_RUN="${2:-false}"
VERSION_FILE="VERSION"
CHANGELOG_FILE="CHANGELOG.md"
REPO_URL="$(git remote get-url origin 2>/dev/null | sed 's/\.git$//' | sed 's|git@github.com:|https://github.com/|')"

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
if [[ "$BUMP_TYPE" != "patch" && "$BUMP_TYPE" != "minor" && "$BUMP_TYPE" != "major" ]]; then
  error "Invalid bump type: ${BUMP_TYPE}. Must be: patch, minor, or major"
fi

# Read current version
if [[ ! -f "$VERSION_FILE" ]]; then
  error "VERSION file not found"
fi
CURRENT_VERSION=$(cat "$VERSION_FILE" | tr -d '[:space:]')

# Parse semver
IFS='.' read -r MAJOR MINOR PATCH <<< "$CURRENT_VERSION"
if [[ -z "$MAJOR" || -z "$MINOR" || -z "$PATCH" ]]; then
  error "Invalid version format: ${CURRENT_VERSION} (expected MAJOR.MINOR.PATCH)"
fi

# Calculate new version
case "$BUMP_TYPE" in
  major) NEW_VERSION="$((MAJOR + 1)).0.0" ;;
  minor) NEW_VERSION="${MAJOR}.$((MINOR + 1)).0" ;;
  patch) NEW_VERSION="${MAJOR}.${MINOR}.$((PATCH + 1))" ;;
esac

RELEASE_NOTES_FILE="docs/manual/blacklist-${NEW_VERSION}-release-notes.md"
if [[ ! -f "$RELEASE_NOTES_FILE" ]]; then
  error "Release notes file not found: ${RELEASE_NOTES_FILE}. Create it before releasing."
fi

# Check tag doesn't already exist
if git tag -l "v${NEW_VERSION}" | grep -q .; then
  error "Tag v${NEW_VERSION} already exists"
fi

ok "Validation passed"
# --- Pre-release test gate ---
# Verify CI passed on the current HEAD commit before releasing.
# Priority: gh CLI (remote CI) > docker stack > local pytest
info "Checking pre-release test status..."

HEAD_SHA=$(git rev-parse HEAD)
CI_VERIFIED=false

# 1. Check remote CI via gh CLI (preferred — verifies exact commit)
if command -v gh &>/dev/null && gh auth status &>/dev/null 2>&1; then
  CI_CONCLUSION=$(gh run list --commit "$HEAD_SHA" --json conclusion,status --jq '.[0].conclusion // empty' 2>/dev/null || true)
  CI_STATUS=$(gh run list --commit "$HEAD_SHA" --json status --jq '.[0].status // empty' 2>/dev/null || true)
  if [[ "$CI_CONCLUSION" == "success" ]]; then
    ok "CI passed on HEAD ($HEAD_SHA)"
    CI_VERIFIED=true
  elif [[ "$CI_STATUS" == "in_progress" || "$CI_STATUS" == "queued" ]]; then
    error "CI is still running on HEAD ($HEAD_SHA). Wait for completion before releasing."
  elif [[ -n "$CI_CONCLUSION" ]]; then
    error "CI failed on HEAD ($HEAD_SHA) with conclusion: ${CI_CONCLUSION}. Fix before releasing."
  else
    warn "No CI run found for HEAD ($HEAD_SHA). Falling back to local tests..."
  fi
fi

# 2. Fallback: Docker stack containerized tests
if [[ "$CI_VERIFIED" == "false" ]]; then
  if command -v docker &>/dev/null && docker compose ps --services 2>/dev/null | grep -q .; then
    if docker compose exec -T blacklist-app python -m pytest tests/ -x -q --tb=short 2>/dev/null; then
      ok "Backend tests passed (docker)"
      CI_VERIFIED=true
    else
      error "Backend tests failed. Fix test failures before releasing."
    fi
  fi
fi

# 3. Fallback: Local pytest
if [[ "$CI_VERIFIED" == "false" ]]; then
  if command -v pytest &>/dev/null; then
    if pytest tests/ -x -q --tb=short 2>/dev/null; then
      ok "Backend tests passed (local)"
      CI_VERIFIED=true
    else
      error "Backend tests failed. Fix test failures before releasing."
    fi
  fi
fi

# 4. No test method available
if [[ "$CI_VERIFIED" == "false" ]]; then
  error "No test verification available (gh CLI, docker stack, or pytest). Install one before releasing."
fi

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

# Categorize commits by conventional commit prefix
declare -A CATEGORIES
CATEGORIES=(
  [feat]="Added"
  [fix]="Fixed"
  [refactor]="Changed"
  [perf]="Changed"
  [style]="Changed"
  [docs]="Documentation"
  [test]="Testing"
  [chore]="Maintenance"
  [ci]="CI/CD"
  [build]="CI/CD"
)

# Collect commits
ADDED=""
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

# Build changelog section
TODAY=$(date +%Y-%m-%d)
CHANGELOG_ENTRY="## [${NEW_VERSION}] - ${TODAY}"

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

# --- Dry Run Exit ---
if [[ "$DRY_RUN" == "true" ]]; then
  echo ""
  warn "DRY RUN — no changes made"
  echo ""
  echo "To execute this release, run:"
  echo -e "  ${CYAN}make release TYPE=${BUMP_TYPE}${NC}"
  exit 0
fi

# --- Execute Release ---
echo ""
info "Executing release..."

# 1. Bump VERSION
echo "${NEW_VERSION}" > "$VERSION_FILE"
ok "VERSION bumped: ${CURRENT_VERSION} → ${NEW_VERSION}"

# 1b. Sync frontend/package.json version
FRONTEND_PKG="frontend/package.json"
if [[ -f "$FRONTEND_PKG" ]]; then
  sed -i "s/\"version\": \"[^\"]*\"/\"version\": \"${NEW_VERSION}\"/" "$FRONTEND_PKG"
  ok "frontend/package.json version synced to ${NEW_VERSION}"
fi


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
      echo "" >> "$TMPFILE"
      echo -e "$CHANGELOG_ENTRY" >> "$TMPFILE"
      echo "" >> "$TMPFILE"
      echo "---" >> "$TMPFILE"
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
git add "$VERSION_FILE" "$CHANGELOG_FILE" "$FRONTEND_PKG"
git commit -m "chore(release): v${NEW_VERSION}

Automated release: ${BUMP_TYPE} bump ${CURRENT_VERSION} → ${NEW_VERSION}"
ok "Changes committed"

# 4. Tag
git tag -a "v${NEW_VERSION}" -m "v${NEW_VERSION}"
ok "Tag v${NEW_VERSION} created"

# 5. Push
info "Pushing to origin..."
git push origin master
git push origin "v${NEW_VERSION}"
ok "Pushed to origin (master + v${NEW_VERSION})"

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
