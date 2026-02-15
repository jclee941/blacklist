"""Unit tests for AnalyticsService"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime


@pytest.mark.unit
class TestAnalyticsService:
    """Tests for AnalyticsService"""

    def setup_method(self):
        """Setup test fixtures"""
        self.mock_db = Mock()
        from app.core.services.analytics_service import AnalyticsService

        self.service = AnalyticsService(db_service=self.mock_db)

    # --- analyze_false_positive_patterns ---

    def test_analyze_false_positive_patterns_success(self):
        """Full analysis with all queries returning data"""
        reason_data = [{"reason": "brute_force", "count": 50, "unique_ips": 30}]
        source_data = [{"source": "REGTECH", "count": 100, "unique_ips": 80, "last_updated": "2025-01-01"}]
        country_data = [{"country": "CN", "count": 60, "unique_ips": 40}]
        hourly_data = [{"hour": 14, "count": 20}]
        spike_data = [{"ip_prefix": "192.168.", "count": 15, "unique_ips": 12}]

        self.mock_db.query.side_effect = [
            reason_data,  # reason_stats
            source_data,  # source_stats
            country_data,  # country_stats
            hourly_data,  # hourly_stats
            spike_data,  # spike_detection
        ]

        result = self.service.analyze_false_positive_patterns(days=7)

        assert result["success"] is True
        assert result["period_days"] == 7
        assert "analyzed_at" in result
        assert result["analysis"]["reason_distribution"] == reason_data
        assert result["analysis"]["source_distribution"] == source_data
        assert result["analysis"]["country_distribution"] == country_data
        assert result["analysis"]["hourly_pattern"] == hourly_data
        assert result["analysis"]["spike_detection"] == spike_data
        assert self.mock_db.query.call_count == 5

    def test_analyze_false_positive_patterns_custom_days(self):
        """Analysis with custom period"""
        self.mock_db.query.return_value = []

        result = self.service.analyze_false_positive_patterns(days=30)

        assert result["success"] is True
        assert result["period_days"] == 30

    def test_analyze_false_positive_patterns_empty_data(self):
        """Analysis when no data found"""
        self.mock_db.query.return_value = []

        result = self.service.analyze_false_positive_patterns()

        assert result["success"] is True
        assert result["analysis"]["reason_distribution"] == []
        assert result["insights"] == []

    def test_analyze_false_positive_patterns_country_query_fails(self):
        """Country stats failure doesn't break overall analysis"""
        self.mock_db.query.side_effect = [
            [{"reason": "scan", "count": 10, "unique_ips": 5}],  # reason
            [],  # source
            Exception("Country column missing"),  # country - raises
        ]

        # The third query raises, but it's caught internally
        # Actually the side_effect will raise on 3rd call, which is country_stats
        # The service catches this with try/except
        # Let me test differently - use a function that returns data for first 2, raises on 3rd
        call_count = 0
        original_side_effects = [
            [{"reason": "scan", "count": 10, "unique_ips": 5}],
            [],
        ]

        def query_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                return original_side_effects[call_count - 1]
            elif call_count == 3:
                raise Exception("Country column missing")
            else:
                return []

        self.mock_db.query.side_effect = query_side_effect

        result = self.service.analyze_false_positive_patterns()

        assert result["success"] is True
        assert result["analysis"]["country_distribution"] == []

    def test_analyze_false_positive_patterns_db_error(self):
        """DB error returns failure"""
        self.mock_db.query.side_effect = Exception("Database down")

        result = self.service.analyze_false_positive_patterns()

        assert result["success"] is False
        assert "Database down" in result["error"]

    # --- _generate_insights ---

    def test_generate_insights_top_reason_high_severity(self):
        """Top reason > 50% = high severity"""
        reason_stats = [
            {"reason": "malware", "count": 80, "unique_ips": 50},
            {"reason": "scan", "count": 20, "unique_ips": 10},
        ]
        insights = self.service._generate_insights(reason_stats, [], [], [])

        assert len(insights) == 1
        assert insights[0]["type"] == "top_reason"
        assert insights[0]["severity"] == "high"
        assert "malware" in insights[0]["message"]
        assert "80.0%" in insights[0]["message"]

    def test_generate_insights_top_reason_medium_severity(self):
        """Top reason <= 50% = medium severity"""
        reason_stats = [
            {"reason": "malware", "count": 40, "unique_ips": 30},
            {"reason": "scan", "count": 35, "unique_ips": 20},
            {"reason": "spam", "count": 25, "unique_ips": 15},
        ]
        insights = self.service._generate_insights(reason_stats, [], [], [])

        assert insights[0]["severity"] == "medium"

    def test_generate_insights_spike_detection(self):
        """Spike detection generates high severity insights"""
        spikes = [
            {"ip_prefix": "10.0.", "count": 50, "unique_ips": 40},
            {"ip_prefix": "172.16.", "count": 30, "unique_ips": 25},
        ]
        insights = self.service._generate_insights([], [], [], spikes)

        assert len(insights) == 2
        assert all(i["type"] == "ip_spike" for i in insights)
        assert all(i["severity"] == "high" for i in insights)

    def test_generate_insights_spike_max_three(self):
        """At most 3 spike insights generated"""
        spikes = [{"ip_prefix": f"10.{i}.", "count": 50 - i, "unique_ips": 40} for i in range(5)]
        insights = self.service._generate_insights([], [], [], spikes)

        spike_insights = [i for i in insights if i["type"] == "ip_spike"]
        assert len(spike_insights) == 3

    def test_generate_insights_country_concentration(self):
        """Country concentration > 70% generates insight"""
        country_stats = [
            {"country": "CN", "count": 80, "unique_ips": 60},
            {"country": "US", "count": 20, "unique_ips": 15},
        ]
        insights = self.service._generate_insights([], [], country_stats, [])

        assert len(insights) == 1
        assert insights[0]["type"] == "country_concentration"
        assert insights[0]["severity"] == "medium"
        assert "CN" in insights[0]["message"]

    def test_generate_insights_country_no_concentration(self):
        """Country < 70% does not generate concentration insight"""
        country_stats = [
            {"country": "CN", "count": 40, "unique_ips": 30},
            {"country": "US", "count": 35, "unique_ips": 25},
            {"country": "RU", "count": 25, "unique_ips": 15},
        ]
        insights = self.service._generate_insights([], [], country_stats, [])

        assert not any(i["type"] == "country_concentration" for i in insights)

    def test_generate_insights_empty_data(self):
        """No data = no insights"""
        insights = self.service._generate_insights([], [], [], [])
        assert insights == []

    def test_generate_insights_combined(self):
        """Multiple insight types at once"""
        reason_stats = [{"reason": "malware", "count": 90, "unique_ips": 70}]
        spikes = [{"ip_prefix": "10.0.", "count": 20, "unique_ips": 15}]
        country_stats = [{"country": "CN", "count": 80, "unique_ips": 60}]

        insights = self.service._generate_insights(reason_stats, [], country_stats, spikes)

        types = [i["type"] for i in insights]
        assert "top_reason" in types
        assert "ip_spike" in types
        assert "country_concentration" in types

    # --- get_whitelist_candidates ---

    def test_get_whitelist_candidates_success(self):
        """Whitelist candidates returned"""
        candidates = [
            {
                "ip_address": "10.0.0.1",
                "reason": "scan",
                "source": "REGTECH",
                "detection_count": 10,
                "last_seen": "2025-01-01",
            },
        ]
        self.mock_db.query.return_value = candidates

        result = self.service.get_whitelist_candidates(min_blocked_count=5)

        assert result["success"] is True
        assert result["count"] == 1
        assert result["candidates"] == candidates

    def test_get_whitelist_candidates_custom_threshold(self):
        """Custom min_blocked_count passed to query"""
        self.mock_db.query.return_value = []

        result = self.service.get_whitelist_candidates(min_blocked_count=10)

        assert result["success"] is True
        # Verify the threshold was passed
        call_args = self.mock_db.query.call_args
        assert call_args[0][1] == (10,)

    def test_get_whitelist_candidates_db_error(self):
        """DB error returns failure"""
        self.mock_db.query.side_effect = Exception("Query failed")

        result = self.service.get_whitelist_candidates()

        assert result["success"] is False
        assert "Query failed" in result["error"]

    # --- get_performance_metrics ---

    def test_get_performance_metrics_success(self):
        """Performance metrics with data"""
        overall = [{"total_ips": 500, "total_sources": 3, "last_updated": "2025-01-01"}]
        recent = [{"service_name": "REGTECH", "items_collected": 100, "success": True}]

        self.mock_db.query.side_effect = [overall, recent]

        result = self.service.get_performance_metrics(hours=24)

        assert result["success"] is True
        assert result["period_hours"] == 24
        assert result["overall"]["total_ips"] == 500
        assert result["health_status"] == "healthy"

    def test_get_performance_metrics_no_ips(self):
        """Health status is degraded with no IPs"""
        self.mock_db.query.side_effect = [
            [{"total_ips": 0, "total_sources": 0, "last_updated": None}],
            [],
        ]

        result = self.service.get_performance_metrics()

        assert result["health_status"] == "degraded"

    def test_get_performance_metrics_empty_result(self):
        """Empty query results"""
        self.mock_db.query.side_effect = [[], []]

        result = self.service.get_performance_metrics()

        assert result["success"] is True
        assert result["health_status"] == "degraded"

    def test_get_performance_metrics_db_error(self):
        """DB error returns failure"""
        self.mock_db.query.side_effect = Exception("Connection lost")

        result = self.service.get_performance_metrics()

        assert result["success"] is False
        assert "Connection lost" in result["error"]
