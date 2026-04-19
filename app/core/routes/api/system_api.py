"""
시스템 관리 API 엔드포인트

Compatibility shim that loads the modular system route package.
"""

from importlib import import_module

import_module(".system", __package__)
