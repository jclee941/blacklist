#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# ///
# ─── How to run ───
# uv run .github/scripts/validate_automation_contracts.py
from __future__ import annotations

import re
from pathlib import Path
from typing import Final


ROOT: Final = Path(__file__).resolve().parents[2]
WORKFLOWS: Final = ROOT / ".github" / "workflows"
MUTABLE_ACTION_REF: Final = re.compile(r"^\s*-?\s*uses:\s+[^\s]+@(v|main|master|latest)", re.MULTILINE)
RELEASE_JOB_PERMISSIONS: Final = {
    "validate": "    permissions:\n      contents: read",
    "build-images": "    permissions:\n      contents: read",
    "package": "    permissions:\n      contents: read",
    "create-release": "    permissions:\n      contents: write",
    "push-to-registry": "    permissions:\n      packages: write",
    "notify": "    permissions: {}",
}
PRIMARY_CI_WORKFLOW: Final = "CI"
RELEASE_SETUP_PYTHON_ACTION: Final = (
    "actions/setup-python@5fda3b95a4ea91299a34e894583c3862153e4b97 # v7.0.0"
)
CI_E2E_COMPOSE_COMMAND: Final = (
    'docker compose --env-file "$CI_ENV_FILE" -f deploy/base.yml -f .github/docker-compose.ci.yml'
)
POSTGRES_GOSU_FALSE_POSITIVE_SKIP: Final = (
    "skip-files: ${{ matrix.service == 'postgres' && 'usr/local/bin/gosu' || '' }}"
)


