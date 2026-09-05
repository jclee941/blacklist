# Operator Credential Migration Guide

**Version:** repository root `VERSION`<br>
**Updated:** September 2026<br>
**Audience:** system operators and DevOps engineers

## Scope

Blacklist stores REGTECH collection credentials in PostgreSQL. The dashboard is the supported management surface. Legacy `REGTECH_ID` and `REGTECH_PW` values must not remain in tracked files, shell history, command arguments, or logs.

The externally supported endpoint is the frontend HTTPS listener on port `443`. Flask (`2542`), Collector (`8545`), PostgreSQL (`5432`), and Redis (`6379`) are internal service listeners and must not be exposed for credential migration.

## Before Migration

- Back up PostgreSQL through the deployment's approved backup procedure.
- Confirm `CREDENTIAL_MASTER_KEY` and `ENCRYPTION_SALT` are supplied from the deployment secret store.
- Keep the existing REGTECH credential in a password manager. Do not print it or copy it into a command line.
- Start the supported Compose stack with `make dev` for development or the packaged installer for production.

## Migration

1. Open `https://<blacklist-host>/login` and sign in as an administrator.
2. Open **수집 관리** (`/collection`).
3. Edit the REGTECH collector, enter the username and password, choose the collection interval, and save.
4. Select **연결 테스트**. The dashboard must report a successful REGTECH connection.
5. Select **수집 실행** and wait for a successful collection history entry.
6. Remove legacy `REGTECH_ID` and `REGTECH_PW` values from deployment configuration and restart the stack.
7. Repeat the connection test and one collection after the restart. This proves PostgreSQL is the active credential source.

Password values are encrypted before storage and are never returned by the API. Updating only settings leaves the existing password unchanged; creating a new credential requires a password.

## Verification

Use only the frontend endpoint and service logs:

```bash
curl --fail --insecure https://localhost/health
docker compose logs --since=10m blacklist-collector
```

Verify all of the following in the dashboard:

- REGTECH shows **configured** and **enabled**.
- The connection test succeeds.
- The latest collection history entry succeeds and has a non-zero result count when upstream data is available.
- No credential value appears in application or collector logs.

## Troubleshooting

### Credential is not configured

Return to **수집 관리**, save both username and password, and retry the connection test. Do not fall back to environment-variable credentials.

### Decryption fails after restart

Restore the same `CREDENTIAL_MASTER_KEY` and `ENCRYPTION_SALT` used when the credential was saved. If either value is permanently lost, delete and recreate the credential through the dashboard using values retrieved from the password manager.

### Collection cannot reach REGTECH

Check Collector logs and the WARP deployment mode. WARP is supported only by the development overlay; production bundles keep it disabled. Confirm normal production egress rather than enabling the development proxy in production.

### Rollback

Restore the pre-migration database backup and the matching application version. Do not restore plaintext credentials to tracked configuration. If the older release requires environment credentials, inject them from the deployment secret store only for the rollback window and remove them after recovery.

## Security

Never include credentials, tokens, internal addresses, database dumps, or log excerpts containing sensitive values in a public issue. Report an active vulnerability through the private channel documented in [`SECURITY.md`](../SECURITY.md).
