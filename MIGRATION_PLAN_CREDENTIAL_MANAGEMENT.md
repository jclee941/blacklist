# Credential Management Migration Plan: Env Vars → DB-Only

**Status**: Design Phase  
**Target Version**: 3.6.0  
**Complexity**: High (affects core collection pipeline)  
**Risk Level**: Medium (backward compatibility required)

---

## Executive Summary

Currently, the Blacklist Intelligence Platform stores credentials in **two places**:
1. **Environment variables** (REGTECH_ID, REGTECH_PW, SECUDIUM_ID, SECUDIUM_PW) — HIGH PRIORITY
2. **PostgreSQL `collection_credentials` table** — FALLBACK

This dual-storage creates operational friction: env vars always win, making DB updates invisible to the collector service. **Goal**: Eliminate env var credential storage, manage ALL credentials exclusively through the UI (DB-backed).

---

## Current Architecture (Dual-Storage)

### Priority Logic
\`\`\`
Collector.get_regtech_credentials():
  IF (REGTECH_ID env var AND REGTECH_PW env var exist):
    RETURN (env_id, env_pw)  ← ALWAYS WINS
  ELSE:
    Query collection_credentials table
    Decrypt password field (PBKDF2 + Fernet)
    RETURN (db_username, db_password)
\`\`\`

### Impact of Current Design
- **Problem 1**: Operators cannot update credentials via UI if env vars are set
- **Problem 2**: No audit trail for env var credentials (plain text in .env)
- **Problem 3**: Credential rotation requires container restart
- **Problem 4**: Different code paths (env vs DB) increase complexity

---

## Migration Strategy: Phase-Based Rollout

### Phase 0: Pre-Migration (Week 1)
**Goal**: Prepare environments, create backups, audit current state

- Audit all deployment environments for currently-set env vars
- Verify CREDENTIAL_MASTER_KEY is set everywhere
- Backup all production databases
- Audit collection_credentials table for existing records
- Create rollback playbook document

### Phase 1: Code Changes (Week 2)
**Goal**: Implement DB-only credential getter functions

Key Changes:
1. Remove env var properties from collector/config.py (L31-37, 135-154)
2. Refactor get_regtech_credentials() to ALWAYS query DB
3. Refactor get_secudium_credentials() to ALWAYS query DB
4. Add startup validation: fail if credentials missing
5. Create CredentialNotFoundError and CredentialDecryptionError exception classes
6. Add comprehensive logging for credential operations (audit trail)

### Phase 2: Migration Script (Week 2)
**Goal**: Create CLI tool to migrate existing env var credentials → DB

Location: scripts/migrate_env_credentials_to_db.py
- Extract env var values
- Call SecureCredentialService.save_credentials() with encryption
- Validate encryption/decryption works
- Provide rollback instructions

### Phase 3: Deployment Strategy

Production deployment checklist:
1. Backup production database
2. Deploy updated app and collector services
3. Run migration script to move env var credentials to DB
4. Verify collector reads from DB (check logs)
5. Remove env vars from .env file
6. Restart services
7. Run smoke tests (verify collections work)

Rollback options if issues occur:
- Option 1: Quick rollback with env vars (old credentials still in DB)
- Option 2: Full restore from backup
- Option 3: Hybrid (test on staging first)

---

## Testing Plan

### Unit Tests
- test_credential_not_found_error.py
- test_collector_config_db_only.py
- test_secure_credential_service_encryption.py

### Integration Tests
- App saves credentials to DB, collector reads them
- Collector fails gracefully if credentials missing
- Migration script properly encrypts credentials
- Backward compatibility with existing encrypted data

### E2E Tests
- User can add credentials via UI
- Collection works after credential update
- Credential changes take effect without restart

---

## Risk Mitigation

| Risk | Severity | Mitigation |
|------|----------|-----------|
| Collector fails (missing credentials) | HIGH | Phase 0 audit + startup validation with clear errors |
| Decryption fails (wrong master key) | HIGH | Phase 0 verifies key, tests cover decryption |
| Operator forgets .env update | MEDIUM | Clear runbook + pre-startup validation script |
| DB corruption | MEDIUM | Backup before migration, transaction-safe script |
| Backward compat broken | MEDIUM | get_credentials() handles both encrypted/plaintext |
| Collection fails silently | MEDIUM | Clear error logging, UI credential status display |

---

## Success Criteria

- [ ] All env var references removed from code
- [ ] Collector only reads from collection_credentials table
- [ ] No env var fallback code path exists
- [ ] Operators can update credentials via API/UI without restart
- [ ] Credential changes take effect within 1 collection cycle
- [ ] Unit tests pass (≥80% coverage)
- [ ] E2E tests pass (smoke + chromium + webkit)
- [ ] Production deployment without incident
- [ ] No credential errors in 7-day post-deployment monitoring

---

## Timeline

| Phase | Duration | Status |
|-------|----------|--------|
| Phase 0: Pre-migration audit | 3 days | Pending |
| Phase 1: Code changes | 3 days | Pending |
| Phase 2: Migration script | 2 days | Pending |
| Phase 3: Testing | 3 days | Pending |
| Phase 4: Staging deployment | 2 days | Pending |
| Phase 5: Production deployment | 1 day | Pending |
| **Total** | **14 days** | — |
