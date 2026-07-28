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


def read(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def main() -> None:
    ci = read(".github/workflows/ci.yml")
    build_images = read(".github/workflows/build-images.yml")
    release = read(".github/workflows/release.yml")
    release_script = read("scripts/release.sh")
    ci_compose = read(".github/docker-compose.ci.yml")
    frontend_dockerfile = read("frontend/Dockerfile")
    reusable_node = read(".github/workflows/_ci-node.yml")

    failures = [
        message
        for condition, message in (
            ("contents: read\n      packages: write" in build_images, "build-images lacks contents: read"),
            ("collector/|tests/unit/collector/" in ci, "collector test changes are not detected"),
            ("contents: read\n  packages: write" not in ci, "CI grants package write globally"),
            ("node-version: \"24\"" in ci, "CI frontend lint does not use Node 24"),
            ("node-version: 24" in ci, "CI frontend test or E2E does not use Node 24"),
            ("default: \"24\"" in reusable_node, "reusable Node workflow does not default to Node 24"),
            ("contents: read\n      packages: write" in ci, "image publishing lacks contents: read"),
            ("context: ./deploy/redis" in ci, "CI Redis build context is invalid"),
            ("API_URL: https://localhost:3443" in ci, "E2E API calls bypass the frontend proxy"),
            ("BASE_URL: https://localhost:3443" in ci, "E2E browser target bypasses the frontend proxy"),
            ("E2E_USERNAME: admin" in ci, "CI does not provide the E2E username"),
            ("E2E_PASSWORD: blacklist-dev-password" in ci, "CI does not provide the E2E password"),
            ("ports:\n      - \"3443:443\"" in ci_compose, "CI frontend is not exposed on the proxy port"),
            ("ADMIN_USERNAME: admin" in ci_compose, "CI app username does not match E2E credentials"),
            ("ADMIN_PASSWORD: blacklist-dev-password" in ci_compose, "CI app password does not match E2E credentials"),
            ("FROM node:24-alpine AS builder" in frontend_dockerfile, "frontend build image does not use Node 24"),
            ("FROM node:24-alpine AS runner" in frontend_dockerfile, "frontend runtime image does not use Node 24"),
            ("RELEASE_NOTES_FILE=" in release_script, "release script does not define its release note asset"),
            ("Release notes file not found" in release_script, "release script does not validate release notes"),
            ("Release notes file not found" in release, "release workflow does not validate release notes"),
        )
        if not condition
    ]

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
