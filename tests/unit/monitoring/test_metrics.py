"""Tests for core.monitoring.metrics — decorators, helper functions, update_entries_count."""

from unittest.mock import MagicMock, Mock, patch, PropertyMock
import pytest


class TestTrackBlacklistQueryDecorator:
    def test_track_query_hit(self):
        from core.monitoring.metrics import track_blacklist_query

        mock_counter = MagicMock()
        with patch("core.monitoring.metrics.blacklist_queries_total", mock_counter):

            @track_blacklist_query("lookup")
            def my_func():
                return {"blocked": True}

            result = my_func()
            assert result == {"blocked": True}
            mock_counter.labels.assert_called()

    def test_track_query_miss(self):
        from core.monitoring.metrics import track_blacklist_query

        mock_counter = MagicMock()
        with patch("core.monitoring.metrics.blacklist_queries_total", mock_counter):

            @track_blacklist_query("lookup")
            def my_func():
                return {"blocked": False}

            result = my_func()
            assert result == {"blocked": False}

    def test_track_query_error(self):
        from core.monitoring.metrics import track_blacklist_query

        mock_counter = MagicMock()
        with patch("core.monitoring.metrics.blacklist_queries_total", mock_counter):

            @track_blacklist_query("lookup")
            def my_func():
                raise ValueError("boom")

            with pytest.raises(ValueError):
                my_func()


class TestTrackDbOperationDecorator:
    def test_track_db_success(self):
        from core.monitoring.metrics import track_db_operation

        mock_ops = MagicMock()
        mock_duration = MagicMock()
        with (
            patch("core.monitoring.metrics.blacklist_db_operations_total", mock_ops),
            patch("core.monitoring.metrics.blacklist_db_operation_duration_seconds", mock_duration),
        ):

            @track_db_operation("query")
            def my_func():
                return [{"id": 1}]

            result = my_func()
            assert result == [{"id": 1}]

    def test_track_db_error(self):
        from core.monitoring.metrics import track_db_operation

        mock_ops = MagicMock()
        mock_duration = MagicMock()
        with (
            patch("core.monitoring.metrics.blacklist_db_operations_total", mock_ops),
            patch("core.monitoring.metrics.blacklist_db_operation_duration_seconds", mock_duration),
        ):

            @track_db_operation("insert")
            def my_func():
                raise RuntimeError("db down")

            with pytest.raises(RuntimeError):
                my_func()


class TestUpdateEntriesCount:
    def test_update_entries_count(self):
        from core.monitoring.metrics import update_entries_count

        mock_gauge = MagicMock()
        with patch("core.monitoring.metrics.blacklist_entries_total", mock_gauge):
            update_entries_count("malware", 42)
            mock_gauge.labels.assert_called_once_with(category="malware")
            mock_gauge.labels.return_value.set.assert_called_once_with(42)


class TestMetricHelpers:
    def test_get_or_create_counter_new(self):
        from core.monitoring.metrics import _get_or_create_counter

        with patch("core.monitoring.metrics._metrics_cache", {}):
            with patch("core.monitoring.metrics._metric_exists", return_value=False):
                from prometheus_client import Counter, REGISTRY

                name = "test_helper_counter_unique_1234"
                try:
                    counter = _get_or_create_counter(name, "test", ["label1"])
                    assert counter is not None
                finally:
                    if name + "_total" in REGISTRY._names_to_collectors:
                        REGISTRY.unregister(REGISTRY._names_to_collectors[name + "_total"])
                    elif name + "_created" in REGISTRY._names_to_collectors:
                        REGISTRY.unregister(REGISTRY._names_to_collectors[name + "_created"])

    def test_get_or_create_counter_cached(self):
        mock_counter = MagicMock()
        cache = {"cached_counter": mock_counter}
        with patch("core.monitoring.metrics._metrics_cache", cache):
            from core.monitoring.metrics import _get_or_create_counter

            result = _get_or_create_counter("cached_counter", "test", ["l"])
            assert result is mock_counter

    def test_metric_exists_false(self):
        from core.monitoring.metrics import _metric_exists

        assert _metric_exists("nonexistent_metric_xyz_999") is False


class TestMetricsView:
    def test_metrics_view(self):
        from core.monitoring.metrics import metrics_view

        result = metrics_view()
        assert isinstance(result, tuple)
        assert result[1] == 200
        body = result[0]
        assert isinstance(body, bytes)


class TestSetupMetrics:
    def test_setup_metrics_registers_hooks(self):
        from core.monitoring.metrics import setup_metrics

        mock_app = MagicMock()
        mock_app.config = {"VERSION": "1.0.0"}
        setup_metrics(mock_app)
        mock_app.before_request.assert_called_once()
        mock_app.after_request.assert_called_once()
        mock_app.errorhandler.assert_called_once_with(404)
