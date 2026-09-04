# DOCS KNOWLEDGE BASE

## OVERVIEW

Operator documentation. `manual/` is the current truth; `wiki/` and `deliverables/` are historical records.

## CURRENT (docs/manual/)

| Document | Audience |
| --- | --- |
| `blacklist-user-guide.md` / `.pdf` | end users: login, dashboard, IP lookup, analytics |
| `blacklist-admin-guide.md` / `.pdf` | operators: collection management, pacing/WAF response, integrations, backup |
| `blacklist-offline-installation-guide.md` | air-gapped install |
| `blacklist-offline-package-guide.md` | bundle layout (also bundle README) |
| `blacklist-operations-guide.md` | day-2 operations |
| `blacklist-<version>-release-notes.md` | per-release notes; current file must match root `VERSION` |
| `blacklist-release-signing-key-v1.asc` / `.fingerprint` | release signing public key and fingerprint |
| `security-remediation-*.md` | remediation review, checklist, and validation reports |
| `screenshots/` | guide images, regenerated from the live dashboard |

## DECISIONS

- `decisions/0002-collector-authentication-enforcement.md` records the Collector control-route authentication decision and amendments.
- Numbering is archival; no `0001` file is currently tracked.
- Keep unresolved follow-ups explicit instead of describing unregistered routes as implemented.

## RULES

- Guide screenshots regenerate via `frontend/e2e/helpers/capture-guide-screenshots.mjs` against a running stack.
- Guide PDFs regenerate with `make docs-pdf` using pandoc + xelatex and the NanumGothic font family.
- `wiki/` and `deliverables/` are records, not operational truth — preserve; correct only on explicit request.

## GENERATED ASSETS

- Treat markdown as the editable source for current guides and release notes.
- Regenerate PDFs rather than patching binary output by hand.
- Keep release signing public material tracked; private signing keys stay in 1Password/GitHub environment secrets.
