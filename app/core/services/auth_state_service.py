from __future__ import annotations

from dataclasses import dataclass

from core.auth.security import PasswordPolicyError, hash_password, verify_password
from core.services.database_lease import connection_lease
from core.services.database_service import DatabaseService


AUTH_LOCK_ID = 1_078_811_105
PASSWORD_KEY = "admin_password"
USERNAME_KEY = "admin_username"
SESSION_VERSION_KEY = "admin_session_version"


@dataclass(frozen=True, slots=True)
class AdminCredentials:
    username: str
    password_hash: str
    session_version: int


@dataclass(frozen=True, slots=True)
class AuthStateUnavailableError(Exception):
    operation: str

    def __str__(self) -> str:
        return f"Authentication state unavailable during {self.operation}"


class AuthStateService:
    def __init__(self, database: DatabaseService) -> None:
        self._database = database

    @staticmethod
    def _upsert(cursor, key: str, value: str, setting_type: str) -> None:
        cursor.execute(
            """
            INSERT INTO system_settings
                (setting_key, setting_value, setting_type, description, category, is_encrypted, is_active)
            VALUES (%s, %s, %s, %s, 'security', false, true)
            ON CONFLICT (setting_key) DO UPDATE
            SET setting_value = EXCLUDED.setting_value,
                setting_type = EXCLUDED.setting_type,
                is_encrypted = false,
                is_active = true,
                updated_at = CURRENT_TIMESTAMP
            """,
            (key, value, setting_type, f"Authentication state: {key}"),
        )

    def get_credentials(self, default_username: str, default_password: str) -> AdminCredentials:
        try:
            with connection_lease(self._database) as connection:
                cursor = connection.cursor()
                try:
                    cursor.execute("SELECT pg_advisory_xact_lock(%s)", (AUTH_LOCK_ID,))
                    cursor.execute(
                        """
                        SELECT setting_key, setting_value
                        FROM system_settings
                        WHERE setting_key IN (%s, %s, %s) AND is_active = true
                        FOR UPDATE
                        """,
                        (USERNAME_KEY, PASSWORD_KEY, SESSION_VERSION_KEY),
                    )
                    values = {key: value for key, value in cursor.fetchall()}
                    changed = False
                    username = values.get(USERNAME_KEY)
                    if not username:
                        username = default_username
                        if username:
                            self._upsert(cursor, USERNAME_KEY, username, "string")
                            changed = True
                    password_hash = values.get(PASSWORD_KEY)
                    if not password_hash:
                        password_hash = hash_password(default_password) if default_password else ""
                        if password_hash:
                            self._upsert(cursor, PASSWORD_KEY, password_hash, "password")
                            changed = True
                    if username and password_hash and SESSION_VERSION_KEY not in values:
                        self._upsert(cursor, SESSION_VERSION_KEY, "1", "integer")
                        values[SESSION_VERSION_KEY] = "1"
                        changed = True
                    if changed:
                        connection.commit()
                    return AdminCredentials(
                        username=username,
                        password_hash=password_hash,
                        session_version=int(values.get(SESSION_VERSION_KEY, "0")),
                    )
                finally:
                    cursor.close()
        except (AuthStateUnavailableError, PasswordPolicyError):
            raise
        except Exception as error:
            raise AuthStateUnavailableError("credential read") from error

    def current_session_version(self, subject: str) -> int:
        try:
            with connection_lease(self._database) as connection:
                cursor = connection.cursor()
                try:
                    cursor.execute(
                        """
                        SELECT setting_value
                        FROM system_settings
                        WHERE setting_key = %s AND is_active = true
                        """,
                        (SESSION_VERSION_KEY,),
                    )
                    row = cursor.fetchone()
                finally:
                    cursor.close()
            if row is None:
                return 0
            version = int(row[0])
            if version < 0:
                raise ValueError("negative session version")
            return version
        except Exception as error:
            raise AuthStateUnavailableError("session version read") from error

    def upgrade_password_hash(self, expected_password: str, replacement_hash: str) -> bool:
        try:
            with connection_lease(self._database) as connection:
                cursor = connection.cursor()
                try:
                    cursor.execute(
                        """
                        UPDATE system_settings
                        SET setting_value = %s, updated_at = CURRENT_TIMESTAMP
                        WHERE setting_key = %s AND setting_value = %s AND is_active = true
                        """,
                        (replacement_hash, PASSWORD_KEY, expected_password),
                    )
                    upgraded = cursor.rowcount == 1
                    connection.commit()
                finally:
                    cursor.close()
            return upgraded
        except Exception as error:
            raise AuthStateUnavailableError("password hash upgrade") from error

    def rotate_password(self, subject: str, current_password: str, new_password: str) -> bool:
        replacement_hash = hash_password(new_password)
        try:
            with connection_lease(self._database) as connection:
                cursor = connection.cursor()
                try:
                    cursor.execute("SELECT pg_advisory_xact_lock(%s)", (AUTH_LOCK_ID,))
                    cursor.execute(
                        """
                        SELECT setting_key, setting_value
                        FROM system_settings
                        WHERE setting_key IN (%s, %s) AND is_active = true
                        FOR UPDATE
                        """,
                        (PASSWORD_KEY, SESSION_VERSION_KEY),
                    )
                    values = {key: value for key, value in cursor.fetchall()}
                    configured = values.get(PASSWORD_KEY)
                    if not configured or not verify_password(current_password, configured)[0]:
                        return False
                    version = int(values.get(SESSION_VERSION_KEY, "0"))
                    self._upsert(cursor, PASSWORD_KEY, replacement_hash, "password")
                    self._upsert(cursor, SESSION_VERSION_KEY, str(version + 1), "integer")
                    connection.commit()
                    return True
                finally:
                    cursor.close()
        except PasswordPolicyError:
            raise
        except Exception as error:
            raise AuthStateUnavailableError("password rotation") from error
