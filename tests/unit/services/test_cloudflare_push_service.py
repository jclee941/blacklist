"""Tests for CloudflarePushService"""

import os
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "app"))

ENCRYPTED_ROW = ("encrypted-token-blob", True)
DEFAULT_CREDENTIALS = {
    "password": "test-token-abc123",
    "config": {"account_id": "test-account-id", "list_id": "test-list-id"},
}


def _make_service(db_service=None, env=None, row=ENCRYPTED_ROW, credentials=DEFAULT_CREDENTIALS):
    """Create CloudflarePushService with mocked DB credentials."""
    if db_service is None:
        mock_db = Mock()
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_cursor.fetchone.return_value = row
        mock_conn.cursor.return_value = mock_cursor
        mock_db.get_connection.return_value = mock_conn
    else:
        mock_db = db_service

    import importlib

    mod = importlib.import_module("core.services.cloudflare_push_service")
    importlib.reload(mod)
    with patch("core.services.secure_credential_service.SecureCredentialService") as credential_service_cls:
        credential_service_cls.return_value.get_credentials.return_value = credentials
        svc = mod.CloudflarePushService(db_service=mock_db)
    return svc, mock_db


class TestCloudflareServiceInit:
    """Test service initialization"""

    def test_init_reads_credentials_from_db(self):
        """Credentials are loaded from database"""
        svc, _ = _make_service()
        assert svc.api_token == "test-token-abc123"
        assert svc.account_id == "test-account-id"
        assert svc.list_id == "test-list-id"

    def test_init_sets_db_conn_none(self):
        svc, _ = _make_service()
        assert svc.db_conn is None

    def test_init_builds_session_with_auth(self):
        svc, _ = _make_service()
        assert "Authorization" in svc.session.headers
        assert svc.session.headers["Authorization"] == "Bearer test-token-abc123"

    def test_init_no_db_service(self):
        """Service initializes with empty credentials when no DB"""
        mock_db = Mock()
        mock_db.get_connection.return_value = None
        svc, _ = _make_service(db_service=mock_db)
        assert svc.api_token == ""

    def test_load_credentials_from_db(self):
        """DB credentials are loaded successfully"""
        mock_db = Mock()
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_cursor.fetchone.return_value = ENCRYPTED_ROW
        mock_conn.cursor.return_value = mock_cursor
        mock_db.get_connection.return_value = mock_conn

        svc, _ = _make_service(
            db_service=mock_db,
            credentials={
                "password": "db-token-xyz",
                "config": {"account_id": "db-account-id", "list_id": "db-list-id"},
            },
        )

        assert svc.api_token == "db-token-xyz"
        assert svc.account_id == "db-account-id"
        assert svc.list_id == "db-list-id"
        assert svc.session.headers["Authorization"] == "Bearer db-token-xyz"
        mock_cursor.execute.assert_called_once_with(
            "SELECT password, encrypted FROM collection_credentials "
            "WHERE service_name = 'CLOUDFLARE' AND is_active = true"
        )
        mock_cursor.close.assert_called_once()
        mock_db.return_connection.assert_called_once_with(mock_conn)

    def test_unencrypted_row_is_rejected(self):
        """A plaintext credential row is refused instead of used"""
        svc, _ = _make_service(row=("plaintext-token", False))

        assert svc.api_token == ""
        assert svc.account_id == ""
        assert svc.list_id == ""
        assert svc.is_configured() is False

    def test_encrypted_row_without_token_is_rejected(self):
        svc, _ = _make_service(row=(None, True))

        assert svc.api_token == ""
        assert svc.is_configured() is False

    def test_failed_decryption_leaves_credentials_empty(self):
        svc, _ = _make_service(credentials=None)

        assert svc.api_token == ""
        assert svc.is_configured() is False

    def test_load_credentials_no_db_connection(self):
        """Empty credentials when DB has no connection"""
        mock_db = Mock()
        mock_db.get_connection.return_value = None

        svc, _ = _make_service(db_service=mock_db)

        assert svc.api_token == ""
        assert svc.account_id == ""
        assert svc.list_id == ""

    def test_load_credentials_db_error(self):
        """Empty credentials when DB lookup raises"""
        mock_db = Mock()
        mock_db.get_connection.side_effect = RuntimeError("db unavailable")

        svc, _ = _make_service(db_service=mock_db)

        assert svc.api_token == ""
        assert svc.account_id == ""
        assert svc.list_id == ""


