# FORTINET API KNOWLEDGE BASE

**Generated:** 2026-02-22 21:55 Asia/Seoul
**Commit:** 6c134bd
**Branch:** master | **Version:** 3.6.3

## OVERVIEW

Fortinet integration API. Threat feed export + device/log operations.

## FILES

| File             | Role                                         |
| ---------------- | -------------------------------------------- |
| `core.py`        | IP export + EBL format generation            |
| `threat_feed.py` | JSON connector endpoint (**public**, no JWT) |
| `management.py`  | device list/push operations                  |
| `logs.py`        | session/pull-log endpoints                   |
| `utils.py`       | shared helpers                               |
| `__init__.py`    | blueprint registration + health              |

## PUBLIC ENDPOINTS (no JWT required)

- `/api/fortinet/threat-feed`
- `/api/fortinet/json-connector`

## ANTI-PATTERNS

- Changing `threat_feed.py` response format without verifying FortiGate connector compatibility.
- Adding auth requirements to public endpoints (breaks FortiGate automated polling).

## NOTES

- `threat_feed.py` is compatibility-sensitive — FortiGate connector depends on exact response format.
- EBL (External Block List) format follows Fortinet specification.
