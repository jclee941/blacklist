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

- Enabled GitHub private vulnerability reporting and added the repository security policy.
- Corrected security advisory links so active vulnerabilities are not redirected to an unrelated repository.

## Upgrade Notes

This patch has no database migration. Verify the signed release bundle before installation and retain the existing deployment `.env`, PostgreSQL data, and TLS material during upgrade.
