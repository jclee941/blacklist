from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from unittest.mock import MagicMock

import pytest


def test_app_server_loads_the_internal_service_certificate(monkeypatch: pytest.MonkeyPatch) -> None:
    flask_app = MagicMock()
    core_app = ModuleType("core.app")
    setattr(core_app, "create_app", lambda: flask_app)
    monkeypatch.setitem(sys.modules, "core.app", core_app)
    monkeypatch.setenv("INTERNAL_TLS_CERT", "/probe/tls.crt")
    monkeypatch.setenv("INTERNAL_TLS_KEY", "/probe/tls.key")
    module_path = Path(__file__).parents[2] / "app" / "run_app.py"
    spec = importlib.util.spec_from_file_location("app_server_tls_probe", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    module.run_server()

    flask_app.run.assert_called_once_with(
        host="0.0.0.0",
        port=2542,
        debug=False,
        ssl_context=("/probe/tls.crt", "/probe/tls.key"),
    )