class TestFetchActiveIps:
    """Test IP fetching from database"""

    def test_fetch_returns_ip_list(self):
        svc, mock_db = _make_service()
        mock_cursor = Mock()
        mock_cursor.fetchall.return_value = [("1.2.3.4",), ("5.6.7.8",)]
        mock_conn = Mock()
        mock_conn.cursor.return_value = mock_cursor
        svc.db_conn = mock_conn

        result = svc.fetch_active_ips()
        assert result == ["1.2.3.4", "5.6.7.8"]

    def test_fetch_empty_result(self):
        svc, _ = _make_service()
        mock_cursor = Mock()
        mock_cursor.fetchall.return_value = []
        mock_conn = Mock()
        mock_conn.cursor.return_value = mock_cursor
        svc.db_conn = mock_conn

        result = svc.fetch_active_ips()
        assert result == []

    def test_fetch_no_connection(self):
        svc, _ = _make_service()
        svc.db_conn = None
        result = svc.fetch_active_ips()
        assert result == []

    def test_fetch_db_error(self):
        svc, _ = _make_service()
        mock_cursor = Mock()
        mock_cursor.execute.side_effect = Exception("DB error")
        mock_conn = Mock()
        mock_conn.cursor.return_value = mock_cursor
        svc.db_conn = mock_conn

        result = svc.fetch_active_ips()
        assert result == []


class TestPushToCloudflare:
    """Test Cloudflare API push"""

    def test_push_not_configured(self):
        """Returns False when config is missing"""
        svc, _ = _make_service()
        svc.api_token = None
        assert svc.push_to_cloudflare(["1.2.3.4"]) is False

    def test_push_success(self):
        """Full push flow: PUT → operation_id → poll completed"""
        svc, _ = _make_service()
        mock_put_response = Mock()
        mock_put_response.json.return_value = {
            "success": True,
            "result": {"operation_id": "op-123"},
        }
        mock_put_response.raise_for_status = Mock()

        mock_poll_response = Mock()
        mock_poll_response.json.return_value = {
            "success": True,
            "result": {"status": "completed"},
        }
        mock_poll_response.raise_for_status = Mock()

        svc.session.put = Mock(return_value=mock_put_response)
        svc.session.get = Mock(return_value=mock_poll_response)

        result = svc.push_to_cloudflare(["1.2.3.4", "5.6.7.8"])
        assert result is True

        # Verify PUT was called with correct URL and payload
        call_args = svc.session.put.call_args
        assert "/rules/lists/test-list-id/items" in call_args[0][0]
        assert call_args[1]["json"] == [{"ip": "1.2.3.4"}, {"ip": "5.6.7.8"}]

    def test_push_api_error(self):
        """Returns False when CF API returns success=false"""
        svc, _ = _make_service()
        mock_response = Mock()
        mock_response.json.return_value = {
            "success": False,
            "errors": [{"message": "bad request"}],
        }
        mock_response.raise_for_status = Mock()
        svc.session.put = Mock(return_value=mock_response)

        assert svc.push_to_cloudflare(["1.2.3.4"]) is False

    def test_push_connection_error(self):
        """Returns False on network error"""
        svc, _ = _make_service()
        import requests as real_requests

        svc.session.put = Mock(side_effect=real_requests.RequestException("timeout"))

        assert svc.push_to_cloudflare(["1.2.3.4"]) is False

    def test_push_formats_items_correctly(self):
        """Verify each IP is wrapped in {"ip": ...}"""
        svc, _ = _make_service()
        mock_response = Mock()
        mock_response.json.return_value = {
            "success": True,
            "result": {"operation_id": "op-456"},
        }
        mock_response.raise_for_status = Mock()
        svc.session.put = Mock(return_value=mock_response)
        svc._poll_operation = Mock(return_value=True)

        svc.push_to_cloudflare(["10.0.0.1", "10.0.0.2", "10.0.0.3"])

        payload = svc.session.put.call_args[1]["json"]
        assert payload == [{"ip": "10.0.0.1"}, {"ip": "10.0.0.2"}, {"ip": "10.0.0.3"}]


