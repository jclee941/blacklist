"""Tests for collector/config.py — CollectorConfig class."""

import pytest
from unittest.mock import patch, MagicMock


class TestCollectorConfigMethods:
    def setup_method(self):
        from collector.config import CollectorConfig

        self.cfg = CollectorConfig
        self.cfg._credentials_cache = {}
        self.cfg._cache_loaded = False

    def test_get_db_connection_string(self):
        conn_str = self.cfg.get_db_connection_string()
        assert "postgresql://" in conn_str
        assert "blacklist_collector_optimized" in conn_str

    def test_get_redis_connection_params_no_password(self):
        self.cfg.REDIS_PASSWORD = ""
        params = self.cfg.get_redis_connection_params()
        assert params["host"] == self.cfg.REDIS_HOST
        assert "password" not in params

    def test_get_redis_connection_params_with_password(self):
        self.cfg.REDIS_PASSWORD = "secret"
        params = self.cfg.get_redis_connection_params()
        assert params["password"] == "secret"
        self.cfg.REDIS_PASSWORD = ""

    def test_get_performance_config(self):
        perf = self.cfg.get_performance_config()
        assert "batch_size" in perf
        assert "page_size" in perf
        assert "max_pages" in perf

    def test_get_database_optimization_params(self):
        opt = self.cfg.get_database_optimization_params()
        assert "work_mem" in opt
        assert "maintenance_work_mem" in opt

    def test_validate_config_success(self):
        assert self.cfg.validate_config() is True

    @patch.object(__import__("collector.config", fromlist=["CollectorConfig"]).CollectorConfig, "POSTGRES_HOST", "")
    def test_validate_config_missing_host(self):
        from collector.config import CollectorConfig

        assert CollectorConfig.validate_config() is False

    def test_validate_config_invalid_batch_size(self):
        orig = self.cfg.BATCH_SIZE
        self.cfg.BATCH_SIZE = 0
        assert self.cfg.validate_config() is False
        self.cfg.BATCH_SIZE = orig

    def test_validate_config_invalid_page_size(self):
        orig = self.cfg.PAGE_SIZE
        self.cfg.PAGE_SIZE = 6000
        assert self.cfg.validate_config() is False
        self.cfg.PAGE_SIZE = orig


class TestGetCredentials:
    def setup_method(self):
        from collector.config import CollectorConfig

        self.cfg = CollectorConfig
        self.cfg._credentials_cache = {}
        self.cfg._cache_loaded = False

    def test_regtech_from_env(self):
        self.cfg.REGTECH_ID = "env_user"
        self.cfg.REGTECH_PW = "env_pass"
        result = self.cfg.get_regtech_credentials()
        assert result == ("env_user", "env_pass")
        self.cfg.REGTECH_ID = ""
        self.cfg.REGTECH_PW = ""

    def test_secudium_from_env(self):
        self.cfg.SECUDIUM_ID = "sec_user"
        self.cfg.SECUDIUM_PW = "sec_pass"
        result = self.cfg.get_secudium_credentials()
        assert result == ("sec_user", "sec_pass")
        self.cfg.SECUDIUM_ID = ""
        self.cfg.SECUDIUM_PW = ""

    @patch("collector.config.psycopg2")
    def test_regtech_from_db_fallback(self, mock_psycopg2):
        self.cfg.REGTECH_ID = ""
        self.cfg.REGTECH_PW = ""

        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_cur.fetchall.return_value = []
        mock_conn.cursor.return_value = mock_cur
        mock_psycopg2.connect.return_value = mock_conn

        uid, pw = self.cfg.get_regtech_credentials()
        assert uid == ""
        assert pw == ""

    @patch("collector.config.psycopg2")
    def test_db_load_failure_returns_empty(self, mock_psycopg2):
        self.cfg.REGTECH_ID = ""
        self.cfg.REGTECH_PW = ""
        mock_psycopg2.connect.side_effect = RuntimeError("no db")

        uid, pw = self.cfg.get_regtech_credentials()
        assert uid == ""
        assert pw == ""

    def test_to_dict(self):
        self.cfg.REGTECH_ID = "u"
        self.cfg.REGTECH_PW = "p"
        d = self.cfg.to_dict()
        assert d["regtech_id"] == "u"
        assert d["batch_size"] > 0
        self.cfg.REGTECH_ID = ""
        self.cfg.REGTECH_PW = ""
