# FORTINET API KNOWLEDGE BASE

## OVERVIEW

Fortinet integration API. Threat feed export + device/log operations.

## FILES

| File             | Role                                         |
| ---------------- | -------------------------------------------- |
| `core.py`        | IP export + EBL format generation            |
| `threat_feed.py` | threat-feed + JSON connector (`@public`, admin-JWT exempt, gated by `feed_access_required`) |
| `management.py`  | device list/push operations                  |
| `logs.py`        | session/pull-log endpoints                   |
| `utils.py`       | shared helpers                               |
| `__init__.py`    | blueprint registration + health              |

## FEED ENDPOINTS (exempt from admin JWT, not fully open)

- `/api/fortinet/threat-feed` and `/api/fortinet/json-connector` carry `@public` (skips the global admin-JWT hook) plus `@feed_access_required` (`core/auth/feed.py`), which enforces a bearer feed token and a source-network check. They are not unauthenticated.
- Every other Fortinet route (`core.py`, `management.py`, `logs.py`) goes through the default admin-JWT enforcement.

## ANTI-PATTERNS

- Changing `threat_feed.py` response format without verifying FortiGate connector compatibility.
- Replacing `feed_access_required` with the admin-JWT hook; FortiGate polling requires the feed-specific token/network contract.

## NOTES

- `threat_feed.py` is compatibility-sensitive — FortiGate connector depends on exact response format.
- EBL (External Block List) format follows Fortinet specification.


## CODE MAP

| Symbol | Type | Location | Refs | Role |
| --- | --- | --- | --- | --- |
| `register_fortinet_routes` | function | `__init__.py` | high | 4 blueprint + health endpoint |
| `fortinet_core_bp` | Blueprint | `core.py` | high | active IPs + blocklist + config |
| `fortinet_feed_bp` | Blueprint | `threat_feed.py` | high | feed-authenticated threat-feed + JSON connector |
| `fortinet_management_bp` | Blueprint | `management.py` | med | device list + FortiGate push |
| `fortinet_logs_bp` | Blueprint | `logs.py` | med | active sessions + pull logs |
