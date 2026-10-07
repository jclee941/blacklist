# SCHEDULER KNOWLEDGE BASE

## OVERVIEW

Collection scheduling package. `manager.py` owns the scheduler loop, the adaptive interval, and the `force_collection` duplicate guard; sibling modules are single-responsibility extractions reached through the `operations.py` facade.

## FILES

| File                   | Role                                                                                                                                         |
| ---------------------- | -------------------------------------------------------------------------------------------------------------------------------------------- |
| `manager.py`           | `CollectionScheduler`: main loop, interval adaptation, `force_collection` duplicate guard (`_active_collections`/`_active_collections_lock`) |
| `operations.py`        | facade re-exports with call-time dependency injection (test monkeypatch seam)                                                                |
| `manual.py`            | `collect_regtech_data` (shared REGTECH trigger for manual + force), `collect_regtech_backfill`, and `run_manual_collection`                  |
| `scheduled.py`         | daily 1-day collection (yesterday through today) and separate adaptive 1-day collection helper                                               |
| `cleanup.py`           | midnight stale-IP eviction (expired `removal_date`)                                                                                          |
| `stats.py`             | startup stats load into scheduler state                                                                                                      |
| `operation_support.py` | shared save-result normalization + elapsed-time helpers                                                                                      |
| `dependencies.py`      | lazy import helper (package / `PYTHONPATH=collector` / Docker `/app` layouts)                                                                |

## COLLECTION PATHS AND PAGE LIMITS

- Scheduled/daily (`scheduled.py` `run_daily_collection`, run by `manager.py`'s `_daily_collection` at 02:00): yesterday through today, unbounded (`max_pages=None`), so each run lands a whole day of REGTECH entries; it is separate from the initial backfill below.
- Manual (`trigger_manual_collection` → `run_manual_collection`): `max_pages=CollectorConfig.MAX_PAGES_PER_COLLECTION` (default 20), ~90-day window. Starts a bare thread — it does NOT go through the duplicate guard below.
- Force (`force_collection`, `POST /api/force-collection/<source>`): same `MAX_PAGES_PER_COLLECTION` bound as manual, but wrapped in `_active_collections_lock`/`_active_collections` — a second force request for a source already running is rejected instead of racing.
- Initial backfill (`_initial_collection`, a 60-second `initial`-tagged job registered with the time-based schedules): its state lives in the `collection_status` row `REGTECH_INITIAL` (`config` JSONB: `state` = `in_progress`/`complete`/`skipped`, plus `next_window_end`). With no row yet, a database that already holds any `blacklist_ips` row is marked `skipped`; otherwise, once REGTECH credentials are enabled, it runs `force_collection("REGTECH", backfill=True)` — the same duplicate guard — which calls `manual.collect_regtech_backfill`: the last 90 days newest-first in 7-day windows, each unbounded (`max_pages=None`), saved and recorded in history on its own, checkpointing the next window end. A WAF block ends the run without losing finished windows, and the retry after `INITIAL_COLLECTION_RETRY_SECONDS` (1 hour) resumes at the checkpoint even though data now exists; `complete`/`skipped` cancel the job; a running REGTECH collection defers it to the next check.

## CONVENTIONS

- The force-collection duplicate guard lives in `manager.py` — new per-source entry points must reuse it, not bypass it.
- Facade functions exist for dependency injection at call time; keep them pass-through.

## ANTI-PATTERNS

- Bypassing `_active_collections_lock` to "force" a run — duplicate collectors corrupt history.
- Assuming manual collection is unbounded — it shares the same `MAX_PAGES_PER_COLLECTION` cap as force.
