# REGTECH KNOWLEDGE BASE

**Generated:** 2026-02-26 00:00 Asia/Seoul
**Commit:** 803209d
**Branch:** master | **Version:** 3.6.4

## OVERVIEW

REGTECH collector package. Auth + collection + data processing via mixin composition.

## FILES

| File                | LOC | Role                                                              |
| ------------------- | --- | ----------------------------------------------------------------- |
| `collector.py`      | 414 | orchestration, main collection loop                               |
| `auth.py`           | 138 | session auth, JWT validity, auth cache                            |
| `data_processor.py` | 331 | parsing, dedupe, normalization, confidence scoring, date handling |

## AUTH CACHE

- Structure: `{auth_key: (timestamp, is_valid)}`
- TTL: 3600s with 5min safety margin.
- Auth flow: `findMember` → `addLogin` → detect success via Korean text.

## ANTI-PATTERNS

- Non-deterministic auth behavior — causes duplicate-login lockouts.
- Skipping auth cache validation (forces unnecessary re-auth).
- Modifying auth flow without testing lockout recovery.

## NOTES

- Composition via mixins (not inheritance).
- Separate from `app/core/services/collection/` (app-side service layer).


## CODE MAP

| Symbol | Type | Location | Refs | Role |
| --- | --- | --- | --- | --- |
| `RegtechCollector` | class | `collector.py:36` | high | orchestration, main collection loop (414L) |
| `RegtechAuth` | class | `auth.py:*` | high | session auth, JWT validity, auth cache (138L) |
| `RegtechDataProcessor` | class | `data_processor.py:*` | high | parsing + dedupe + confidence scoring (331L) |