class TestPollOperation:
    """Test bulk operation polling"""

    def test_poll_completed(self):
        svc, _ = _make_service()
        mock_response = Mock()
        mock_response.json.return_value = {
            "success": True,
            "result": {"status": "completed"},
        }
        mock_response.raise_for_status = Mock()
        svc.session.get = Mock(return_value=mock_response)

        assert svc._poll_operation("op-123") is True

    def test_poll_failed(self):
        svc, _ = _make_service()
        mock_response = Mock()
        mock_response.json.return_value = {
            "success": True,
            "result": {"status": "failed", "error": "list too large"},
        }
        mock_response.raise_for_status = Mock()
        svc.session.get = Mock(return_value=mock_response)

        assert svc._poll_operation("op-123") is False

    def test_poll_timeout(self):
        """Returns False when poll exceeds POLL_TIMEOUT"""
        svc, _ = _make_service()
        import importlib

        mod = importlib.import_module("core.services.cloudflare_push_service")
        with patch.object(mod, "time") as mock_time:
            # Simulate time passing beyond timeout
            mock_time.time.side_effect = [0, 0, 200]  # start, check, expired
            mock_time.sleep = Mock()

            mock_response = Mock()
            mock_response.json.return_value = {
                "success": True,
                "result": {"status": "running"},
            }
            mock_response.raise_for_status = Mock()
            svc.session.get = Mock(return_value=mock_response)

            assert svc._poll_operation("op-123") is False

    def test_poll_pending_then_completed(self):
        """Polls multiple times until completed"""
        svc, _ = _make_service()
        pending = Mock()
        pending.json.return_value = {"success": True, "result": {"status": "running"}}
        pending.raise_for_status = Mock()

        completed = Mock()
        completed.json.return_value = {"success": True, "result": {"status": "completed"}}
        completed.raise_for_status = Mock()

        svc.session.get = Mock(side_effect=[pending, completed])
        svc.POLL_INTERVAL = 0  # no sleep in tests

        assert svc._poll_operation("op-123") is True
        assert svc.session.get.call_count == 2


class TestHandleChangeNotification:
    """Test change notification handling"""

    def test_triggers_sync(self):
        """Triggers full sync when not rate limited"""
        svc, _ = _make_service()
        svc.last_update = 0  # long ago
        svc._fetch_list_state = Mock(return_value=(0, None))
        svc.fetch_active_ips = Mock(return_value=["1.2.3.4"])
        svc.push_to_cloudflare = Mock(return_value=True)

        svc.handle_change_notification("INSERT")

        svc.fetch_active_ips.assert_called_once()
        svc.push_to_cloudflare.assert_called_once_with(["1.2.3.4"])
        assert svc._sync_pending is False

    def test_rate_limited_change_is_retried_not_dropped(self):
        """A change inside the rate limit window stays queued for the next attempt"""
        svc, _ = _make_service()
        svc.last_update = time.time()  # just now
        svc.fetch_active_ips = Mock()

        svc.handle_change_notification("INSERT")

        svc.fetch_active_ips.assert_not_called()
        assert svc._sync_pending is True
        assert svc._retry_at > time.time()
        assert svc._select_timeout() <= svc.RATE_LIMIT_SECONDS

    def test_empty_ip_list_skips_push(self):
        """Does not push when no active IPs"""
        svc, _ = _make_service()
        svc.last_update = 0
        svc._fetch_list_state = Mock(return_value=(100, None))
        svc.fetch_active_ips = Mock(return_value=[])
        svc.push_to_cloudflare = Mock()

        svc.handle_change_notification("DELETE")

        svc.push_to_cloudflare.assert_not_called()
        assert svc._sync_pending is True


class TestChangeGuard:
    """Bulk replace must not publish a sudden list-size swing"""

    def test_small_list_is_not_guarded(self):
        svc, _ = _make_service()
        assert svc._within_change_guard(10, 1) is True

    def test_change_within_ratio_is_allowed(self):
        svc, _ = _make_service()
        assert svc._within_change_guard(100, 125) is True

    def test_mass_deletion_is_blocked(self):
        svc, _ = _make_service()
        assert svc._within_change_guard(1000, 1) is False

    def test_mass_addition_is_blocked(self):
        svc, _ = _make_service()
        assert svc._within_change_guard(100, 200) is False


