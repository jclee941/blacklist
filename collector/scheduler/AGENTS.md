# SCHEDULER KNOWLEDGE BASE

## OVERVIEW

Collection scheduling package. `manager.py` owns the scheduler loop, the adaptive interval, and the `force_collection` duplicate guard; sibling modules are single-responsibility extractions reached through the `operations.py` facade.

## FILES

| File | Role |
| --- | --- |
| `manager.py` | `CollectionScheduler`: main loop, interval adaptation, `force_collection` duplicate guard (`_active_collections`/`_active_collections_lock`) |
| `operations.py` | facade re-exports with call-time dependency injection (test monkeypatch seam) |
| `manual.py` | `collect_regtech_data` (shared REGTECH trigger for manual + force) and `run_manual_collection` |
| `scheduled.py` | scheduled daily/adaptive collection runs, 1-day window |
| `cleanup.py` | midnight stale-IP eviction (expired `removal_date`) |
| `stats.py` | startup stats load into scheduler state |
| `operation_support.py` | shared save-result normalization + elapsed-time helpers |
| `dependencies.py` | lazy import helper (package / `PYTHONPATH=collector` / Docker `/app` layouts) |

## COLLECTION PATHS AND PAGE LIMITS

- Scheduled/daily (`scheduled.py`): `max_pages=1`, ~1-day window, driven by the `schedule` loop in `manager.py`.
- Manual (`trigger_manual_collection` → `run_manual_collection`): `max_pages=CollectorConfig.MAX_PAGES_PER_COLLECTION` (default 20), ~90-day window. Starts a bare thread — it does NOT go through the duplicate guard below.
- Force (`force_collection`, `POST /api/force-collection/<source>`): same `MAX_PAGES_PER_COLLECTION` bound as manual, but wrapped in `_active_collections_lock`/`_active_collections` — a second force request for a source already running is rejected instead of racing.

## CONVENTIONS

- The force-collection duplicate guard lives in `manager.py` — new per-source entry points must reuse it, not bypass it.
- Facade functions exist for dependency injection at call time; keep them pass-through.

## ANTI-PATTERNS

- Bypassing `_active_collections_lock` to "force" a run — duplicate collectors corrupt history.
- Assuming manual collection is unbounded — it shares the same `MAX_PAGES_PER_COLLECTION` cap as force.
- Importing scheduler modules from `app/` (collector isolation).
