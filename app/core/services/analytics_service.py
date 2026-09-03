#!/usr/bin/env python3
"""
분석 서비스 - Phase 3.1: 오탐 패턴 분석
블랙리스트 판단 데이터 분석 및 인사이트 제공
"""

import logging
from datetime import datetime
from typing import TYPE_CHECKING, Dict, List, Any

if TYPE_CHECKING:
    from .database_service import DatabaseService

logger = logging.getLogger(__name__)


class AnalyticsService:
    """블랙리스트 분석 서비스"""

    def __init__(self, db_service: "DatabaseService") -> None:
        """
        Initialize analytics service

        Args:
            db_service: DatabaseService instance for connection pool access
        """
        self.db_service = db_service

    def analyze_false_positive_patterns(self, days: int = 7) -> Dict[str, Any]:
        """
        오탐 패턴 분석 (Phase 3.1)

        Args:
            days: 분석 기간 (일)

        Returns:
            오탐 패턴 분석 결과
        """
        try:
            # 1. 차단 사유별 통계
            reason_stats = self.db_service.query(
                """
                SELECT
                    reason,
                    COUNT(*) as count,
                    COUNT(DISTINCT ip_address) as unique_ips
                FROM blacklist_ips
                WHERE is_active = true
                    AND created_at > NOW() - INTERVAL '%s days'
                GROUP BY reason
                ORDER BY count DESC
                LIMIT 10
            """,
                (days,),
            )

            # 2. 소스별 통계
            source_stats = self.db_service.query(
                """
                SELECT
                    source,
                    COUNT(*) as count,
                    COUNT(DISTINCT ip_address) as unique_ips,
                    MAX(created_at) as last_updated
                FROM blacklist_ips
                WHERE is_active = true
                    AND created_at > NOW() - INTERVAL '%s days'
                GROUP BY source
                ORDER BY count DESC
            """,
                (days,),
            )

            # 3. 국가별 통계 (country 컬럼이 있는 경우)
            try:
                country_stats = self.db_service.query(
                    """
                    SELECT
                        country,
                        COUNT(*) as count,
                        COUNT(DISTINCT ip_address) as unique_ips
                    FROM blacklist_ips
                    WHERE is_active = true
                        AND country IS NOT NULL
                        AND created_at > NOW() - INTERVAL '%s days'
                    GROUP BY country
                    ORDER BY count DESC
                    LIMIT 10
                """,
                    (days,),
                )
            except Exception as e:
                logger.warning(f"Country stats failed: {e}")
                country_stats = []

            # 4. 시간대별 차단 패턴
            hourly_stats = self.db_service.query(
                """
                SELECT
                    EXTRACT(HOUR FROM created_at) as hour,
                    COUNT(*) as count
                FROM blacklist_ips
                WHERE is_active = true
                    AND created_at > NOW() - INTERVAL '%s days'
                GROUP BY hour
                ORDER BY hour
            """,
                (days,),
            )

            # 5. 급증 IP 대역 감지 (최근 24시간)
            spike_detection = self.db_service.query("""
                SELECT
                    substring(ip_address from '([0-9]+\\.[0-9]+\\.)') as ip_prefix,
                    COUNT(*) as count,
                    COUNT(DISTINCT ip_address) as unique_ips
                FROM blacklist_ips
                WHERE is_active = true
                    AND created_at > NOW() - INTERVAL '24 hours'
                GROUP BY ip_prefix
                HAVING COUNT(*) > 10
                ORDER BY count DESC
                LIMIT 10
            """)

            return {
                "success": True,
                "period_days": days,
                "analyzed_at": datetime.now().isoformat(),
                "analysis": {
                    "reason_distribution": reason_stats,
                    "source_distribution": source_stats,
                    "country_distribution": country_stats,
                    "hourly_pattern": hourly_stats,
                    "spike_detection": spike_detection,
                },
                "insights": self._generate_insights(reason_stats, source_stats, country_stats, spike_detection),
            }

        except Exception as e:
            logger.error(f"False positive pattern analysis failed: {e}")
            return {"success": False, "error": str(e)}

    def _generate_insights(self, reason_stats, source_stats, country_stats, spike_detection) -> List[Dict[str, str]]:
        """분석 결과 기반 인사이트 생성"""
        insights = []

        # Top reason 인사이트
        if reason_stats:
            top_reason = reason_stats[0]
            total_count = sum(row["count"] for row in reason_stats)
            percentage = (top_reason["count"] / total_count * 100) if total_count > 0 else 0

            insights.append(
                {
                    "type": "top_reason",
                    "severity": "high" if percentage > 50 else "medium",
                    "message": f"'{top_reason['reason']}' 사유가 전체의 {percentage:.1f}%를 차지합니다.",
                    "recommendation": "해당 사유의 정확성을 재검토하거나 화이트리스트 추가를 고려하세요.",
                }
            )

        # 급증 IP 대역 인사이트
        if spike_detection:
            for spike in spike_detection[:3]:  # Top 3만
                insights.append(
                    {
                        "type": "ip_spike",
                        "severity": "high",
                        "message": (
                            f"IP 대역 {spike['ip_prefix']}*에서 {spike['count']}개 IP가 24시간 내 차단되었습니다."
                        ),
                        "recommendation": "대규모 공격 또는 오탐 가능성이 있으므로 즉시 확인이 필요합니다.",
                    }
                )

        # 국가별 집중도 인사이트
        if country_stats and len(country_stats) > 0:
            top_country = country_stats[0]
            total = sum(row["count"] for row in country_stats)
            percentage = (top_country["count"] / total * 100) if total > 0 else 0

            if percentage > 70:
                insights.append(
                    {
                        "type": "country_concentration",
                        "severity": "medium",
                        "message": f"{top_country['country']} 국가에서 {percentage:.1f}%의 위협이 발생하고 있습니다.",
                        "recommendation": "특정 국가 집중 현상이 정상인지 검토하세요.",
                    }
                )

        return insights

    def get_whitelist_candidates(self, min_blocked_count: int = 5) -> Dict[str, Any]:
        """
        화이트리스트 후보 IP 추천

        Args:
            min_blocked_count: 최소 차단 횟수

        Returns:
            화이트리스트 추가 후보 목록
        """
        try:
            # 자주 차단되지만 화이트리스트에 없는 IP
            candidates = self.db_service.query(
                """
                SELECT
                    bi.ip_address,
                    bi.reason,
                    bi.source,
                    bi.detection_count,
                    bi.last_seen
                FROM blacklist_ips bi
                LEFT JOIN whitelist_ips wi ON bi.ip_address = wi.ip_address
                WHERE bi.is_active = true
                    AND wi.ip_address IS NULL
                    AND bi.detection_count >= %s
                ORDER BY bi.detection_count DESC
                LIMIT 20
            """,
                (min_blocked_count,),
            )

            return {
                "success": True,
                "candidates": candidates,
                "count": len(candidates),
                "recommendation": "이 IP들이 VIP 고객인지 확인 후 화이트리스트 추가를 고려하세요.",
            }

        except Exception as e:
            logger.error(f"Whitelist candidates analysis failed: {e}")
            return {"success": False, "error": str(e)}

    def get_performance_metrics(self, hours: int = 24) -> Dict[str, Any]:
        """
        블랙리스트 시스템 성능 메트릭

        Args:
            hours: 분석 기간 (시간)

        Returns:
            성능 메트릭
        """
        try:
            # 1. 전체 통계
            overall_stats_result = self.db_service.query("""
                SELECT
                    COUNT(*) as total_ips,
                    COUNT(DISTINCT source) as total_sources,
                    MAX(created_at) as last_updated
                FROM blacklist_ips
                WHERE is_active = true
            """)

            overall_stats = overall_stats_result[0] if overall_stats_result else {}

            # 2. 최근 수집 통계
            recent_collections = self.db_service.query(
                """
                SELECT
                    service_name,
                    collection_date,
                    items_collected,
                    success,
                    execution_time_ms
                FROM collection_history
                WHERE collection_date > NOW() - INTERVAL '%s hours'
                ORDER BY collection_date DESC
                LIMIT 10
            """,
                (hours,),
            )

            return {
                "success": True,
                "period_hours": hours,
                "overall": overall_stats,
                "recent_collections": recent_collections,
                "health_status": "healthy" if overall_stats and overall_stats.get("total_ips", 0) > 0 else "degraded",
            }

        except Exception as e:
            logger.error(f"Performance metrics analysis failed: {e}")
            return {"success": False, "error": str(e)}


from flask import current_app
from werkzeug.local import LocalProxy

analytics_service = LocalProxy(lambda: current_app.extensions["analytics_service"])
