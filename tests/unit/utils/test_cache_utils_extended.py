"""Extended tests for core.utils.cache_utils — Redis-backed paths, _record_metric, clear_pattern."""

import json
from unittest.mock import MagicMock, Mock, patch

import pytest


class TestCacheManagerWithRedis:
    """Tests for CacheManager when redis_client is available."""

    def _make_manager(self):
        mock_redis = MagicMock()
        with patch("core.utils.cache_utils.get_redis_client", return_value=mock_redis):
            from core.utils.cache_utils import CacheManager

            mgr = CacheManager(ttl=300, key_prefix="test")
        return mgr, mock_redis

    def test_get_cache_hit(self):
        mgr, mock_redis = self._make_manager()
        mock_redis.get.return_value = json.dumps({"key": "value"}).encode()
        result = mgr.get("mykey")
        assert result == {"key": "value"}
        mock_redis.get.assert_called_once_with("test:mykey")

    def test_get_cache_miss(self):
        mgr, mock_redis = self._make_manager()
        mock_redis.get.return_value = None
        result = mgr.get("mykey", default="fallback")
        assert result == "fallback"

    def test_get_redis_exception(self):
        mgr, mock_redis = self._make_manager()
        mock_redis.get.side_effect = Exception("Redis down")
        result = mgr.get("mykey", default="safe")
        assert result == "safe"

    def test_set_success(self):
        mgr, mock_redis = self._make_manager()
        result = mgr.set("mykey", {"data": 1}, ttl=60)
        assert result is True
        mock_redis.setex.assert_called_once()
        args = mock_redis.setex.call_args
        assert args[0][0] == "test:mykey"
        assert args[0][1] == 60

    def test_set_default_ttl(self):
        mgr, mock_redis = self._make_manager()
        mgr.set("mykey", "val")
        args = mock_redis.setex.call_args
        assert args[0][1] == 300

    def test_set_redis_exception(self):
        mgr, mock_redis = self._make_manager()
        mock_redis.setex.side_effect = Exception("Redis down")
        result = mgr.set("mykey", "val")
        assert result is False

    def test_delete_success(self):
        mgr, mock_redis = self._make_manager()
        mock_redis.delete.return_value = 1
        result = mgr.delete("mykey")
        assert result is True
        mock_redis.delete.assert_called_once_with("test:mykey")

    def test_delete_redis_exception(self):
        mgr, mock_redis = self._make_manager()
        mock_redis.delete.side_effect = Exception("Redis down")
        result = mgr.delete("mykey")
        assert result is False

    def test_exists_true(self):
        mgr, mock_redis = self._make_manager()
        mock_redis.exists.return_value = 1
        assert mgr.exists("mykey") is True

    def test_exists_false(self):
        mgr, mock_redis = self._make_manager()
        mock_redis.exists.return_value = 0
        assert mgr.exists("mykey") is False

    def test_exists_redis_exception(self):
        mgr, mock_redis = self._make_manager()
        mock_redis.exists.side_effect = Exception("Redis down")
        assert mgr.exists("mykey") is False

    def test_clear_pattern_with_keys(self):
        mgr, mock_redis = self._make_manager()
        mock_redis.keys.return_value = [b"test:a", b"test:b", b"test:c"]
        mock_redis.delete.return_value = 3
        result = mgr.clear_pattern("test:*")
        assert result == 3

    def test_clear_pattern_no_keys(self):
        mgr, mock_redis = self._make_manager()
        mock_redis.keys.return_value = []
        result = mgr.clear_pattern("test:*")
        assert result == 0

    def test_clear_pattern_exception(self):
        mgr, mock_redis = self._make_manager()
        mock_redis.keys.side_effect = Exception("Redis down")
        result = mgr.clear_pattern("test:*")
        assert result == 0


class TestCachedDecorator:
    """Tests for the @cached decorator with actual cache hits."""

    def test_cached_hit(self):
        mock_redis = MagicMock()
        cached_value = json.dumps({"cached": True}).encode()
        mock_redis.get.return_value = cached_value

        with patch("core.utils.cache_utils.get_redis_client", return_value=mock_redis):
            from core.utils.cache_utils import cached

            @cached(ttl=60, key_prefix="fn:")
            def my_func(x):
                return {"computed": x}

            result = my_func(42)
            assert result == {"cached": True}

    def test_cached_miss_stores_result(self):
        mock_redis = MagicMock()
        mock_redis.get.return_value = None

        with patch("core.utils.cache_utils.get_redis_client", return_value=mock_redis):
            from core.utils.cache_utils import cached

            @cached(ttl=60, key_prefix="fn:")
            def my_func2(x):
                return {"computed": x}

            result = my_func2(42)
            assert result == {"computed": 42}
            mock_redis.setex.assert_called_once()


class TestRecordMetric:
    """Tests for _record_metric module-level function."""

    def test_record_metric_outside_app_context(self):
        from core.utils.cache_utils import _record_metric

        _record_metric("record_hit", key="test")

    def test_record_metric_callable(self):
        from core.utils.cache_utils import _record_metric

        assert callable(_record_metric)


class TestGetRedisClient:
    """Tests for get_redis_client."""

    def test_get_redis_client_success(self):
        mock_redis_cls = MagicMock()
        with patch("core.utils.cache_utils.redis.Redis", mock_redis_cls):
            with patch(
                "core.utils.cache_utils.os.environ.get",
                side_effect=lambda k, d=None: {"REDIS_HOST": "localhost", "REDIS_PORT": "6379", "REDIS_DB": "0"}.get(
                    k, d
                ),
            ):
                from core.utils.cache_utils import get_redis_client

                client = get_redis_client()
                assert client is not None

    def test_get_redis_client_exception(self):
        with patch("core.utils.cache_utils.redis.Redis", side_effect=Exception("no redis")):
            from core.utils.cache_utils import get_redis_client

            client = get_redis_client()
            assert client is None
