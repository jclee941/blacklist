from core.services.collection.threat_intelligence import ThreatIntelligenceCollector


def _make_collector():
    return ThreatIntelligenceCollector()


class TestThreatIntelligenceCollectorInit:
    def test_init_has_sources(self):
        collector = _make_collector()
        assert isinstance(collector.threat_sources, list)
        assert len(collector.threat_sources) > 0
        assert "alienvault" in collector.threat_sources


class TestCollectThreatIntelligenceIps:
    def test_returns_list(self):
        collector = _make_collector()
        result = collector.collect_threat_intelligence_ips()
        assert isinstance(result, list)


class TestCollectMaliciousIpLists:
    def test_returns_list(self):
        collector = _make_collector()
        result = collector.collect_malicious_ip_lists()
        assert isinstance(result, list)


class TestCollectFromSource:
    def test_alienvault(self):
        collector = _make_collector()
        result = collector._collect_from_source("alienvault")
        assert isinstance(result, list)

    def test_emergingthreats(self):
        collector = _make_collector()
        result = collector._collect_from_source("emergingthreats")
        assert isinstance(result, list)

    def test_malwaredomainlist(self):
        collector = _make_collector()
        result = collector._collect_from_source("malwaredomainlist")
        assert isinstance(result, list)

    def test_spamhaus(self):
        collector = _make_collector()
        result = collector._collect_from_source("spamhaus")
        assert isinstance(result, list)

    def test_barracuda(self):
        collector = _make_collector()
        result = collector._collect_from_source("barracuda")
        assert isinstance(result, list)

    def test_firehol(self):
        collector = _make_collector()
        result = collector._collect_from_source("firehol")
        assert isinstance(result, list)

    def test_unknown_source(self):
        collector = _make_collector()
        result = collector._collect_from_source("unknown_source")
        assert isinstance(result, list)
        assert len(result) == 0


class TestIndividualSourceMethods:
    def test_collect_alienvault_data(self):
        collector = _make_collector()
        result = collector._collect_alienvault_data()
        assert isinstance(result, list)

    def test_collect_emergingthreats_data(self):
        collector = _make_collector()
        result = collector._collect_emergingthreats_data()
        assert isinstance(result, list)
