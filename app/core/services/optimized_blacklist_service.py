#!/usr/bin/env python3
"""
최적화된 블랙리스트 서비스 - 통합 API 지원
단일 쿼리 최적화 및 효율적인 데이터 처리
"""

import logging
from typing import Dict, Any
from datetime import datetime
from psycopg2.extras import RealDictCursor

logger = logging.getLogger(__name__)


class OptimizedBlacklistService:
    """최적화된 블랙리스트 서비스 - 성능 우선"""

    def __init__(self, db_service: Any):
        if db_service is None:
            raise ValueError("db_service is required")
        self.db = db_service

    def get_unified_statistics(self) -> Dict[str, Any]:
        """통합 통계 - 단일 쿼리로 모든 통계 수집"""
        conn = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            # 단일 쿼리로 모든 통계 수집
            cursor.execute("""
                SELECT
                    COUNT(*) as total_ips,
                    COUNT(*) FILTER (WHERE is_active = true) as active_ips,
                    COUNT(DISTINCT source) as sources,
                    COUNT(DISTINCT country) as countries,
                    MAX(updated_at) as last_update,
                    MIN(updated_at) as first_update,
                    COUNT(*) FILTER (WHERE detection_date >= CURRENT_DATE - INTERVAL '1 day') as recent_additions,
                    COUNT(*) FILTER (WHERE detection_count > 5) as high_confidence,
                    ROUND(AVG(confidence_level)::numeric, 2) as avg_confidence
                FROM blacklist_ips_with_auto_inactive
            """)

            stats = cursor.fetchone()

            # 최근 활동 및 수집 히스토리 (별도 최적화된 쿼리)
            cursor.execute("""
                SELECT
                    COUNT(*) as collection_count,
                    MAX(collection_date) as last_collection,
                    COUNT(*) FILTER (WHERE success = true) as successful_collections
                FROM collection_history
                WHERE collection_date >= NOW() - INTERVAL '7 days'
            """)

            collection_stats = cursor.fetchone()

            cursor.close()
            self.db.return_connection(conn)

            return {
                "success": True,
                "statistics": {
                    "total_ips": stats["total_ips"] or 0,
                    "active_ips": stats["active_ips"] or 0,
                    "sources": stats["sources"] or 0,
                    "countries": stats["countries"] or 0,
                    "last_update": stats["last_update"].isoformat() if stats["last_update"] else None,
                    "first_update": stats["first_update"].isoformat() if stats["first_update"] else None,
                    "recent_additions": stats["recent_additions"] or 0,
                    "high_confidence": stats["high_confidence"] or 0,
                    "avg_confidence": float(stats["avg_confidence"]) if stats["avg_confidence"] else 0.0,
                    "collection_count": collection_stats["collection_count"] or 0,
                    "last_collection": collection_stats["last_collection"].isoformat()
                    if collection_stats["last_collection"]
                    else None,
                    "successful_collections": collection_stats["successful_collections"] or 0,
                },
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"통합 통계 조회 실패: {e}")
            if conn:
                self.db.return_connection(conn)
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }

    def search_ips(self, query: str, limit: int = 100) -> Dict[str, Any]:
        """IP 검색 - 최적화된 인덱스 활용"""
        conn = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            # IP 검색 최적화 (인덱스 활용)
            cursor.execute(
                """
                SELECT
                    ip_address, source, reason, confidence_level,
                    detection_count, is_active, country,
                    detection_date, last_seen, created_at
                FROM blacklist_ips_with_auto_inactive
                WHERE ip_address ILIKE %s
                   OR source ILIKE %s
                   OR country ILIKE %s
                ORDER BY detection_count DESC, last_seen DESC
                LIMIT %s
            """,
                (f"%{query}%", f"%{query}%", f"%{query}%", limit),
            )

            results = cursor.fetchall()
            cursor.close()
            self.db.return_connection(conn)

            return {
                "success": True,
                "results": [dict(row) for row in results],
                "count": len(results),
                "query": query,
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"IP 검색 실패: {e}")
            if conn:
                self.db.return_connection(conn)
            return {
                "success": False,
                "error": str(e),
                "query": query,
                "timestamp": datetime.now().isoformat(),
            }

    def get_active_blacklist(self, format_type: str = "json") -> Dict[str, Any]:
        """활성 블랙리스트 조회 - 형식별 최적화"""
        conn = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            if format_type == "plain":
                # 단순 IP 리스트만
                cursor.execute("""
                    SELECT ip_address
                    FROM blacklist_ips_with_auto_inactive
                    WHERE is_active = true
                    ORDER BY ip_address
                """)
                ips = [row["ip_address"] for row in cursor.fetchall()]

                cursor.close()
                self.db.return_connection(conn)

                return {
                    "success": True,
                    "ips": ips,
                    "count": len(ips),
                    "format": "plain",
                    "timestamp": datetime.now().isoformat(),
                }
            else:
                # 전체 정보
                cursor.execute("""
                    SELECT
                        ip_address, source, reason, confidence_level,
                        detection_count, country, detection_date, last_seen
                    FROM blacklist_ips_with_auto_inactive
                    WHERE is_active = true
                    ORDER BY detection_count DESC, last_seen DESC
                """)

                results = cursor.fetchall()
                cursor.close()
                self.db.return_connection(conn)

                return {
                    "success": True,
                    "blacklist": [dict(row) for row in results],
                    "count": len(results),
                    "format": "json",
                    "timestamp": datetime.now().isoformat(),
                }

        except Exception as e:
            logger.error(f"활성 블랙리스트 조회 실패: {e}")
            if conn:
                self.db.return_connection(conn)
            return {
                "success": False,
                "error": str(e),
                "format": format_type,
                "timestamp": datetime.now().isoformat(),
            }

    def get_collection_status(self) -> Dict[str, Any]:
        """수집 상태 조회 - 최적화된 단일 쿼리"""
        conn = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            # 최근 수집 상태 통합 조회
            cursor.execute("""
                SELECT
                    status,
                    ips_collected,
                    created_at,
                    error_message,
                    ROW_NUMBER() OVER (ORDER BY created_at DESC) as row_num
                FROM collection_history
                WHERE created_at >= NOW() - INTERVAL '7 days'
                ORDER BY created_at DESC
                LIMIT 10
            """)

            history = cursor.fetchall()

            # 수집 서비스 상태
            cursor.execute("""
                SELECT service_name, is_active, updated_at
                FROM collection_credentials
                ORDER BY service_name
            """)

            services = cursor.fetchall()

            cursor.close()
            self.db.return_connection(conn)

            latest_collection = history[0] if history else None

            return {
                "success": True,
                "status": {
                    "latest_collection": {
                        "status": latest_collection["status"] if latest_collection else "unknown",
                        "timestamp": latest_collection["created_at"].isoformat()
                        if latest_collection and latest_collection["created_at"]
                        else None,
                        "ips_collected": latest_collection["ips_collected"] if latest_collection else 0,
                        "error": latest_collection["error_message"] if latest_collection else None,
                    },
                    "history": [dict(row) for row in history],
                    "services": [dict(row) for row in services],
                    "active_services": len([s for s in services if s["is_active"]]),
                },
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"수집 상태 조회 실패: {e}")
            if conn:
                self.db.return_connection(conn)
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }

    def health_check(self) -> Dict[str, Any]:
        """서비스 헬스체크 - 빠른 응답"""
        try:
            # 빠른 DB 연결 테스트
            db_healthy = self.db.health_check()

            # 기본 통계 (캐시 가능)
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM blacklist_ips_with_auto_inactive")
            total_ips = cursor.fetchone()[0]
            cursor.close()
            self.db.return_connection(conn)

            return {
                "success": True,
                "status": "healthy",
                "database": "connected" if db_healthy else "disconnected",
                "total_ips": total_ips,
                "service": "optimized-blacklist-service",
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"헬스체크 실패: {e}")
            return {
                "success": False,
                "status": "unhealthy",
                "error": str(e),
                "service": "optimized-blacklist-service",
                "timestamp": datetime.now().isoformat(),
            }


# 전역 최적화된 서비스 인스턴스 대체
# optimized_blacklist_service = OptimizedBlacklistService()
from flask import current_app
from werkzeug.local import LocalProxy

optimized_blacklist_service = LocalProxy(lambda: current_app.extensions["optimized_blacklist_service"])
