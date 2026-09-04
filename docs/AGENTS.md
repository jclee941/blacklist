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
| `security-remediation-*` | remediation review, checklist, validation report (`.md` and `.html`) |
| `screenshots/` | guide images, regenerated from the live dashboard |

## RULES

- Guide screenshots regenerate via `frontend/e2e/helpers/capture-guide-screenshots.mjs` against a running stack.
- Guide PDFs regenerate with pandoc + xelatex (`NanumGothic`); see git history for the exact invocation.
- `wiki/` and `deliverables/` are records, not operational truth — preserve; correct only on explicit request.
