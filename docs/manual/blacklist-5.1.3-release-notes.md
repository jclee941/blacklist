# Blacklist 5.1.3 Release Notes

## Summary

Blacklist 5.1.3 completes the documentation and release-supply-chain remediation identified during the 5.1 security review.

## Fixed

- Replaced shell-based PDF source rewriting with strict SemVer parsing and argument-safe Pandoc execution.
- Generates every guide successfully and revalidates unchanged sources before publishing file-atomic PDF replacements.
- Added a source, version, and screenshot freshness manifest enforced by documentation checks.
- Regenerated all eight guide screenshots through the loopback-only canonical Playwright helper using file-atomic replacements.
- Restored the offline deployment PDF from its current Markdown source.
- Corrected production proxy, CI publication, credential migration, Raw Data export, and security-reporting documentation.
- Preserved natural Korean wrapping while allowing long unbroken reason strings to wrap inside the IP table.

## Security

- Resolved all Critical and High findings, plus the applicable Medium findings, from the 5.1 security review.
- Enforced JWT authentication and administrator authorization across protected APIs, with account lockout, token revocation, password policy enforcement, and transactional session invalidation.
- Removed fail-open credential behavior by persisting administrator authentication state transactionally and failing closed when PostgreSQL is unavailable.
- Hardened request trust boundaries with strict IP and payload validation, trusted-proxy handling, bounded proxy bodies, and Fortinet feed bearer-token and source-network enforcement.
- Applied least-privilege PostgreSQL runtime roles, authenticated Redis access, internal service TLS, non-root containers, read-only filesystems, dropped capabilities, and resource limits.
- Hardened the release supply chain with exact-commit CI gates, reuse of tested image artifacts, Trivy scans with zero unresolved Critical findings, signed release bundles, and verified checksums.
- Removed the reported dependency vulnerabilities and added regression coverage for the remediated authentication, authorization, database, proxy, packaging, and deployment boundaries.
- Enabled GitHub private vulnerability reporting and added the repository security policy.
- Corrected security advisory links so active vulnerabilities are not redirected to an unrelated repository.

## Breaking Changes

None.

## Upgrade Notes

This patch has no database migration. Verify the signed release bundle before installation and retain the existing deployment `.env`, PostgreSQL data, and TLS material during upgrade.
