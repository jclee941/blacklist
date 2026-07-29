# ADR-0002: Enforce Collector Control API Authentication

**Date**: 2026-07-29
**Status**: accepted
**Deciders**: Blacklist maintainers, informed by information-security finding C-05

## Context

Finding C-05 identified that processes able to reach the collector network could invoke collection controls without credentials. The C-04 bridge migration removed host exposure, but an internal-network attacker or compromised sibling container could still drive collection, so authentication is required as defence in depth.

PyJWT is available to the Flask app through `app/requirements.txt`, but it is absent from `collector/requirements.txt`. Adding it would change the air-gapped collector image and offline bundle. The lower-risk mechanism is therefore a dedicated shared bearer token from `COLLECTOR_AUTH_TOKEN`, verified independently inside `collector/` with `hmac.compare_digest`. The secret is read lazily from the environment, is not logged, and has no tracked default value.

The collector exposes six registered routes:

| Collector route | Classification | Authentication policy |
| --- | --- | --- |
| `GET /health` | Read-only liveness, readiness, and collector summary | Open so the Docker health check remains functional. |
| `GET /status` | Read-only collector status | Open. |
| `GET /logs` | Read-only in-memory log retrieval | Open. |
| `POST /trigger` | CONTROL: triggers scheduler collection | Bearer token required. |
| `POST /api/test-auth/<source>` | CONTROL: initiates external source authentication | Bearer token required. |
| `POST /api/force-collection/<source>` | CONTROL: forces scheduler collection | Bearer token required. |

`collector/core/control_auth.py` owns the collector-side policy and does not import from `app/`. `app/core/config.py` constructs the service credential lazily, and every direct app-side collector request uses those request arguments. Missing collector credentials fail closed when enforcement is enabled; `DISABLE_JWT_AUTH=true` remains an explicit operational escape hatch.

## Decision

Decision: enforce

Set the collector's rendered `DISABLE_JWT_AUTH` value to `"false"` and provide the same `COLLECTOR_AUTH_TOKEN` environment value to the app and collector containers. Reject missing, malformed, or incorrect bearer credentials on all three control routes with HTTP 401 and the non-revealing body `{"error":"Unauthorized"}`. Keep the three read-only routes unauthenticated.

## Consequences

- C-05 control-route authentication is active when the deployment supplies `COLLECTOR_AUTH_TOKEN`; the bridge network remains a separate defence-in-depth boundary.
- An enabled collector with a missing shared token rejects every control request, while `/health`, `/status`, and `/logs` remain available.
- The escape hatch intentionally restores unauthenticated control access and must only be used as a time-bounded emergency measure.
- The app and collector must receive exactly the same generated secret. The installer must generate and persist `COLLECTOR_AUTH_TOKEN` before this enforcement posture is deployed.

## Follow-up

1. Generate `COLLECTOR_AUTH_TOKEN` in `deploy/install.sh` with the other target-local secrets; do not distribute a value in the bundle.
2. Reconcile the pre-existing app calls to unregistered `/api/scheduler/restart` and `/api/data` collector routes separately; authentication does not create those routes.
3. Reassess JWT only if the collector later acquires PyJWT for another justified offline-image requirement. The shared bearer mechanism avoids that dependency today.
