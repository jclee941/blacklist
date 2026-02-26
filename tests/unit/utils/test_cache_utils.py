"""Unit tests for core.utils.cache_utils."""

from unittest.mock import patch, MagicMock


class TestGetRedisClient:
    """Tests for get_redis_client function."""

    @patch("core.utils.cache_utils.redis.Redis")
    def test_returns_redis_client(self, mock_redis_cls):
        from core.utils.cache_utils import get_redis_client

        mock_client = MagicMock()
        mock_redis_cls.return_value = mock_client
        mock_client.ping.return_value = True
        result = get_redis_client()
        assert result is not None

    @patch("core.utils.cache_utils.redis.Redis")
    def test_returns_none_on_error(self, mock_redis_cls):
        from core.utils.cache_utils import get_redis_client

        mock_redis_cls.side_effect = Exception("Connection refused")
        result = get_redis_client()
        assert result is None


class TestSerializeDeserialize:
    """Tests for _serialize_value and _deserialize_value."""

    def test_serialize_dict(self):
        from core.utils.cache_utils import _serialize_value

        result = _serialize_value({"key": "value"})
        assert isinstance(result, str)
        assert "key" in result

    def test_serialize_list(self):
        from core.utils.cache_utils import _serialize_value

        result = _serialize_value([1, 2, 3])
        assert isinstance(result, str)

    def test_serialize_string(self):
        from core.utils.cache_utils import _serialize_value

        result = _serialize_value("hello")
        assert result == "hello"

    def test_deserialize_json(self):
        from core.utils.cache_utils import _deserialize_value

        result = _deserialize_value('{"key": "value"}')
        assert isinstance(result, dict)
        assert result["key"] == "value"

    def test_deserialize_plain_string(self):
        from core.utils.cache_utils import _deserialize_value

        result = _deserialize_value("hello")
        assert result == "hello"


class TestCacheManager:
    """Tests for CacheManager class."""

    def test_init_with_defaults(self):
        from core.utils.cache_utils import CacheManager

        manager = CacheManager()
        assert manager.ttl == 300

    def test_init_with_custom_ttl(self):
        from core.utils.cache_utils import CacheManager

        manager = CacheManager(ttl=600)
        assert manager.ttl == 600

    def test_init_with_prefix(self):
        from core.utils.cache_utils import CacheManager

        manager = CacheManager(key_prefix="test:")
        assert manager.key_prefix == "test:"

    def test_get_returns_default_when_no_redis(self):
        from core.utils.cache_utils import CacheManager

        with patch("core.utils.cache_utils.get_redis_client", return_value=None):
            manager = CacheManager()
            result = manager.get("nonexistent", default="fallback")
            assert result == "fallback"

    def test_set_returns_gracefully_when_no_redis(self):
        from core.utils.cache_utils import CacheManager

        with patch("core.utils.cache_utils.get_redis_client", return_value=None):
            manager = CacheManager()
            # Should not raise
            manager.set("key", "value")

    def test_delete_returns_gracefully_when_no_redis(self):
        from core.utils.cache_utils import CacheManager

        with patch("core.utils.cache_utils.get_redis_client", return_value=None):
            manager = CacheManager()
            # Should not raise
            manager.delete("key")

    def test_exists_returns_false_when_no_redis(self):
        from core.utils.cache_utils import CacheManager

        with patch("core.utils.cache_utils.get_redis_client", return_value=None):
            manager = CacheManager()
            assert manager.exists("key") is False


class TestCachedDecorator:
    """Tests for @cached decorator."""

    def test_cached_calls_function_on_miss(self):
        from core.utils.cache_utils import cached

        call_count = 0

        # Must patch get_redis_client BEFORE the decorator creates CacheManager
        with patch("core.utils.cache_utils.get_redis_client", return_value=None):

            @cached(ttl=60)
            def my_func(x):
                nonlocal call_count
                call_count += 1
                return x * 2

            result = my_func(5)
            assert result == 10
            assert call_count == 1
