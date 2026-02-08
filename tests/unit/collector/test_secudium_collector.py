import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from datetime import datetime, timedelta
import requests


COLLECTOR_MODULE = "collector.core.secudium_collector"


def _make_mock_config():
    config = MagicMock()
    config.SECUDIUM_BASE_URL = "https://secudium.test.local"
    config.get_secudium_credentials.return_value = ("testuser", "testpass")
    config.REQUEST_TIMEOUT = 30
    config.BATCH_SIZE = 100
    return config


@pytest.fixture
def mock_env(monkeypatch):
    monkeypatch.setenv("SECUDIUM_EMAIL", "test@example.com")
    monkeypatch.setenv("SECUDIUM_EMAIL_PASSWORD", "emailpass")
    monkeypatch.setenv("SECUDIUM_IMAP_SERVER", "imap.test.local")


@pytest.fixture
def collector(mock_env):
    with patch(f"{COLLECTOR_MODULE}.CollectorConfig", _make_mock_config()):
        from collector.core.secudium_collector import SecudiumCollector
        c = SecudiumCollector(db_service=MagicMock())
        c._request_delay = 0
        yield c


@pytest.mark.unit
class TestExtractToken:
    def test_from_json_body(self, collector):
        resp = MagicMock()
        resp.json.return_value = {"X-Auth-Token": "user1:1234567890:abcdef0123456789" + "a" * 46}
        resp.cookies = {}
        resp.headers = {}
        result = collector._extract_token(resp)
        assert result is not None
        assert result.startswith("user1:")

    def test_from_cookie(self, collector):
        resp = MagicMock()
        resp.json.side_effect = ValueError("no json")
        resp.cookies = {}
        resp.headers = {}
        resp.text = ""
        collector.session.cookies = {"token": "user2:9999999999:" + "b" * 64}
        result = collector._extract_token(resp)
        assert result is not None
        assert result.startswith("user2:")

    def test_from_set_cookie_header(self, collector):
        token_val = "user3:1111111111:" + "c" * 64
        resp = MagicMock()
        resp.json.side_effect = ValueError("no json")
        resp.cookies = {}
        resp.headers = {"Set-Cookie": f"token={token_val}; Path=/"}
        resp.text = ""
        result = collector._extract_token(resp)
        assert result == token_val

    def test_no_token_found(self, collector):
        resp = MagicMock()
        resp.json.side_effect = ValueError("no json")
        resp.cookies = {}
        resp.headers = {}
        resp.text = "no token here"
        result = collector._extract_token(resp)
        assert result is None


@pytest.mark.unit
class TestBuildUrl:
    def test_basic_path(self, collector):
        collector._token = "mytoken:123:" + "a" * 64
        url = collector._build_url("/isap-api/test")
        assert "secudium.test.local" in url
        assert "X-Auth-Token=" in url
        assert "mytoken" in url

    def test_with_extra_params(self, collector):
        collector._token = "t:1:" + "a" * 64
        url = collector._build_url("/isap-api/test", {"count": "50", "page": "2"})
        assert "count=50" in url
        assert "page=2" in url
        assert "X-Auth-Token=" in url

    def test_no_token(self, collector):
        collector._token = None
        url = collector._build_url("/isap-api/test")
        assert "X-Auth-Token" not in url
        assert "/isap-api/test" in url


@pytest.mark.unit
class TestTokenCaching:
    def test_fresh_token_is_valid(self, collector):
        from collector.core.secudium_collector import SecudiumCollector
        SecudiumCollector._cached_token = "cached:123:" + "d" * 64
        SecudiumCollector._token_obtained_at = datetime.now()
        with patch.object(collector, "_verify_token", return_value=True):
            assert collector._is_token_valid() is True

    def test_expired_token_is_invalid(self, collector):
        from collector.core.secudium_collector import SecudiumCollector
        SecudiumCollector._cached_token = "cached:123:" + "d" * 64
        SecudiumCollector._token_obtained_at = datetime.now() - timedelta(hours=5)
        assert collector._is_token_valid() is False

    def test_no_cached_token(self, collector):
        from collector.core.secudium_collector import SecudiumCollector
        SecudiumCollector._cached_token = None
        SecudiumCollector._token_obtained_at = None
        assert collector._is_token_valid() is False


