"""Unit tests for core.auth.decorators."""

from core.auth.decorators import public


class TestPublicDecorator:
    """Tests for the @public decorator."""

    def test_sets_public_attribute(self):
        """Decorated function should have _public=True."""

        @public
        def my_view():
            return "ok"

        assert hasattr(my_view, "_public")
        assert my_view._public is True

    def test_preserves_function_behavior(self):
        """Decorated function should still be callable and return normally."""

        @public
        def my_view():
            return "hello"

        assert my_view() == "hello"

    def test_preserves_function_name(self):
        """Decorated function should preserve its original name."""

        @public
        def some_unique_name():
            pass

        assert some_unique_name.__name__ == "some_unique_name"

    def test_works_with_args(self):
        """Decorated function should work with arguments."""

        @public
        def add(a, b):
            return a + b

        assert add(2, 3) == 5
        assert add._public is True

    def test_works_with_kwargs(self):
        """Decorated function should work with keyword arguments."""

        @public
        def greet(name="world"):
            return f"hello {name}"

        assert greet(name="test") == "hello test"
        assert greet._public is True

    def test_multiple_decorations_idempotent(self):
        """Applying @public multiple times should be harmless."""

        @public
        @public
        def my_view():
            return "ok"

        assert my_view._public is True
        assert my_view() == "ok"
