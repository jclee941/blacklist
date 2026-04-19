"""System API route modules attached to the shared api_bp."""

from importlib import import_module

import_module(".monitoring", __name__)
import_module(".operations", __name__)
import_module(".schema", __name__)
