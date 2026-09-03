"""
API Routes Package

RESTful API endpoints for the blacklist platform.
"""

from ..api_routes import api_bp
from .dashboard_api import dashboard_bp

# Register dashboard blueprint
api_bp.register_blueprint(dashboard_bp, url_prefix="/dashboard")

# Register IP management blueprint
from .ip_management import ip_management_api_bp, ip_management_legacy_bp

api_bp.register_blueprint(ip_management_api_bp)

from .monitoring import monitoring_bp

api_bp.register_blueprint(monitoring_bp)

# Import collection_api (it attaches routes to api_bp directly)
#
from . import system_api
from .database_api import database_api_bp

api_bp.register_blueprint(database_api_bp)
# Register Fortinet blueprints
from .fortinet import (
    fortinet_core_bp,
    fortinet_logs_bp,
    fortinet_management_bp,
    fortinet_feed_bp,
)

api_bp.register_blueprint(fortinet_core_bp, url_prefix="/fortinet")
api_bp.register_blueprint(fortinet_logs_bp, url_prefix="/fortinet")
api_bp.register_blueprint(fortinet_management_bp, url_prefix="/fortinet")
api_bp.register_blueprint(fortinet_feed_bp, url_prefix="/fortinet")
from .analytics import detection_bp

api_bp.register_blueprint(detection_bp)

from . import core_api
from . import dashboard_api
from . import error_metrics_api

from .settings_api import settings_api_bp

api_bp.register_blueprint(settings_api_bp)

from .collection.credentials import collection_credentials_bp

api_bp.register_blueprint(collection_credentials_bp, url_prefix="/collection")

from .collection.status import collection_status_bp
from .collection.trigger import collection_trigger_bp
from .collection.history import collection_history_bp
from .collection.sync import collection_sync_bp
from .collection.config import collection_config_bp
from .collection.sources import sources_bp

api_bp.register_blueprint(collection_status_bp, url_prefix="/collection")
api_bp.register_blueprint(collection_trigger_bp, url_prefix="/collection")
api_bp.register_blueprint(collection_history_bp, url_prefix="/collection")
api_bp.register_blueprint(collection_sync_bp)
api_bp.register_blueprint(collection_config_bp)
api_bp.register_blueprint(sources_bp, url_prefix="/collection")
