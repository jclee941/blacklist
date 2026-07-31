# SCHEDULER KNOWLEDGE BASE

**Version:** 5.0.0

## OVERVIEW

Collection scheduling package. `manager.py` owns the scheduler loop and the in-progress lock; sibling modules are single-responsibility extractions reached through the `operations.py` facade.

## FILES

| File | Role |
| --- | --- |
| `manager.py` | `CollectionScheduler`: main loop, interval adaptation, in-progress/duplicate guard |
| `operations.py` | facade re-exports with call-time dependency injection (test monkeypatch seam) |
| `manual.py` | manual trigger path (`run_manual_collection`, unbounded `max_pages=None`) |
| `scheduled.py` | scheduled daily/adaptive collection runs |
| `cleanup.py` | midnight stale-IP eviction (expired `removal_date`) |
| `stats.py` | startup stats load into scheduler state |
| `operation_support.py` | shared save-result normalization + elapsed-time helpers |
| `dependencies.py` | lazy import helper (package / `PYTHONPATH=collector` / Docker `/app` layouts) |

## CONVENTIONS

- The in-progress lock lives in `manager.py` — new entry points must go through it, not around it.
- Facade functions exist for dependency injection at call time; keep them pass-through.
- Manual runs are always unbounded; scheduled runs honor per-source intervals (300s–3600s adaptive).

## ANTI-PATTERNS

- Bypassing the manager lock to "force" a run — duplicate collectors corrupt history.
- Importing scheduler modules from `app/` (collector isolation).
