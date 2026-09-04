# Operator Migration Guide: Env Vars → DB-Only Credentials

**Version**: 3.6.0+  
**Updated**: February 2026  
**Audience**: System Operators, DevOps Engineers

---

## Overview

Starting with version 3.6.0, the Blacklist Intelligence Platform **no longer supports storing credentials in environment variables**. All credentials must be managed through the **PostgreSQL database** and configured via the **web API**.

### What Changed?

| Before (3.5.x)                                            | After (3.6.0+)                                       |
| --------------------------------------------------------- | ---------------------------------------------------- |
| Credentials in `.env` file (REGTECH_ID, REGTECH_PW, etc.) | Credentials stored in `collection_credentials` table |
| Manual restart required for credential changes            | Changes take effect within next collection cycle     |
| No audit trail for env var credentials                    | Full audit trail in database                         |
| Env vars took priority over DB                            | DB is the single source of truth                     |

---

## Pre-Migration Checklist

Before deploying version 3.6.0, ensure:

- [ ] Current REGTECH credentials are documented
- [ ] `CREDENTIAL_MASTER_KEY` environment variable is set in production
- [ ] Production database is backed up
- [ ] Test environment has been upgraded to 3.6.0
- [ ] Migration script has been tested on staging

---

## Migration Steps

### Step 1: Extract Current Credentials

Retrieve your current credentials from the `.env` file or your deployment config:

```bash
# On your deployment machine
echo "REGTECH_ID=$REGTECH_ID"
echo "REGTECH_PW=$REGTECH_PW"

# Store safely for Step 3
```

### Step 2: Verify CREDENTIAL_MASTER_KEY

Ensure the encryption master key is set:

```bash
# Check if already set
docker compose exec -T blacklist-app env | grep CREDENTIAL_MASTER_KEY

# If not set, generate and store:
python3 -c "import secrets; print(secrets.token_hex(32))"
# Output: a1b2c3d4e5f6... (64 hex characters)

# Add to docker compose environment or Kubernetes secrets
```

### Step 3: Deploy New Version

#### Docker Compose Users

```bash
# Download or build 3.6.0 images
make build  # or docker compose pull

# Bring up new version
docker compose down
docker compose up -d

# Verify it started
docker compose logs collector | head -20
# Should show: "🔍 Validating credentials" and error about missing credentials (expected)
```

#### Kubernetes Users

```bash
# Update image tags in your deployment
kubectl set image deployment/blacklist-app \
  blacklist-app=ghcr.io/qws941/blacklist-app:3.6.0

kubectl set image deployment/blacklist-collector \
  blacklist-collector=ghcr.io/qws941/blacklist-collector:3.6.0

# Check rollout
kubectl rollout status deployment/blacklist-collector
```

### Step 4: Migrate Credentials to Database

Use the provided migration script:

```bash
# Run from the app container
docker compose exec -T blacklist-app python3 scripts/migrate_env_credentials_to_db.py \
    --regtech-id "$REGTECH_ID" \
    --regtech-pw "$REGTECH_PW" \

# Expected output:
# ====== MIGRATION SUMMARY ======
# ✓ Successfully migrated (2):
#   - REGTECH: your_username
# ==================================
```

**Important**: The script will print next steps. Follow them carefully!

### Step 5: Verify Database Storage

```bash
# Connect to postgres
docker compose exec -T postgres psql -U postgres -d blacklist << 'SQL'
SELECT source, username, enabled FROM collection_credentials;
SQL

# Expected output:
#  source  | username | enabled
# ---------+----------+---------
#  regtech | xxxxx    | t
```

### Step 6: Verify Collector Can Read Credentials

```bash
# Check collector logs
docker compose logs collector | grep -E "REGTECH|credentials"

# Expected logs:
# 🔍 Validating credentials
# ✅ REGTECH credentials loaded from database
# ✅ All required credentials are configured
```

### Step 7: Test Collection Pipeline

```bash
# Trigger manual collection to verify everything works
curl -X POST http://localhost:2542/api/collection/run \
  -H "Content-Type: application/json" \
  -d '{"source": "regtech"}'

# Monitor logs for success
docker compose logs -f collector | grep -E "REGTECH|collection|ERROR"

# Should see collection job start and complete without credential errors
```

### Step 8: Remove Environment Variables

Once verified in Step 7, remove credentials from `.env`:

```bash
# Edit .env and remove:
# REGTECH_ID=...      ← DELETE
# REGTECH_PW=...      ← DELETE

# KEEP these:
# CREDENTIAL_MASTER_KEY=...
# ENCRYPTION_SALT=...
```