class TestSyncNow:
    """Deferred-retry behaviour of the reconcile step"""

    def test_successful_sync_clears_pending(self):
        svc, _ = _make_service()
        svc._sync_pending = True
        svc._fetch_list_state = Mock(return_value=(100, 3600.0))
        svc.fetch_active_ips = Mock(return_value=["1.2.3.4"] * 90)
        svc.push_to_cloudflare = Mock(return_value=True)

        assert svc.sync_now() is True
        assert svc._sync_pending is False

    def test_recent_remote_modification_defers(self):
        """Rate limiting survives a restart because the list's own timestamp is used"""
        svc, _ = _make_service()
        svc._sync_pending = True
        svc._fetch_list_state = Mock(return_value=(100, 5.0))
        svc.fetch_active_ips = Mock()
        svc.push_to_cloudflare = Mock()

        assert svc.sync_now() is False
        svc.push_to_cloudflare.assert_not_called()
        assert svc._sync_pending is True

    def test_guard_violation_blocks_push(self):
        svc, _ = _make_service()
        svc._sync_pending = True
        svc._fetch_list_state = Mock(return_value=(1000, 3600.0))
        svc.fetch_active_ips = Mock(return_value=["1.2.3.4"])
        svc.push_to_cloudflare = Mock()

        assert svc.sync_now() is False
        svc.push_to_cloudflare.assert_not_called()
        assert svc._sync_pending is False

    def test_failed_push_is_retried(self):
        svc, _ = _make_service()
        svc._sync_pending = True
        svc._fetch_list_state = Mock(return_value=(100, 3600.0))
        svc.fetch_active_ips = Mock(return_value=["1.2.3.4"] * 95)
        svc.push_to_cloudflare = Mock(return_value=False)

        assert svc.sync_now() is False
        assert svc._sync_pending is True

    def test_unreadable_list_state_is_retried(self):
        svc, _ = _make_service()
        svc._sync_pending = True
        svc._fetch_list_state = Mock(return_value=None)
        svc.push_to_cloudflare = Mock()

        assert svc.sync_now() is False
        svc.push_to_cloudflare.assert_not_called()
        assert svc._sync_pending is True


class TestListState:
    """Live list state feeds both the guard and the rate limit"""

    def test_reads_item_count_and_modification_age(self):
        svc, _ = _make_service()
        modified = (datetime.now(timezone.utc) - timedelta(seconds=120)).strftime("%Y-%m-%dT%H:%M:%SZ")
        response = Mock()
        response.raise_for_status = Mock()
        response.json.return_value = {
            "success": True,
            "result": {"num_items": 250, "modified_on": modified},
        }
        svc.session.get = Mock(return_value=response)

        item_count, age = svc._fetch_list_state()

        assert item_count == 250
        assert 110 <= age <= 180

    def test_api_error_returns_none(self):
        svc, _ = _make_service()
        response = Mock()
        response.raise_for_status = Mock()
        response.json.return_value = {"success": False, "errors": [{"message": "bad token"}]}
        svc.session.get = Mock(return_value=response)

        assert svc._fetch_list_state() is None

    def test_missing_modified_on_is_unknown(self):
        svc, _ = _make_service()
        assert svc._modified_age_seconds(None) is None


class TestConnectDatabase:
    """Test database connection setup"""

    def test_with_db_service(self):
        mock_db = Mock()
        mock_conn = Mock()
        mock_db.create_raw_connection.return_value = mock_conn
        svc, _ = _make_service(db_service=mock_db)

        svc.connect_database()

        mock_db.create_raw_connection.assert_called_once()
        assert svc.db_conn == mock_conn

    def test_without_db_service(self):
        svc, _ = _make_service()
        svc.db_service = None
        import importlib

        mod = importlib.import_module("core.services.cloudflare_push_service")
        with patch.object(mod, "psycopg2") as mock_psycopg2:
            mock_conn = Mock()
            mock_psycopg2.connect.return_value = mock_conn

            svc.connect_database()

            assert svc.db_conn == mock_conn

    def test_sets_autocommit_and_listen(self):
        mock_db = Mock()
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_db.create_raw_connection.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        svc, _ = _make_service(db_service=mock_db)

        svc.connect_database()

        mock_conn.set_isolation_level.assert_called_once()
        mock_cursor.execute.assert_called_once_with("LISTEN blacklist_changes;")
