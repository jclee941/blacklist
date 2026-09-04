# FORTINET API KNOWLEDGE BASE

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


## CODE MAP

| Symbol | Type | Location | Refs | Role |
| --- | --- | --- | --- | --- |
| `register_fortinet_routes` | function | `__init__.py:16` | high | 4 blueprint + health endpoint |
| `fortinet_core_bp` | Blueprint | `core.py:15` | high | active IPs + blocklist + config |
| `fortinet_feed_bp` | Blueprint | `threat_feed.py:14` | high | public threat-feed + JSON connector |
| `fortinet_management_bp` | Blueprint | `management.py:15` | med | device list + FortiGate push |
| `fortinet_logs_bp` | Blueprint | `logs.py:13` | med | active sessions + pull logs |
