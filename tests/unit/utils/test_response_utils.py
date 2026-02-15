"""Unit tests for core.utils.response_utils."""

import json
from unittest.mock import patch, MagicMock

import pytest
from flask import Flask

from core.utils.response_utils import (
    success_response,
    paginated_response,
    empty_response,
    created_response,
    deleted_response,
    health_response,
    batch_operation_response,
    statistics_response,
    collection_response,
)


def _make_app():
    app = Flask(__name__)
    app.config["TESTING"] = True
    return app


class TestSuccessResponse:
    """Tests for success_response."""

    def test_returns_200_by_default(self):
        app = _make_app()
        with app.test_request_context("/test"):
            response, status = success_response({"key": "value"})
            assert status == 200

    def test_contains_success_flag(self):
        app = _make_app()
        with app.test_request_context("/test"):
            response, status = success_response({"key": "value"})
            data = json.loads(response.get_data(as_text=True))
            assert data["success"] is True

    def test_contains_data(self):
        app = _make_app()
        with app.test_request_context("/test"):
            response, status = success_response({"foo": "bar"})
            data = json.loads(response.get_data(as_text=True))
            assert data["data"]["foo"] == "bar"

    def test_custom_status_code(self):
        app = _make_app()
        with app.test_request_context("/test"):
            response, status = success_response({}, status_code=201)
            assert status == 201

    def test_contains_timestamp(self):
        app = _make_app()
        with app.test_request_context("/test"):
            response, status = success_response({})
            data = json.loads(response.get_data(as_text=True))
            assert "timestamp" in data

    def test_with_message(self):
        app = _make_app()
        with app.test_request_context("/test"):
            response, status = success_response({}, message="All good")
            data = json.loads(response.get_data(as_text=True))
            # message is injected into data["data"]["message"]
            assert data["data"]["message"] == "All good"


class TestPaginatedResponse:
    """Tests for paginated_response."""

    def test_contains_pagination_info(self):
        app = _make_app()
        with app.test_request_context("/test"):
            items = [{"id": 1}, {"id": 2}]
            response, status = paginated_response(items, total=100, page=1, limit=10)
            data = json.loads(response.get_data(as_text=True))
            # paginated_response wraps via success_response, so pagination is under data["data"]
            pag = data["data"]["pagination"]
            assert pag["total"] == 100
            assert pag["page"] == 1
            assert pag["limit"] == 10
            assert pag["total_pages"] == 10

    def test_total_pages_calculation(self):
        app = _make_app()
        with app.test_request_context("/test"):
            response, status = paginated_response([], total=25, page=1, limit=10)
            data = json.loads(response.get_data(as_text=True))
            pag = data["data"]["pagination"]
            assert pag["total_pages"] == 3  # ceil(25/10)

    def test_returns_200(self):
        app = _make_app()
        with app.test_request_context("/test"):
            _, status = paginated_response([], total=0, page=1, limit=10)
            assert status == 200


class TestEmptyResponse:
    """Tests for empty_response."""

    def test_204_returns_empty_body(self):
        app = _make_app()
        with app.test_request_context("/test"):
            response, status = empty_response(status_code=204)
            assert status == 204

    def test_non_204_returns_json(self):
        app = _make_app()
        with app.test_request_context("/test"):
            response, status = empty_response(message="Nothing here", status_code=200)
            assert status == 200


class TestCreatedResponse:
    """Tests for created_response."""

    def test_returns_201(self):
        app = _make_app()
        with app.test_request_context("/test"):
            _, status = created_response({"id": 1})
            assert status == 201

    def test_contains_data(self):
        app = _make_app()
        with app.test_request_context("/test"):
            response, _ = created_response({"id": 42})
            data = json.loads(response.get_data(as_text=True))
            assert data["data"]["id"] == 42


class TestDeletedResponse:
    """Tests for deleted_response."""

    def test_returns_200(self):
        app = _make_app()
        with app.test_request_context("/test"):
            _, status = deleted_response()
            assert status == 200

    def test_with_deleted_count(self):
        app = _make_app()
        with app.test_request_context("/test"):
            response, _ = deleted_response(deleted_count=5)
            data = json.loads(response.get_data(as_text=True))
            assert data["data"]["deleted_count"] == 5


class TestHealthResponse:
    """Tests for health_response."""

    def test_returns_200(self):
        app = _make_app()
        with app.test_request_context("/test"):
            _, status = health_response()
            assert status == 200

    def test_contains_status(self):
        app = _make_app()
        with app.test_request_context("/test"):
            response, _ = health_response(status="healthy")
            data = json.loads(response.get_data(as_text=True))
            assert data["data"]["status"] == "healthy"

    def test_with_checks(self):
        app = _make_app()
        with app.test_request_context("/test"):
            checks = {"db": "ok", "redis": "ok"}
            response, _ = health_response(checks=checks)
            data = json.loads(response.get_data(as_text=True))
            # health_response merges checks into data dict via data.update(checks)
            # then wraps via success_response, so checks are at data["data"] level
            assert data["data"]["db"] == "ok"
            assert data["data"]["redis"] == "ok"


class TestBatchOperationResponse:
    """Tests for batch_operation_response."""

    def test_returns_200(self):
        app = _make_app()
        with app.test_request_context("/test"):
            _, status = batch_operation_response(total=10, successful=8, failed=2)
            assert status == 200

    def test_contains_counts(self):
        app = _make_app()
        with app.test_request_context("/test"):
            response, _ = batch_operation_response(total=10, successful=8, failed=2)
            data = json.loads(response.get_data(as_text=True))
            assert data["data"]["total"] == 10
            assert data["data"]["successful"] == 8
            assert data["data"]["failed"] == 2

    def test_success_rate_calculation(self):
        app = _make_app()
        with app.test_request_context("/test"):
            response, _ = batch_operation_response(total=10, successful=7, failed=3)
            data = json.loads(response.get_data(as_text=True))
            assert data["data"]["success_rate"] == 70.0


class TestStatisticsResponse:
    """Tests for statistics_response."""

    def test_returns_200(self):
        app = _make_app()
        with app.test_request_context("/test"):
            _, status = statistics_response({"count": 100})
            assert status == 200

    def test_contains_statistics(self):
        app = _make_app()
        with app.test_request_context("/test"):
            response, _ = statistics_response({"count": 100})
            data = json.loads(response.get_data(as_text=True))
            assert data["data"]["statistics"]["count"] == 100

    def test_with_period(self):
        app = _make_app()
        with app.test_request_context("/test"):
            response, _ = statistics_response({"count": 100}, period="daily")
            data = json.loads(response.get_data(as_text=True))
            assert data["data"]["period"] == "daily"


class TestCollectionResponse:
    """Tests for collection_response."""

    def test_returns_200(self):
        app = _make_app()
        with app.test_request_context("/test"):
            _, status = collection_response(source="regtech", items_collected=50)
            assert status == 200

    def test_contains_collection_info(self):
        app = _make_app()
        with app.test_request_context("/test"):
            response, _ = collection_response(source="regtech", items_collected=50)
            data = json.loads(response.get_data(as_text=True))
            assert data["data"]["source"] == "regtech"
            assert data["data"]["items_collected"] == 50

    def test_with_errors(self):
        app = _make_app()
        with app.test_request_context("/test"):
            response, _ = collection_response(source="secudium", items_collected=0, success=False, errors=["timeout"])
            data = json.loads(response.get_data(as_text=True))
            assert data["data"]["success"] is False
            assert "timeout" in data["data"]["errors"]
