# SCRIPTS KNOWLEDGE BASE

## OVERVIEW

Release and offline-bundle automation. Entry points: `release.sh` (versioned release) and `build_offline_bundle.py` (air-gapped package).

## FILES

| File                               | Role                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| ---------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `release.sh`                       | release entry (`scripts/release.sh $TYPE $DRY_RUN`, invoked by `make release`/`make release-dry`): clean-`master` + exact-HEAD CI check via `gh run list` against the remote `CI` workflow run for `HEAD_SHA` — requires an authenticated `gh` CLI and a `success` conclusion, with no local/offline fallback; then bumps `VERSION`/`CHANGELOG.md`/`frontend/package.json`+`package-lock.json`, commits, creates an annotated `v<version>` tag, and pushes |
| `build_offline_bundle.py`          | local bundle build: `--build` (rebuild all images), `--skip-images`, `--output`                                                                                                                                                                                                                                                                                                                                                                            |
| `offline_bundle/assembly.py`       | copies compose/installer/docs (guides + screenshots + PDFs) + bind-mount assets, fail-closed on missing                                                                                                                                                                                                                                                                                                                                                    |
| `offline_bundle/images.py`         | per-service docker build (`blacklist-<svc>:<version>`) and `docker save` export                                                                                                                                                                                                                                                                                                                                                                            |
| `offline_bundle/integrity.py`      | version resolution, manifest/checksum writing, packing                                                                                                                                                                                                                                                                                                                                                                                                     |
| `migrate_env_credentials_to_db.py` | one-off credential migration utility                                                                                                                                                                                                                                                                                                                                                                                                                       |

`make release` defaults `TYPE=patch` (Makefile); `release.sh` itself defaults to `auto` (reuse current `VERSION`/existing CHANGELOG entry) when invoked directly with no argument — always go through `make release[-dry] TYPE=...` to get the patch default. Valid `TYPE` values: `auto`, `patch`, `minor`, `major`, `current`.

## CONVENTIONS

- Bundle image tags always equal `VERSION`; `export_images` fails if a tagged image is missing locally.
- `OPERATOR_DOCUMENTS` in `assembly.py` is the bundle doc contract — every entry must exist or packaging aborts.
- Bundle docs live in `docs/manual/`; guide screenshots regenerate via `frontend/e2e/helpers/capture-guide-screenshots.mjs`.

## ANTI-PATTERNS

- Releasing outside `scripts/release.sh` (version/changelog drift).
- Editing bundle contents after `pack` — rebuild instead.
- Duplicating `.github/workflows/release.yml` gate/sign/publish logic here — `release.sh` only prepares and tags `master`; see `.github/AGENTS.md` for what the tag push triggers.
