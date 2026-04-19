#!/usr/bin/env python3
"""
Service Factory - Centralized Service Initialization
Implements dependency injection pattern for Flask application

This factory:
1. Initializes all 14 application services in correct dependency order
2. Returns service container dictionary
3. Manages service dependencies explicitly
4. Eliminates 100+ redundant imports in route files

Usage:
    from core.services.service_factory import initialize_services

    services = initialize_services(app)
    for name, instance in services.items():
        app.extensions[name] = instance

Service Categories:
- Core Infrastructure: database_service
- Collection Services: collection_service, scheduler_service
- Integration Services: cloudflare_service
- Configuration Services: credential_service, secure_credential_service, regtech_config_service, settings_service
- Business Logic: blacklist_service, analytics_service, scoring_service, expiry_service, ab_test_service

Created: 2025-11-21 (Service DI Improvement - HIGH PRIORITY #2)
"""

from typing import Dict, Any
from flask import Flask
import logging

logger = logging.getLogger(__name__)


def initialize_services(app: Flask) -> Dict[str, Any]:
    """
    Initialize all application services and return service container

    Services are initialized in dependency order:
    1. Core infrastructure (no dependencies)
    2. Services depending on infrastructure
    3. Collection and integration services
    4. Configuration services
    5. Business logic services

    Args:
        app: Flask application instance

    Returns:
        Dictionary mapping service names to initialized service instances

    Example:
        services = initialize_services(app)
        db_service = services['db_service']
        blacklist_service = services['blacklist_service']
    """
    services = {}

    logger.info("🔧 Initializing application services...")

    # ============================================================
    # 1. CORE INFRASTRUCTURE (No Dependencies)
    # ============================================================

    try:
        from .database_service import DatabaseService

        # Initialize DatabaseService instance
        db_service = DatabaseService()
        services["db_service"] = db_service
        logger.info("  ✅ db_service (DatabaseService)")
    except Exception as e:
        logger.error(f"  ❌ Failed to initialize db_service: {e}")

    # ============================================================
    # 2. SERVICES DEPENDING ON DB_SERVICE
    # ============================================================

    # Blacklist Service - Core IP filtering logic
    try:
        from .blacklist_service import BlacklistService

        blacklist_service = BlacklistService(db_service=services["db_service"])
        services["blacklist_service"] = blacklist_service
        logger.info("  ✅ blacklist_service (BlacklistService) - using DatabaseService pool")
    except Exception as e:
        logger.error(f"  ❌ Failed to initialize blacklist_service: {e}")

    # Analytics Service - Analytics and reporting
    try:
        from .analytics_service import AnalyticsService

        analytics_service = AnalyticsService(db_service=services["db_service"])
        services["analytics_service"] = analytics_service
        logger.info("  ✅ analytics_service (AnalyticsService) - using DatabaseService pool")
    except Exception as e:
        logger.error(f"  ❌ Failed to initialize analytics_service: {e}")

    # ============================================================
    # 3. COLLECTION SERVICES
    # ============================================================

    # Collection Service - Collection orchestration
    try:
        from .collection_service import CollectionService

        collection_service = CollectionService(db_service=services["db_service"])
        services["collection_service"] = collection_service
        logger.info("  ✅ collection_service (CollectionService)")
    except Exception as e:
        logger.error(f"  ❌ Failed to initialize collection_service: {e}")

    # Scheduler Service - Collection scheduling
    try:
        from .scheduler_service import CollectionScheduler

        scheduler_service = CollectionScheduler(db_service=services["db_service"])
        services["scheduler_service"] = scheduler_service
        logger.info("  ✅ scheduler_service (CollectionScheduler) - using DatabaseService pool")
    except Exception as e:
        logger.error(f"  ❌ Failed to initialize scheduler_service: {e}")

    # ============================================================
    # 4. INTEGRATION SERVICES
    # ============================================================

    # Cloudflare Service - Cloudflare Lists API push integration
    try:
        from .cloudflare_push_service import CloudflarePushService

        cloudflare_service = CloudflarePushService(db_service=services["db_service"])
        services["cloudflare_service"] = cloudflare_service
        logger.info("  ✅ cloudflare_service (CloudflarePushService)")
    except Exception as e:
        logger.error(f"  ❌ Failed to initialize cloudflare_service: {e}")

    # ============================================================
    # 5. CONFIGURATION SERVICES
    # ============================================================

    # Credential Service - Credential CRUD operations
    try:
        from .credential_service import CredentialService

        credential_service = CredentialService(db_service=services["db_service"])
        services["credential_service"] = credential_service
        logger.info("  ✅ credential_service (CredentialService)")
    except Exception as e:
        logger.error(f"  ❌ Failed to initialize credential_service: {e}")

    # Secure Credential Service - AES-256-GCM encryption
    try:
        from .secure_credential_service import SecureCredentialService

        secure_credential_service = SecureCredentialService(db_service=services["db_service"])
        services["secure_credential_service"] = secure_credential_service
        logger.info("  ✅ secure_credential_service (SecureCredentialService)")
    except Exception as e:
        logger.error(f"  ❌ Failed to initialize secure_credential_service: {e}")

    # REGTECH Config Service - REGTECH configuration management
    try:
        from .regtech_config_service import RegtechConfigService

        regtech_config_service = RegtechConfigService()
        services["regtech_config_service"] = regtech_config_service
        logger.info("  ✅ regtech_config_service (RegtechConfigService)")
    except Exception as e:
        logger.error(f"  ❌ Failed to initialize regtech_config_service: {e}")

    # Settings Service - System settings persistence
    try:
        from .settings_service import SettingsService

        settings_service = SettingsService(db_service=services["db_service"])
        services["settings_service"] = settings_service
        logger.info("  ✅ settings_service (SettingsService)")
    except Exception as e:
        logger.error(f"  ❌ Failed to initialize settings_service: {e}")

    # ============================================================
    # 6. BUSINESS LOGIC SERVICES
    # ============================================================

    # Scoring Service - Risk scoring
    try:
        from .scoring_service import scoring_service

        services["scoring_service"] = scoring_service
        logger.info("  ✅ scoring_service (ScoringService)")
    except Exception as e:
        logger.error(f"  ❌ Failed to initialize scoring_service: {e}")

    # Expiry Service - IP expiration handling
    try:
        from .expiry_service import IPExpiryService

        expiry_service = IPExpiryService(db_service=services["db_service"])
        services["expiry_service"] = expiry_service
        logger.info("  ✅ expiry_service (IPExpiryService) - using DatabaseService pool")
    except Exception as e:
        logger.error(f"  ❌ Failed to initialize expiry_service: {e}")

    # A/B Test Service - A/B testing utilities
    try:
        from .ab_test_service import ABTestService

        ab_test_service = ABTestService()
        services["ab_test_service"] = ab_test_service
        logger.info("  ✅ ab_test_service (ABTestService)")
    except Exception as e:
        logger.error(f"  ❌ Failed to initialize ab_test_service: {e}")

    # Optimized Blacklist Service - Performance optimized filtering
    try:
        from .optimized_blacklist_service import OptimizedBlacklistService

        optimized_blacklist_service = OptimizedBlacklistService(db_service=services["db_service"])
        services["optimized_blacklist_service"] = optimized_blacklist_service
        logger.info("  ✅ optimized_blacklist_service (OptimizedBlacklistService) - using DatabaseService pool")
    except Exception as e:
        logger.error(f"  ❌ Failed to initialize optimized_blacklist_service: {e}")

    # ============================================================
    # SUMMARY
    # ============================================================

    initialized_count = len(services)
    total_services = 14

    if initialized_count == total_services:
        logger.info(f"✅ Successfully initialized all {initialized_count} services")
    else:
        failed_count = total_services - initialized_count
        logger.warning(f"⚠️  Initialized {initialized_count}/{total_services} services ({failed_count} failed)")

    return services


def get_service_info() -> Dict[str, Any]:
    """
    Get information about available services

    Returns:
        Dictionary with service metadata
    """
    return {
        "total_services": 14,
        "categories": {
            "core_infrastructure": ["db_service"],
            "collection_services": ["collection_service", "scheduler_service"],
            "integration_services": ["cloudflare_service"],
            "configuration_services": [
                "credential_service",
                "secure_credential_service",
                "regtech_config_service",
                "settings_service",
            ],
            "business_logic": [
                "blacklist_service",
                "analytics_service",
                "scoring_service",
                "expiry_service",
                "ab_test_service",
                "optimized_blacklist_service",
            ],
        },
        "initialization_order": [
            "1. Core Infrastructure",
            "2. Services depending on db_service",
            "3. Collection services",
            "4. Integration services",
            "5. Configuration services",
            "6. Business logic services",
        ],
    }
