# SCRIPTS KNOWLEDGE BASE

**Version:** 5.0.0

## OVERVIEW

Release and offline-bundle automation. Entry points: `release.sh` (versioned release) and `build_offline_bundle.py` (air-gapped package).

## FILES

| File | Role |
| --- | --- |
| `release.sh` | release entry: clean-master check, VERSION/CHANGELOG/package.json bump, annotated tag, push |
| `build_offline_bundle.py` | local bundle build: `--build` (rebuild all images), `--skip-images`, `--output` |
| `offline_bundle/assembly.py` | copies compose/installer/docs (guides + screenshots + PDFs) + bind-mount assets, fail-closed on missing |
| `offline_bundle/images.py` | per-service docker build (`blacklist-<svc>:<version>`) and `docker save` export |
| `offline_bundle/integrity.py` | version resolution, manifest/checksum writing, packing |
| `migrate_env_credentials_to_db.py` | one-off credential migration utility |

## CONVENTIONS

- Bundle image tags always equal `VERSION`; `export_images` fails if a tagged image is missing locally.
- `OPERATOR_DOCUMENTS` in `assembly.py` is the bundle doc contract — every entry must exist or packaging aborts.
- Bundle docs live in `docs/manual/`; guide screenshots regenerate via `frontend/e2e/helpers/capture-guide-screenshots.mjs`.

## ANTI-PATTERNS

- Releasing outside `scripts/release.sh` (version/changelog drift).
- Editing bundle contents after `pack` — rebuild instead.