### Step 9: Restart Services (Final)

```bash
docker compose down
docker compose up -d

# Verify startup success
docker compose logs | grep "✅ Blacklist Collector started successfully"

# Verify collections work (should run on schedule automatically)
docker compose logs -f collector | tail -30
```

---

## Managing Credentials After Migration

### Web UI Method (Recommended)

1. **Open the web dashboard**: <https://your-server/>
2. **Navigate to**: Settings → Credentials
3. **Update REGTECH**: Enter username and password, click Save
4. **Changes take effect**: Within next collection cycle (no restart needed)

### API Method

#### Add/Update REGTECH Credentials

```bash
curl -X POST http://localhost:2542/api/credentials \
  -H "Content-Type: application/json" \
  -d '{
    "source": "regtech",
    "username": "your_regtech_username",
    "password": "your_regtech_password"
  }'
```

#### View Current Credentials (Summary Only)

```bash
curl http://localhost:2542/api/credentials \
  -H "Authorization: Bearer $TOKEN" | jq
```

#### Delete Credentials

```bash
curl -X DELETE http://localhost:2542/api/credentials/regtech \
  -H "Authorization: Bearer $TOKEN"
```

---

## Troubleshooting

### Collector Won't Start: "Missing Credentials"

**Error**:

```text
❌ Missing credentials: REGTECH. Collections will fail.
```

**Solution**: Run the migration script from Step 4:

```bash
docker compose exec -T blacklist-app python3 scripts/migrate_env_credentials_to_db.py \
    --regtech-id "YOUR_ID" \
    --regtech-pw "YOUR_PASSWORD" \
```

### Collections Fail: "Credentials Not Found"

**Error**: Collection jobs fail with "credentials not found"

**Solution**:

1. Check database: `SELECT * FROM collection_credentials WHERE enabled = true;`
2. If empty, run migration script again
3. If present but collection still fails, credentials may be incorrect
4. Update via web UI or API with correct credentials

### Decryption Failed: Wrong Master Key

**Error**:

```text
❌ Credential validation error: Failed to decrypt REGTECH credentials
```

**Solution**:

1. Verify `CREDENTIAL_MASTER_KEY` env var matches your database encryption key
2. If lost, you must re-add credentials (decryption cannot be reversed)
3. Update via web UI: Settings → Credentials

### Need to Rollback to 3.5.x

If something goes wrong:

1. **Restore database backup** from pre-migration
2. **Restore old app/collector images**:

   ```bash
   git checkout v3.5.64
   make build
   docker compose down
   docker compose up -d
   ```

3. **Re-add env var credentials** to `.env`
4. **Restart and verify**

---

## Health Check

After migration, verify everything is working:

```bash
# 1. Check app health
curl http://localhost:2542/health | jq '.status'

# 2. Check collector health
curl http://localhost:8545/health | jq '.status'

# 3. Check collector startup logs
docker compose logs collector | grep -A 10 "Validating credentials"

# 4. Check recent collections
curl http://localhost:2542/api/collection/status | jq '.history[0]'

# All should show ✅ and no errors
```

---

## FAQ

**Q: Can I keep environment variables for other purposes?**
A: Yes! Only REGTECH_ID and REGTECH_PW are removed. Other env vars (database, Redis, etc.) are unchanged.

**Q: How often do credential changes take effect?**
A: Immediately for new collection jobs. Current collection in progress will finish with old credentials.

**Q: Can I view my stored credentials?**
A: The API returns source name and username only. Passwords are encrypted and never returned in plaintext.

**Q: What if I forget my credentials?**
A: Contact your IT team or REGTECH support. Credentials cannot be recovered from the encrypted database. You must update them via web UI or API.

**Q: Do I need to restart the collector after changing credentials?**
A: No! Collector reloads credentials before each collection job. Changes take effect within the next scheduled collection.

**Q: What's the CREDENTIAL_MASTER_KEY used for?**
A: It encrypts passwords in the database using AES-256. Store it securely (Vault, K8s Secrets, etc.). If lost, you cannot decrypt existing credentials.

---

## Support

For issues:

1. Check logs: `docker compose logs collector`
2. Run health checks (see above)
3. Review this guide's Troubleshooting section
4. Contact your DevOps/Platform team
5. Open an issue: <https://github.com/qws941/blacklist/issues>

---

## Version Info

| Version | Status  | Credential Management |
| ------- | ------- | --------------------- |
| < 3.6.0 | Legacy  | Env vars (deprecated) |
| 3.6.0+  | Current | DB-only (required)    |

**Migrate ASAP** to 3.6.0+ for improved security and operational flexibility.