@pytest.mark.unit
class TestAuthenticate:
    def test_uses_cached_valid_token(self, collector):
        from collector.core.secudium_collector import SecudiumCollector
        token = "cached:999:" + "e" * 64
        SecudiumCollector._cached_token = token
        SecudiumCollector._token_obtained_at = datetime.now()

        with patch.object(collector, "_verify_token", return_value=True):
            result = collector.authenticate()

        assert result is True
        assert collector._token == token

    @patch(f"{COLLECTOR_MODULE}.OTPEmailReader")
    def test_otp_flow(self, mock_otp_cls, collector):
        from collector.core.secudium_collector import SecudiumCollector
        SecudiumCollector._cached_token = None
        SecudiumCollector._token_obtained_at = None

        mock_otp_instance = MagicMock()
        mock_otp_instance.get_latest_otp.return_value = "123456"
        mock_otp_cls.return_value = mock_otp_instance

        login_results = iter(["otp_required", "success"])

        def mock_login(uid, pw, is_otp="N", otp_value=""):
            return next(login_results)

        with patch.object(collector, "_login", side_effect=mock_login):
            with patch.object(collector, "_verify_token", return_value=True):
                collector._token = "new:111:" + "f" * 64
                result = collector.authenticate()

        assert result is True

    def test_direct_login_success(self, collector):
        from collector.core.secudium_collector import SecudiumCollector
        SecudiumCollector._cached_token = None
        SecudiumCollector._token_obtained_at = None

        with patch.object(collector, "_login", return_value="success"):
            with patch.object(collector, "_verify_token", return_value=True):
                collector._token = "direct:222:" + "f" * 64
                result = collector.authenticate()

        assert result is True

    def test_max_attempts_exceeded(self, collector):
        from collector.core.secudium_collector import SecudiumCollector
        SecudiumCollector._cached_token = None
        SecudiumCollector._token_obtained_at = None

        with patch.object(collector, "_login", return_value="failed"):
            result = collector.authenticate()

        assert result is False


@pytest.mark.unit
class TestLogin:
    def test_successful_login(self, collector):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"X-Auth-Token": "user:123:" + "a" * 64}
        mock_resp.cookies = {}
        mock_resp.headers = {}

        collector.session.post = MagicMock(return_value=mock_resp)

        with patch.object(collector, "_set_token_cookie"):
            with patch.object(collector, "_verify_token", return_value=True):
                result = collector._login("user", "pass", is_otp="N", otp_value="")

        assert result == "success"
        assert collector._token is not None

    def test_otp_required_response(self, collector):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"otp_required": True}
        mock_resp.cookies = {}
        mock_resp.headers = {}
        mock_resp.text = "otp_required"

        collector.session.post = MagicMock(return_value=mock_resp)

        with patch.object(collector, "_extract_token", return_value=None):
            result = collector._login("user", "pass", is_otp="N", otp_value="")

        assert result in ("otp_required", "failed")

    def test_network_error(self, collector):
        collector.session.post = MagicMock(side_effect=requests.RequestException("Connection refused"))
        result = collector._login("user", "pass", is_otp="N", otp_value="")
        assert result == "failed"


@pytest.mark.unit
class TestCollectData:
    def test_auth_failure_returns_error(self, collector):
        with patch.object(collector, "authenticate", return_value=False):
            result = collector.collect_data()

        assert result["success"] is False
        assert len(result["errors"]) > 0

    @patch(f"{COLLECTOR_MODULE}.parse_xls_file")
    @patch(f"{COLLECTOR_MODULE}.extract_download_info")
    @patch(f"{COLLECTOR_MODULE}.parse_black_ip_list")
    def test_successful_collection(self, mock_parse_list, mock_extract_dl, mock_parse_xls, collector):
        mock_parse_list.return_value = [
            {
                "id": 1,
                "title": "Black IP 2026-02-06",
                "date": "2026-02-06",
                "download_html": "<button onclick='download(\"uuid1\", \"file.xls\");'>Down</button>",
            }
        ]
        mock_extract_dl.return_value = ("uuid1", "file.xls")
        mock_parse_xls.return_value = [
            {"ip": "1.2.3.4", "port": 80, "description": "C2", "source_date": "2026-02-06"}
        ]

        mock_list_resp = MagicMock()
        mock_list_resp.status_code = 200
        mock_list_resp.json.return_value = {"rows": [{"id": 1, "data": [""] * 8}]}

        mock_dl_resp = MagicMock()
        mock_dl_resp.status_code = 200
        mock_dl_resp.content = b"fake xls content"
        mock_dl_resp.iter_content = MagicMock(return_value=[b"fake xls content"])

        collector.session.get = MagicMock(side_effect=[mock_list_resp, MagicMock(status_code=200), mock_dl_resp])

        with patch.object(collector, "authenticate", return_value=True):
            with patch.object(collector, "_insert_ips", return_value=1):
                with patch.object(collector, "_logout"):
                    collector._token = "t:1:" + "a" * 64
                    result = collector.collect_data()

        assert result["success"] is True
