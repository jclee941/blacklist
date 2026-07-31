import asyncio
from unittest.mock import MagicMock, Mock, patch


def run_async(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def make_service():
    mock_db = Mock()
    mock_redis = MagicMock()
    with patch("core.services.blacklist_service.redis.Redis", return_value=mock_redis):
        from core.services.blacklist_service import BlacklistService

        svc = BlacklistService(db_service=mock_db)
    svc.repo = Mock()
    svc.redis_client = mock_redis
    svc.db_service = mock_db
    return svc, mock_db, mock_redis
