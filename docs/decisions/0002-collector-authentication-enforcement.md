# ADR-0002: Enforce Collector Control API Authentication

**Date**: 2026-07-29
**Amended**: 2026-09-04 — route classification and escape-hatch scope corrected; see Amendment below.
**Status**: accepted
**Deciders**: Blacklist maintainers, informed by information-security finding C-05

## Context

Finding C-05 identified that processes able to reach the collector network could invoke collection controls without credentials. The C-04 bridge migration removed host exposure, but an internal-network attacker or compromised sibling container could still drive collection, so authentication is required as defence in depth.

PyJWT is available to the Flask app through `app/requirements.txt`, but it is absent from `collector/requirements.txt`. Adding it would change the air-gapped collector image and offline bundle. The lower-risk mechanism is therefore a dedicated shared bearer token from `COLLECTOR_AUTH_TOKEN`, verified independently inside `collector/` with `hmac.compare_digest`. The secret is read lazily from the environment, is not logged, and has no tracked default value.

The collector exposes six registered routes:

| Collector route                       | Classification                                    | Authentication policy                                                    |
| ------------------------------------- | ------------------------------------------------- | ------------------------------------------------------------------------ |
| `GET /health`                         | Read-only liveness and readiness                  | Open so the Docker health check remains functional.                      |
| `GET /status`                         | Read-only collector status                        | Bearer token required (reclassified as a control route — see Amendment). |
| `GET /logs`                           | Read-only in-memory log retrieval                 | Bearer token required (reclassified as a control route — see Amendment). |
| `POST /trigger`                       | CONTROL: triggers scheduler collection            | Bearer token required.                                                   |
| `POST /api/test-auth/<source>`        | CONTROL: initiates external source authentication | Bearer token required.                                                   |
| `POST /api/force-collection/<source>` | CONTROL: forces scheduler collection              | Bearer token required.                                                   |

`collector/core/control_auth.py` owns the collector-side policy and does not import from `app/`. `app/core/config.py` constructs the service credential lazily, and every direct app-side collector request uses those request arguments. Missing collector credentials fail closed when enforcement is enabled. `DISABLE_JWT_AUTH=true` is not a production escape hatch: `require_control_authentication` only honors it when `ENVIRONMENT=development` or `TESTING=true` (see Amendment).

## Decision

Decision: enforce

Set the collector's rendered `DISABLE_JWT_AUTH` value to `"false"` and provide the same `COLLECTOR_AUTH_TOKEN` environment value to the app and collector containers. Reject missing, malformed, or incorrect bearer credentials on all five control routes (`/status`, `/logs`, `/trigger`, `/api/test-auth/<source>`, `/api/force-collection/<source>`) with HTTP 401 and the non-revealing body `{"error":"Unauthorized"}`. Keep only `GET /health` unauthenticated.

## Consequences

- C-05 control-route authentication is active when the deployment supplies `COLLECTOR_AUTH_TOKEN`; the bridge network remains a separate defence-in-depth boundary.
- An enabled collector with a missing shared token rejects every control request, while `/health` remains available.
- There is no production escape hatch: `core/control_auth.py` only bypasses control-route authentication when `authentication_disabled` (`DISABLE_JWT_AUTH=true`) AND (`ENVIRONMENT=development` OR `TESTING=true`). Setting `DISABLE_JWT_AUTH=true` in a production deployment has no effect — control routes stay enforced.
- The app and collector must receive exactly the same generated secret. The installer must generate and persist `COLLECTOR_AUTH_TOKEN` before this enforcement posture is deployed.

## Follow-up

1. Generate `COLLECTOR_AUTH_TOKEN` in `deploy/install.sh` with the other target-local secrets; do not distribute a value in the bundle.
2. The former `/api/scheduler/restart` app call was removed. Reconcile the remaining app call to the unregistered collector `/api/data` route separately; authentication does not create that route.
3. Reassess JWT only if the collector later acquires PyJWT for another justified offline-image requirement. The shared bearer mechanism avoids that dependency today.

## Amendment (2026-09-04)

Source review found two drifts from this record's original text, both now corrected above:

1. **Route classification.** `GET /status` and `GET /logs` are control routes requiring the bearer token, not open read-only routes — `collector/core/control_auth.py`'s `CONTROL_ROUTES` set includes `/logs`, `/status`, `/trigger`, `/api/test-auth/<source>`, and `/api/force-collection/<source>`. Only `GET /health` is open.
2. **Escape hatch scope.** The original text described `DISABLE_JWT_AUTH=true` as a general "time-bounded emergency measure," implying production use. The enforced behavior is narrower and code-gated: `require_control_authentication` only bypasses authentication when `DISABLE_JWT_AUTH=true` **and** (`ENVIRONMENT=development` **or** `TESTING=true`). A production deployment (any other `ENVIRONMENT` value, `TESTING` unset) cannot disable control-route authentication regardless of `DISABLE_JWT_AUTH`. The escape hatch is forbidden in production, full stop — not merely discouraged.
