"""Data models for multi-source threat intelligence collection."""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional


class SourceType(Enum):
    """위협 정보 소스 타입"""

    REGTECH = "regtech"
    ABUSE_CH = "abuse_ch"
    MALWARE_BAZAAR = "malware_bazaar"
    URLHAUS = "urlhaus"
    PHISHTANK = "phishtank"
    OPENPHISH = "openphish"
    VIRUSTOTAL = "virustotal"
    ALIENVAULT = "alienvault"
    THREATFOX = "threatfox"
    FEODO = "feodo"
    CUSTOM_API = "custom_api"
    RSS_FEED = "rss_feed"
    CSV_FILE = "csv_file"
    JSON_API = "json_api"


@dataclass
class SourceConfig:
    """소스 설정"""

    source_type: SourceType
    name: str
    url: str
    api_key: Optional[str] = None
    headers: Optional[Dict[str, str]] = None
    params: Optional[Dict[str, Any]] = None
    enabled: bool = True
    priority: int = 1
    rate_limit: float = 1.0
    timeout: int = 30
    retry_count: int = 3
    data_format: str = "json"
    ip_field: str = "ip"
    date_field: Optional[str] = None
    reason_field: Optional[str] = None
    confidence_boost: int = 0
    category: str = "malicious"
