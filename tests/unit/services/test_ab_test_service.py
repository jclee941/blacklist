"""Tests for core.services.ab_test_service"""

from core.services.ab_test_service import ABTestService


class TestABTestService:
    def _make_service(self):
        return ABTestService()

    def test_init(self):
        svc = self._make_service()
        assert svc.NEW_LOGIC_PERCENTAGE == 10
        assert "scoring_system" in svc.FEATURE_FLAGS
        assert "whitelist_priority" in svc.FEATURE_FLAGS

    def test_should_use_new_logic_unknown_feature(self):
        svc = self._make_service()
        result = svc.should_use_new_logic("1.1.1.1", "nonexistent")
        assert result is False

    def test_should_use_new_logic_disabled_feature(self):
        svc = self._make_service()
        svc.FEATURE_FLAGS["scoring_system"]["enabled"] = False
        result = svc.should_use_new_logic("1.1.1.1", "scoring_system")
        assert result is False

    def test_should_use_new_logic_100_percent(self):
        svc = self._make_service()
        result = svc.should_use_new_logic("1.1.1.1", "whitelist_priority")
        assert result is True

    def test_should_use_new_logic_hash_based(self):
        svc = self._make_service()
        svc.FEATURE_FLAGS["scoring_system"]["enabled"] = True
        svc.FEATURE_FLAGS["scoring_system"]["percentage"] = 50
        result = svc.should_use_new_logic("1.1.1.1", "scoring_system")
        assert isinstance(result, bool)

    def test_should_use_new_logic_zero_percent(self):
        svc = self._make_service()
        svc.FEATURE_FLAGS["scoring_system"]["percentage"] = 0
        result = svc.should_use_new_logic("1.1.1.1", "scoring_system")
        assert result is False

    def test_track_experiment(self):
        svc = self._make_service()
        svc.track_experiment("1.1.1.1", "scoring_system", "new", {"blocked": True})

    def test_get_feature_status(self):
        svc = self._make_service()
        result = svc.get_feature_status()
        assert "features" in result
        assert "timestamp" in result
        assert result["features"] == svc.FEATURE_FLAGS

    def test_update_feature_percentage_success(self):
        svc = self._make_service()
        svc.FEATURE_FLAGS["scoring_system"]["percentage"] = 10
        result = svc.update_feature_percentage("scoring_system", 50)
        assert result["success"] is True
        assert result["new_percentage"] == 50
        assert svc.FEATURE_FLAGS["scoring_system"]["percentage"] == 50

    def test_update_feature_percentage_unknown_feature(self):
        svc = self._make_service()
        result = svc.update_feature_percentage("nonexistent", 50)
        assert result["success"] is False

    def test_update_feature_percentage_invalid_range(self):
        svc = self._make_service()
        result = svc.update_feature_percentage("scoring_system", -1)
        assert result["success"] is False

    def test_update_feature_percentage_over_100(self):
        svc = self._make_service()
        result = svc.update_feature_percentage("scoring_system", 101)
        assert result["success"] is False
