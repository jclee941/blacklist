#!/usr/bin/env python3
"""
Migrate credentials from environment variables to PostgreSQL collection_credentials table.

This script safely migrates credentials from env vars (REGTECH_ID, REGTECH_PW, SECUDIUM_ID, 
SECUDIUM_PW) to encrypted storage in the collection_credentials table.

Usage:
    export DATABASE_URL="postgresql://user:pass@localhost:5432/blacklist"
    export CREDENTIAL_MASTER_KEY="<32-byte hex key>"
    python3 scripts/migrate_env_credentials_to_db.py \
        --regtech-id XXXX \
        --regtech-pw XXXX \
        --secudium-id XXXX \
        --secudium-pw XXXX \
        --dry-run

Or from environment variables:
    python3 scripts/migrate_env_credentials_to_db.py --auto
"""

import argparse
import os
import sys
from pathlib import Path

# Add app directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.services.secure_credential_service import SecureCredentialService
from app.core.logger import get_logger

logger = get_logger(__name__)


class CredentialMigrator:
    """Handles migration of env var credentials to encrypted DB storage."""
    
    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.service = SecureCredentialService()
        self.migrated = []
        self.skipped = []
        self.errors = []
    
    def migrate_credential(
        self,
        source: str,
        username: str,
        password: str,
    ) -> bool:
        """Migrate a single credential to DB."""
        if not username or not password:
            self.skipped.append(f"{source.upper()}: Missing username or password")
            return False
        
        try:
            # Validate inputs
            if len(username) > 255:
                raise ValueError(f"Username too long (max 255 chars): {len(username)}")
            if source.lower() not in ["regtech", "secudium"]:
                raise ValueError(f"Invalid source: {source}")
            
            if self.dry_run:
                logger.info(f"[DRY RUN] Would migrate {source.upper()} credentials")
                self.migrated.append(f"{source.upper()}: {username} (DRY RUN)")
                return True
            
            # Encrypt and save to DB
            self.service.save_credentials(
                source=source.lower(),
                username=username,
                password=password,
                is_active=True,
                enabled=True,
                encrypted=True
            )
            
            # Verify by reading back
            stored_username, stored_password = self.service.get_credentials(source.lower())
            if stored_username == username and stored_password == password:
                self.migrated.append(f"{source.upper()}: {username}")
                logger.info(f"✓ Migrated {source.upper()} credentials")
                return True
            else:
                self.errors.append(f"{source.upper()}: Verification failed")
                return False
                
        except Exception as e:
            error_msg = f"{source.upper()}: {str(e)}"
            self.errors.append(error_msg)
            logger.error(f"✗ {error_msg}")
            return False
    
    def print_summary(self) -> None:
        """Print migration summary."""
        print("\n" + "=" * 70)
        print("MIGRATION SUMMARY")
        print("=" * 70)
        
        if self.migrated:
            print(f"\n✓ Successfully migrated ({len(self.migrated)}):")
            for item in self.migrated:
                print(f"  - {item}")
        
        if self.skipped:
            print(f"\n⊘ Skipped ({len(self.skipped)}):")
            for item in self.skipped:
                print(f"  - {item}")
        
        if self.errors:
            print(f"\n✗ Errors ({len(self.errors)}):")
            for item in self.errors:
                print(f"  - {item}")
        
        print("\n" + "=" * 70)


def validate_environment() -> None:
    """Validate required environment variables."""
    if not os.getenv("CREDENTIAL_MASTER_KEY"):
        print("ERROR: CREDENTIAL_MASTER_KEY env var not set")
        sys.exit(1)


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Migrate environment variable credentials to encrypted DB storage"
    )
    
    parser.add_argument("--regtech-id", help="REGTECH username")
    parser.add_argument("--regtech-pw", help="REGTECH password")
    parser.add_argument("--secudium-id", help="SECUDIUM username")
    parser.add_argument("--secudium-pw", help="SECUDIUM password")
    parser.add_argument("--auto", action="store_true", help="Read from env vars")
    parser.add_argument("--dry-run", action="store_true", help="Preview without changes")
    
    args = parser.parse_args()
    
    # Validate environment
    validate_environment()
    
    # Determine credentials source
    regtech_id = args.regtech_id
    regtech_pw = args.regtech_pw
    secudium_id = args.secudium_id
    secudium_pw = args.secudium_pw
    
    if args.auto:
        regtech_id = regtech_id or os.getenv("REGTECH_ID")
        regtech_pw = regtech_pw or os.getenv("REGTECH_PW")
        secudium_id = secudium_id or os.getenv("SECUDIUM_ID")
        secudium_pw = secudium_pw or os.getenv("SECUDIUM_PW")
    
    # Check if any credentials provided
    if not any([regtech_id, regtech_pw, secudium_id, secudium_pw]):
        parser.print_help()
        return 1
    
    # Run migration
    migrator = CredentialMigrator(dry_run=args.dry_run)
    
    if regtech_id and regtech_pw:
        migrator.migrate_credential("regtech", regtech_id, regtech_pw)
    
    if secudium_id and secudium_pw:
        migrator.migrate_credential("secudium", secudium_id, secudium_pw)
    
    # Print summary
    migrator.print_summary()
    
    return 1 if migrator.errors else 0


if __name__ == "__main__":
    sys.exit(main())
