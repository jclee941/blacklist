"""
Settings Service
Manages application settings stored in database
Replaces .env file dependency for runtime configurable settings
"""

import logging
from typing import Optional, Dict, List, Any
from datetime import datetime
from cryptography.fernet import Fernet
import os
import base64
import hashlib

from ..config import config
from .database_service import DatabaseService

logger = logging.getLogger(__name__)


class SettingsService:
    """Singleton service for managing system settings"""

    _instance = None
    _encryption_key: bytes = b""

    def __init__(self, db_service: Optional[DatabaseService] = None):
        self.db = db_service
        self._cache: Dict[str, Any] = {}
        self._cache_timestamp: Optional[datetime] = None
        self._cache_ttl = 60

        self._init_encryption_key()
        logger.info("SettingsService initialized")

    def _get_connection(self):
        if self.db is None:
            raise RuntimeError("DatabaseService not initialized")
        return self.db.get_connection()

    # Removed singleton __new__ method to allow DI instantiation

    def _init_encryption_key(self):
        """Initialize encryption key from environment or generate new one"""
        key_str = config.SETTINGS_ENCRYPTION_KEY

        if not key_str:
            secret = config.SECRET_KEY

            if not secret:
                env_mode = config.FLASK_ENV
                if env_mode == "production":
                    logger.warning("SECRET_KEY missing in production! Generating random key.")
                    secret = base64.urlsafe_b64encode(os.urandom(32)).decode()
                else:
                    secret = "blacklist-secret-key-change-in-production"

            # Generate deterministic key from secret
            key_bytes = hashlib.sha256(secret.encode()).digest()
            key_str = base64.urlsafe_b64encode(key_bytes).decode()

        self._encryption_key: bytes = key_str.encode()
        logger.info("Encryption key initialized")

    def _encrypt_value(self, value: str) -> str:
        """Encrypt a value using Fernet"""
        try:
            f = Fernet(self._encryption_key)
            encrypted = f.encrypt(value.encode())
            return base64.urlsafe_b64encode(encrypted).decode()
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            raise

    def _decrypt_value(self, encrypted_value: str) -> str:
        """Decrypt a value using Fernet"""
        try:
            f = Fernet(self._encryption_key)
            decoded = base64.urlsafe_b64decode(encrypted_value.encode())
            decrypted = f.decrypt(decoded)
            return decrypted.decode()
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise

    def _invalidate_cache(self):
        """Invalidate settings cache"""
        self._cache = {}
        self._cache_timestamp = None
        logger.debug("Settings cache invalidated")

    def _is_cache_valid(self) -> bool:
        """Check if cache is still valid"""
        if not self._cache_timestamp:
            return False

        age = (datetime.now() - self._cache_timestamp).total_seconds()
        return age < self._cache_ttl

    def get_setting(self, key: str, default: Any = None, use_cache: bool = True) -> Any:
        """
        Get setting value by key

        Args:
            key: Setting key (e.g., 'COLLECTION_INTERVAL')
            default: Default value if setting not found
            use_cache: Whether to use cached value

        Returns:
            Setting value (decrypted if encrypted)
        """
        try:
            # Check cache first
            if use_cache and self._is_cache_valid() and key in self._cache:
                return self._cache[key]

            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT setting_value, setting_type, is_encrypted
                FROM system_settings
                WHERE setting_key = %s AND is_active = true
            """,
                (key,),
            )

            result = cursor.fetchone()
            cursor.close()

            if not result:
                logger.warning(f"Setting not found: {key}, using default: {default}")
                return default

            value, setting_type, is_encrypted = result

            # Decrypt if needed
            if is_encrypted and value:
                value = self._decrypt_value(value)

            # Convert type
            converted_value = self._convert_value(value, setting_type)

            # Update cache
            self._cache[key] = converted_value
            if not self._cache_timestamp:
                self._cache_timestamp = datetime.now()

            return converted_value

        except Exception as e:
            logger.error(f"Error getting setting {key}: {e}")
            return default

    def _convert_value(self, value: str, setting_type: str) -> Any:
        """Convert string value to appropriate type"""
        if value is None:
            return None

        try:
            if setting_type == "integer":
                return int(value)
            elif setting_type == "boolean":
                return value.lower() in ("true", "1", "yes", "on")
            elif setting_type == "json":
                import json

                return json.loads(value)
            else:  # string, password
                return value
        except Exception as e:
            logger.error(f"Error converting value '{value}' to type '{setting_type}': {e}")
            return value

    def set_setting(self, key: str, value: Any, encrypt: bool = False) -> bool:
        """
        Set or update setting value

        Args:
            key: Setting key
            value: Setting value
            encrypt: Whether to encrypt the value

        Returns:
            True if successful
        """
        conn: Any = None
        try:
            # Convert value to string
            if isinstance(value, bool):
                str_value = "true" if value else "false"
            elif isinstance(value, (dict, list)):
                import json

                str_value = json.dumps(value)
            else:
                str_value = str(value)

            # Encrypt if requested
            if encrypt:
                str_value = self._encrypt_value(str_value)

            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute(
                """
                UPDATE system_settings
                SET setting_value = %s,
                    is_encrypted = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE setting_key = %s
                RETURNING id
            """,
                (str_value, encrypt, key),
            )

            result = cursor.fetchone()
            conn.commit()
            cursor.close()

            if result:
                self._invalidate_cache()
                logger.info(f"Setting updated: {key}")
                return True
            else:
                logger.warning(f"Setting not found for update: {key}")
                return False

        except Exception as e:
            logger.error(f"Error setting {key}: {e}")
            if conn is not None:
                conn.rollback()
            return False

    def get_all_settings(self, category: Optional[str] = None, include_encrypted: bool = False) -> List[Dict]:
        """
        Get all settings, optionally filtered by category

        Args:
            category: Category filter (e.g., 'collection', 'security')
            include_encrypted: Whether to include encrypted values (decrypted)

        Returns:
            List of setting dictionaries
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            if category:
                query = """
                    SELECT setting_key, setting_value, setting_type, description,
                           is_encrypted, is_active, category, display_order, updated_at
                    FROM system_settings
                    WHERE category = %s AND is_active = true
                    ORDER BY display_order, setting_key
                """
                cursor.execute(query, (category,))
            else:
                query = """
                    SELECT setting_key, setting_value, setting_type, description,
                           is_encrypted, is_active, category, display_order, updated_at
                    FROM system_settings
                    WHERE is_active = true
                    ORDER BY category, display_order, setting_key
                """
                cursor.execute(query)

            rows = cursor.fetchall()
            cursor.close()

            settings = []
            for row in rows:
                setting = {
                    "key": row[0],
                    "value": row[1],
                    "type": row[2],
                    "description": row[3],
                    "is_encrypted": row[4],
                    "is_active": row[5],
                    "category": row[6],
                    "display_order": row[7],
                    "updated_at": row[8].isoformat() if row[8] else None,
                }

                # Decrypt if needed and requested
                if setting["is_encrypted"] and include_encrypted and setting["value"]:
                    try:
                        setting["value"] = self._decrypt_value(setting["value"])
                    except Exception as e:
                        logger.error(f"Failed to decrypt {setting['key']}: {e}")
                        setting["value"] = "***DECRYPTION_ERROR***"
                elif setting["is_encrypted"]:
                    # Mask encrypted values
                    setting["value"] = "********"

                # Convert value to appropriate type
                if not setting["is_encrypted"] or include_encrypted:
                    setting["value"] = self._convert_value(setting["value"], setting["type"])

                settings.append(setting)

            return settings

        except Exception as e:
            logger.error(f"Error getting all settings: {e}")
            return []

    def get_settings_by_category(self) -> Dict[str, List[Dict]]:
        """
        Get all settings grouped by category

        Returns:
            Dictionary with categories as keys and setting lists as values
        """
        all_settings = self.get_all_settings()

        grouped = {}
        for setting in all_settings:
            category = setting["category"]
            if category not in grouped:
                grouped[category] = []
            grouped[category].append(setting)

        return grouped

    def create_setting(
        self,
        key: str,
        value: Any,
        setting_type: str = "string",
        description: str = "",
        category: str = "general",
        encrypt: bool = False,
    ) -> bool:
        """
        Create a new setting

        Args:
            key: Setting key (uppercase with underscores)
            value: Setting value
            setting_type: Type (string, integer, boolean, json, password)
            description: Setting description
            category: Category (general, collection, security, notification, integration)
            encrypt: Whether to encrypt the value

        Returns:
            True if successful
        """
        conn: Any = None
        try:
            # Convert value to string
            if isinstance(value, bool):
                str_value = "true" if value else "false"
            elif isinstance(value, (dict, list)):
                import json

                str_value = json.dumps(value)
            else:
                str_value = str(value)

            # Encrypt if requested
            if encrypt:
                str_value = self._encrypt_value(str_value)

            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO system_settings
                (setting_key, setting_value, setting_type, description, category, is_encrypted, is_active)
                VALUES (%s, %s, %s, %s, %s, %s, true)
                RETURNING id
            """,
                (key, str_value, setting_type, description, category, encrypt),
            )

            result = cursor.fetchone()
            conn.commit()
            cursor.close()

            if result:
                self._invalidate_cache()
                logger.info(f"Setting created: {key}")
                return True
            else:
                return False

        except Exception as e:
            logger.error(f"Error creating setting {key}: {e}")
            if conn is not None:
                conn.rollback()
            return False

    def delete_setting(self, key: str) -> bool:
        """
        Soft delete a setting (set is_active = false)

        Args:
            key: Setting key

        Returns:
            True if successful
        """
        conn: Any = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute(
                """
                UPDATE system_settings
                SET is_active = false,
                    updated_at = CURRENT_TIMESTAMP
                WHERE setting_key = %s
                RETURNING id
            """,
                (key,),
            )

            result = cursor.fetchone()
            conn.commit()
            cursor.close()

            if result:
                self._invalidate_cache()
                logger.info(f"Setting deleted: {key}")
                return True
            else:
                logger.warning(f"Setting not found for deletion: {key}")
                return False

        except Exception as e:
            logger.error(f"Error deleting setting {key}: {e}")
            if conn is not None:
                conn.rollback()
            return False

    # Convenience methods for common settings
    def get_collection_interval(self) -> int:
        """Get collection interval in seconds"""
        return self.get_setting("COLLECTION_INTERVAL", default=3600)

    def is_auto_collection_disabled(self) -> bool:
        """Check if auto collection is disabled"""
        return self.get_setting("DISABLE_AUTO_COLLECTION", default=True)

    def get_regtech_base_url(self) -> str:
        """Get REGTECH base URL"""
        return self.get_setting("REGTECH_BASE_URL", default="https://regtech.fsec.or.kr")


# Create singleton instance replaced with LocalProxy
# settings_service = SettingsService()
from flask import current_app
from werkzeug.local import LocalProxy

settings_service = LocalProxy(lambda: current_app.extensions["settings_service"])
