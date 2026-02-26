"""Unit tests for core.utils.logger_config."""

import logging


from core.utils.logger_config import (
    StructuredFormatter,
    TaggedLogger,
    setup_logger,
)


class TestStructuredFormatter:
    """Tests for StructuredFormatter."""

    def test_format_returns_string(self):
        formatter = StructuredFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="test message",
            args=(),
            exc_info=None,
        )
        result = formatter.format(record)
        assert isinstance(result, str)

    def test_format_contains_json(self):
        import json

        formatter = StructuredFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="hello world",
            args=(),
            exc_info=None,
        )
        result = formatter.format(record)
        parsed = json.loads(result)
        assert parsed["message"] == "hello world"
        assert parsed["level"] == "INFO"

    def test_format_contains_timestamp(self):
        import json

        formatter = StructuredFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.WARNING,
            pathname="test.py",
            lineno=1,
            msg="warn",
            args=(),
            exc_info=None,
        )
        result = formatter.format(record)
        parsed = json.loads(result)
        assert "timestamp" in parsed


class TestTaggedLogger:
    """Tests for TaggedLogger."""

    def test_with_tags_returns_new_logger(self):
        base_logger = logging.getLogger("test_tagged")
        tagged = TaggedLogger(base_logger, {"service": "test"})
        new_tagged = tagged.with_tags(environment="dev")
        assert isinstance(new_tagged, TaggedLogger)

    def test_log_operation(self):
        base_logger = logging.getLogger("test_op")
        base_logger.setLevel(logging.DEBUG)
        tagged = TaggedLogger(base_logger, {})
        # Should not raise
        tagged.log_operation("test_op", "success", duration=0.5)

    def test_log_metric(self):
        base_logger = logging.getLogger("test_metric")
        base_logger.setLevel(logging.DEBUG)
        tagged = TaggedLogger(base_logger, {})
        # Should not raise
        tagged.log_metric("request_count", 42, unit="count")


class TestSetupLogger:
    """Tests for setup_logger function."""

    def test_returns_tagged_logger(self):
        result = setup_logger("test_setup")
        assert isinstance(result, TaggedLogger)

    def test_default_name(self):
        result = setup_logger()
        assert isinstance(result, TaggedLogger)

    def test_custom_level(self):
        result = setup_logger("test_level", level=logging.DEBUG)
        assert isinstance(result, TaggedLogger)