def read(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def job_body(workflow: str, job_name: str) -> str:
    job = re.search(
        rf"^  {re.escape(job_name)}:\n(?P<body>.*?)(?=^  [A-Za-z0-9_-]+:|\Z)",
        workflow,
        re.MULTILINE | re.DOTALL,
    )
    return job.group("body") if job else ""


def main() -> None:
    ci = read(".github/workflows/ci.yml")
    build_images = read(".github/workflows/build-images.yml")
    release = read(".github/workflows/release.yml")
    release_script = read("scripts/release.sh")
    ci_compose = read(".github/docker-compose.ci.yml")
    frontend_dockerfile = read("frontend/Dockerfile")
    guide_capture = read("frontend/e2e/helpers/capture-guide-screenshots.mjs")
    reusable_node = read(".github/workflows/_ci-node.yml")
    dependabot = read(".github/dependabot.yml")
    gitignore = read(".gitignore")

    failures = [
        message
        for condition, message in (
            ("contents: read" in build_images, "build-images lacks contents: read"),
            ("packages: write" not in build_images, "build-images can publish packages directly"),
            ("inputs.push" not in build_images, "build-images exposes a direct publish input"),
            ("push: false" in build_images, "build-images is not artifact-only"),
            ("collector/|tests/unit/collector/" in ci, "collector test changes are not detected"),
            ("contents: read\n  packages: write" not in ci, "CI grants package write globally"),
            ('node-version: "24"' in ci, "CI frontend lint does not use Node 24"),
            ("node-version: 24" in ci, "CI frontend test or E2E does not use Node 24"),
            ('default: "24"' in reusable_node, "reusable Node workflow does not default to Node 24"),
            ("contents: read\n      packages: write" in ci, "image publishing lacks contents: read"),
            ("dockerfile: deploy/redis/Dockerfile" in ci, "CI Redis Dockerfile path is invalid"),
            ("API_URL: https://localhost:3443" in ci, "E2E API calls bypass the frontend proxy"),
            ("BASE_URL: https://localhost:3443" in ci, "E2E browser target bypasses the frontend proxy"),
            ("E2E_USERNAME: ${{ env.E2E_USERNAME }}" in ci, "CI does not provide the E2E username"),
            ("E2E_PASSWORD: ${{ env.E2E_PASSWORD }}" in ci, "CI does not provide the E2E password"),
            (
                CI_E2E_COMPOSE_COMMAND in ci,
                "CI E2E does not compose deploy/base.yml with the CI override",
            ),
            (
                "BLACKLIST_TLS_DIR=$RUNNER_TEMP/blacklist-ci-tls" in ci,
                "CI E2E stack does not set BLACKLIST_TLS_DIR",
            ),
            (
                "    timeout-minutes: 60" in job_body(ci, "e2e"),
                "CI E2E timeout is too short for the full browser matrix",
            ),
            (
                POSTGRES_GOSU_FALSE_POSITIVE_SKIP in job_body(ci, "scan-images"),
                "CI Trivy scan does not apply the verified PostgreSQL gosu false-positive exclusion",
            ),
            (
                '          if [ "$result" = "failure" ] || [ "$result" = "cancelled" ]; then'
                in job_body(ci, "ci-gate"),
                "CI gate does not fail when a required job is cancelled",
            ),
            ('ports: !override\n      - "3443:3000"' in ci_compose, "CI frontend is not exposed on the proxy port"),
            ("ADMIN_USERNAME:" not in ci_compose, "CI compose overrides the generated app username"),
            ("ADMIN_PASSWORD:" not in ci_compose, "CI compose overrides the generated app password"),
            (
                all(
                    required in ci_compose
                    for required in (
                        "  blacklist-postgres:",
                        "  blacklist-redis:",
                        "image: blacklist-postgres:ci",
                        "image: blacklist-redis:ci",
                    )
                )
                and "\n  postgres:" not in ci_compose
                and "\n  redis:" not in ci_compose
                and "image: postgres:" not in ci_compose
                and "image: redis:" not in ci_compose,
                "CI compose duplicates PostgreSQL or Redis instead of overriding deployment services",
            ),
            ("FROM node:24-alpine AS builder" in frontend_dockerfile, "frontend build image does not use Node 24"),
            ("FROM node:24-alpine AS runner" in frontend_dockerfile, "frontend runtime image does not use Node 24"),
            (
                "const username = process.env.E2E_USERNAME;" in guide_capture,
                "guide screenshot capture does not require the E2E username from the environment",
            ),
            (
                "const password = process.env.E2E_PASSWORD;" in guide_capture,
                "guide screenshot capture does not require the E2E password from the environment",
            ),
            (
                "scripts/build_offline_bundle.py" in release,
                "release packaging does not use the bundle builder, so it can drift from what install.sh requires",
            ),
            (
                RELEASE_SETUP_PYTHON_ACTION in release,
                "release packaging does not use the approved setup-python action",
            ),
            (
                "sha256sum -- ./*.tar.gz > checksums.sha256" not in release,
                "release still hand-rolls the bundle instead of using the builder",
            ),
            ("RELEASE_NOTES_FILE=" in release_script, "release script does not define its release note asset"),
            ("Release notes file not found" in release_script, "release script does not validate release notes"),
            (
                "!docs/manual/\ndocs/manual/*\n!docs/manual/blacklist-*-release-notes.md" in gitignore,
                "release notes remain ignored by .gitignore",
            ),
            (
                'git ls-files --error-unmatch "$RELEASE_NOTES_FILE"' in release_script,
                "release script does not require tracked release notes",
            ),
            (
                'git add "$VERSION_FILE" "$CHANGELOG_FILE" "$FRONTEND_PKG" "$FRONTEND_LOCK" "$RELEASE_NOTES_FILE"' in release_script,
                "release script does not stage release notes",
            ),
            (
                'current) NEW_VERSION="$CURRENT_VERSION" ;;' in release_script,
                "release script cannot tag the current VERSION",
            ),
            (
                'if [[ "$BUMP_TYPE" != "current" && "$BUMP_TYPE" != "auto" ]]; then' in release_script,
                "current-version release does not skip duplicate metadata changes",
            ),
            (
                'auto) NEW_VERSION="$CURRENT_VERSION" ;;' in release_script,
                "release script does not select the VERSION file automatically",
            ),
            (
                "docker compose exec -T blacklist-app test -d /app/tests" in release_script,
                "release script treats production images without tests as failed test runs",
            ),
            (
                f'CI_WORKFLOW="{PRIMARY_CI_WORKFLOW}"' in release_script,
                "release script does not select the primary CI workflow",
            ),
            (
                'gh run list --workflow "$CI_WORKFLOW" --commit "$HEAD_SHA"' in release_script,
                "release script does not limit remote verification to the primary CI workflow",
            ),
            (
                all(
                    "github.event_name == 'push'" in job_body(release, job_name)
                    and "startsWith(github.ref, 'refs/tags/')" in job_body(release, job_name)
                    and "!inputs.dry_run" in job_body(release, job_name)
                    and "needs.release-gate.result == 'success'" in job_body(release, job_name)
                    for job_name in ("create-release", "push-to-registry")
                ),
                "release workflow publication jobs are not restricted to tag-triggered non-dry runs",
            ),
            ("Release notes file not found" in release, "release workflow does not validate release notes"),
            (
                'if [[ ! -s "$RELEASE_NOTES_FILE" ]]; then' in release,
                "release workflow does not reject empty release notes",
            ),
            (
                '  - package-ecosystem: "npm"\n    directory: "/frontend"' in dependabot,
                "Dependabot npm directory does not point to /frontend",
            ),
        )
        if not condition
    ]
    failures.extend(
        f"release workflow job '{job_name}' lacks explicit least-privilege permissions"
        for job_name, permissions in RELEASE_JOB_PERMISSIONS.items()
        if permissions not in job_body(release, job_name)
    )

    mutable_files = [
        workflow.relative_to(ROOT).as_posix()
        for workflow in WORKFLOWS.glob("*.yml")
        if MUTABLE_ACTION_REF.search(workflow.read_text(encoding="utf-8"))
    ]
    failures.extend(f"mutable action reference in {workflow}" for workflow in mutable_files)

    if failures:
        raise SystemExit("\n".join(f"ERROR: {failure}" for failure in failures))


if __name__ == "__main__":
    main()
