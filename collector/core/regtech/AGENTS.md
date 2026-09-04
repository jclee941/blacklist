# REGTECH KNOWLEDGE BASE

## OVERVIEW

REGTECH (regtech.fsec.or.kr) collection pipeline. Mixin composition on `RegtechCollector`; page and Excel fetching run through `core/bounded_process.py` via curl subprocess, through the shared rate limiter.

## FILES

| File                 | Role                                                                                  |
| -------------------- | ------------------------------------------------------------------------------------- |
| `collector.py`       | orchestration: pagination loop, retry attempts, WAF circuit breaker                   |
| `auth.py`            | session auth (findMember → addLogin → Korean success text), JWT validity, auth cache  |
| `page_collection.py` | curl page fetch: `-sS --max-time --max-filesize`, `_last_failure_kind` classification |
| `data_processor.py`  | dedupe, post-processing, confidence scoring                                           |
| `normalization.py`   | IP validation, private-IP filtering, date parsing (`_parse_date` → `str \| None`)     |
| `html_parsing.py`    | HTML table parsing, country extraction                                                |
| `date_strategies.py` | collection date-window strategies (전체/사용자 지정/최근 1일/최근 3개월)              |
| `errors.py`          | `RegtechPageCollectionError`, `RegtechCollectionBlockedError`, `_env_int`             |

## WAF HARDENING

The remote WAF quota-bans IPs for fast paging (empty bodies → blackhole). Current defenses — do not remove:

- Pacing: `REGTECH_RATE_INITIAL/MIN/MAX/BURST` (defaults 0.2/0.1/0.5/1) in `core/rate_limiter.py`.
- Circuit breaker: `REGTECH_BLOCK_THRESHOLD` (default 3) consecutive `block_suspect` signals (empty body, 403/429, table-less HTML) → `RegtechCollectionBlockedError`, run aborts for cooldown.
- Failure kinds: `block_suspect` vs `http_error` vs `curl_error` drive the breaker; success resets.
- Download size bound: page uses `run_text_bounded`, Excel uses `run_bounded`, and page curl additionally passes `--max-filesize`. Both paths cap output at `CollectorConfig.MAX_DOWNLOAD_BYTES` (default 10 MiB); oversized output kills the subprocess.

## AUTH CACHE

- Structure: `{auth_key: (timestamp, is_valid)}`, TTL 3600s with 5min margin.
- Non-deterministic auth causes duplicate-login lockouts — keep flow deterministic.

## ANTI-PATTERNS

- Skipping auth cache validation (forces re-auth).
- Raising request rate to "finish faster" — this is what got the egress IP banned.
