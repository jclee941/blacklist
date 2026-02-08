"""
탐지일 데이터 분석 및 시각화 API
Detection Date Analytics and Visualization

Updated: 2025-11-21 (Error Handling Standardization - HIGH PRIORITY #4)
Reference: docs/104-ERROR-HANDLING-STANDARDIZATION-PLAN.md
"""

import logging
from datetime import datetime
from flask import Blueprint, jsonify, request, g, render_template, current_app
from ...exceptions import (
    ValidationError,
    DatabaseError,
    InternalServerError,
)

logger = logging.getLogger(__name__)

# Detection Analytics Blueprint
detection_bp = Blueprint("detection_analytics", __name__, url_prefix="/analytics")


@detection_bp.route("/overview", methods=["GET"])
def get_analytics_overview():
    """Analytics dashboard overview with key metrics"""
    try:
        db_service = current_app.extensions["db_service"]
        
        stats = db_service.query("""
            SELECT 
                (SELECT COUNT(*) FROM blacklist_ips) as total_ips,
                (SELECT COUNT(*) FROM blacklist_ips WHERE is_active = true) as active_ips,
                (SELECT COUNT(DISTINCT data_source) FROM blacklist_ips) as source_count,
                (SELECT COUNT(*) FROM blacklist_ips WHERE created_at > NOW() - INTERVAL '24 hours') as new_today,
                (SELECT COUNT(*) FROM blacklist_ips WHERE created_at > NOW() - INTERVAL '7 days') as new_week
        """)
        
        row = stats[0] if stats else {}
        return jsonify({
            "success": True,
            "data": {
                "total_ips": row.get("total_ips", 0),
                "active_ips": row.get("active_ips", 0),
                "source_count": row.get("source_count", 0),
                "new_today": row.get("new_today", 0),
                "new_week": row.get("new_week", 0)
            },
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Analytics overview failed: {e}")
        raise DatabaseError(
            message="Failed to get analytics overview",
            query="analytics_overview"
        )


@detection_bp.route("/detection-timeline", methods=["GET"])
def get_detection_timeline():
    """
    탐지일별 IP 수집 현황 분석 (Phase 1.4: Standardized Error Handling)

    GET /analytics/detection-timeline?days=30&format=json

    Query Parameters:
        days (int): Analysis period in days (default: 30)
        format (str): Response format - "json" or "chart" (default: "json")

    Raises:
        ValidationError: Invalid days parameter
        DatabaseError: Database query failed
    """
    # Get and validate query parameters
    days_param = request.args.get("days", "30")
    
    # days=0 or days=all means no date filter (all data)
    if days_param.lower() == "all" or days_param == "0":
        days_back = None  # No limit
    else:
        try:
            days_back = int(days_param)
        except ValueError as e:
            raise ValidationError(
                message="Days parameter must be a valid integer or 'all'",
                field="days",
                details={"error": str(e)},
            )

    format_type = request.args.get("format", "json")  # json or chart

    try:
        db_service = current_app.extensions["db_service"]

        conn = db_service.get_connection()
        cursor = conn.cursor()

        # 날짜별 수집 통계 (View 사용 - 3개월 자동 비활성화 로직 적용)
        if days_back is None:
            # 전체 데이터 조회 (날짜 필터 없음)
            query = """
                SELECT
                    COALESCE(detection_date, created_at::date) as detection_day,
                    COUNT(*) as ip_count,
                    COUNT(DISTINCT source) as source_count,
                    STRING_AGG(DISTINCT source, ', ') as sources,
                    MIN(created_at) as first_collected,
                    MAX(created_at) as last_collected
                FROM blacklist_ips_with_auto_inactive
                GROUP BY COALESCE(detection_date, created_at::date)
                ORDER BY detection_day DESC
            """
            cursor.execute(query)
        else:
            query = """
                SELECT
                    COALESCE(detection_date, created_at::date) as detection_day,
                    COUNT(*) as ip_count,
                    COUNT(DISTINCT source) as source_count,
                    STRING_AGG(DISTINCT source, ', ') as sources,
                    MIN(created_at) as first_collected,
                    MAX(created_at) as last_collected
                FROM blacklist_ips_with_auto_inactive
                WHERE COALESCE(detection_date, created_at::date) >= CURRENT_DATE - INTERVAL '%s days'
                GROUP BY COALESCE(detection_date, created_at::date)
                ORDER BY detection_day DESC
            """
            cursor.execute(query, (days_back,))
        results = cursor.fetchall()

        # 컬럼명 매핑
        columns = [
            "detection_day",
            "ip_count",
            "source_count",
            "sources",
            "first_collected",
            "last_collected",
        ]
        timeline_data = []

        for row in results:
            data = dict(zip(columns, row))

            # 날짜 형식 변환
            if data["detection_day"]:
                data["detection_day"] = str(data["detection_day"])
            if data["first_collected"]:
                data["first_collected"] = data["first_collected"].isoformat()
            if data["last_collected"]:
                data["last_collected"] = data["last_collected"].isoformat()

            timeline_data.append(data)

        # 통계 요약
        total_ips = sum([d["ip_count"] for d in timeline_data])
        total_days = len(timeline_data)
        avg_per_day = total_ips / total_days if total_days > 0 else 0

        # 소스별 통계
        if days_back is None:
            # 전체 데이터 조회 (날짜 필터 없음)
            query = """
                SELECT
                    COALESCE(detection_date, created_at::date) as detection_day,
                    COUNT(*) as ip_count,
                    COUNT(DISTINCT source) as source_count,
                    STRING_AGG(DISTINCT source, ', ') as sources,
                    MIN(created_at) as first_collected,
                    MAX(created_at) as last_collected
                FROM blacklist_ips_with_auto_inactive
                GROUP BY COALESCE(detection_date, created_at::date)
                ORDER BY detection_day DESC
            """
            cursor.execute(query)
        else:
            query = """
                SELECT
                    COALESCE(detection_date, created_at::date) as detection_day,
                    COUNT(*) as ip_count,
                    COUNT(DISTINCT source) as source_count,
                    STRING_AGG(DISTINCT source, ', ') as sources,
                    MIN(created_at) as first_collected,
                    MAX(created_at) as last_collected
                FROM blacklist_ips_with_auto_inactive
                WHERE COALESCE(detection_date, created_at::date) >= CURRENT_DATE - INTERVAL '%s days'
                GROUP BY COALESCE(detection_date, created_at::date)
                ORDER BY detection_day DESC
            """
            cursor.execute(query, (days_back,))

        source_results = cursor.fetchall()
        source_stats = []
        for row in source_results:
            source_data = {
                "source": row[0],
                "total_ips": row[1],
                "active_days": row[2],
                "first_detection": str(row[3]) if row[3] else None,
                "last_detection": str(row[4]) if row[4] else None,
                "avg_per_day": round(row[1] / row[2], 1) if row[2] > 0 else 0,
            }
            source_stats.append(source_data)

        cursor.close()
        conn.close()

        # 로그 출력 (탐지일 데이터 분석)
        period_str = "전체" if days_back is None else f"{days_back}일"
        logger.info("📊 탐지일 데이터 분석 결과:")
        logger.info(f"   • 분석 기간: {period_str}")
        logger.info(f"   • 총 IP 수: {total_ips:,}개")
        logger.info(f"   • 활성 일수: {total_days}일")
        logger.info(f"   • 일평균: {avg_per_day:.1f}개")

        response_data = {
            "success": True,
            "metadata": {
                "analysis_period_days": days_back,  # None means all
                "total_ips": total_ips,
                "total_days": total_days,
                "avg_per_day": round(avg_per_day, 1),
                "generated_at": datetime.now().isoformat(),
            },
            "timeline": timeline_data,
            "source_statistics": source_stats,
        }

        if format_type == "chart":
            # 차트용 간단한 데이터 형식
            chart_data = {
                "labels": [d["detection_day"] for d in timeline_data],
                "datasets": [
                    {
                        "label": "IP 수집량",
                        "data": [d["ip_count"] for d in timeline_data],
                        "backgroundColor": "rgba(54, 162, 235, 0.8)",
                        "borderColor": "rgba(54, 162, 235, 1)",
                        "borderWidth": 1,
                    }
                ],
            }
            return jsonify(
                {
                    "success": True,
                    "data": {
                        "chart_data": chart_data,
                        "summary": response_data["metadata"],
                    },
                    "timestamp": datetime.now().isoformat(),
                    "request_id": g.request_id,
                }
            ), 200

        return jsonify(
            {
                "success": True,
                "data": response_data,
                "timestamp": datetime.now().isoformat(),
                "request_id": g.request_id,
            }
        ), 200

    except Exception as e:
        logger.error(f"Detection timeline analysis error: {e}", exc_info=True)
        raise DatabaseError(
            message="Failed to analyze detection timeline",
            details={
                "days": days_back,
                "format": format_type,
                "error_type": type(e).__name__,
            },
        )


@detection_bp.route("/suspicious-patterns", methods=["GET"])
def get_suspicious_patterns():
    """
    수상한 데이터 패턴 상세 분석 (Phase 1.4: Standardized Error Handling)

    GET /analytics/suspicious-patterns

    Raises:
        DatabaseError: Database query failed
    """
    db_service = current_app.extensions["db_service"]
    conn = None

    try:
        conn = db_service.get_connection()
        cursor = conn.cursor()

        try:
            patterns = []

            # 1. 정확히 떨어지는 숫자 패턴
            cursor.execute(
                """
                SELECT
                    COALESCE(detection_date, created_at::date) as day,
                    COUNT(*) as count,
                    source
                FROM blacklist_ips_with_auto_inactive
                GROUP BY COALESCE(detection_date, created_at::date), source
                HAVING COUNT(*) % 1000 = 0 AND COUNT(*) >= 1000
                ORDER BY count DESC
            """
            )

            round_numbers = cursor.fetchall()
            if round_numbers:
                patterns.append(
                    {
                        "type": "round_numbers",
                        "description": "정확히 떨어지는 숫자 (1000, 5000, 10000 등)",
                        "severity": "high",
                        "count": len(round_numbers),
                        "examples": [
                            {"date": str(row[0]), "ip_count": row[1], "source": row[2]} for row in round_numbers[:5]
                        ],
                    }
                )

                # 로그 출력
                logger.warning("🚨 정확히 떨어지는 숫자 패턴 발견:")
                for row in round_numbers[:3]:
                    logger.warning(f"   • {row[0]}: {row[1]:,}개 ({row[2]})")

            # 2. 비정상적 대량 수집
            cursor.execute(
                """
                WITH daily_stats AS (
                    SELECT
                        COALESCE(detection_date, created_at::date) as day,
                        COUNT(*) as count
                    FROM blacklist_ips_with_auto_inactive
                    GROUP BY COALESCE(detection_date, created_at::date)
                ),
                avg_stats AS (
                    SELECT AVG(count) as avg_count, STDDEV(count) as stddev_count
                    FROM daily_stats
                )
                SELECT d.day, d.count, a.avg_count
                FROM daily_stats d, avg_stats a
                WHERE d.count > (a.avg_count + 2 * COALESCE(a.stddev_count, a.avg_count))
                ORDER BY d.count DESC
            """
            )

            bulk_collections = cursor.fetchall()
            if bulk_collections:
                patterns.append(
                    {
                        "type": "bulk_collection",
                        "description": "비정상적 대량 수집 (평균 + 2σ 이상)",
                        "severity": "medium",
                        "count": len(bulk_collections),
                        "examples": [
                            {
                                "date": str(row[0]),
                                "ip_count": row[1],
                                "avg_baseline": round(float(row[2]), 1),
                            }
                            for row in bulk_collections[:5]
                        ],
                    }
                )

                # 로그 출력
                logger.warning("🚨 비정상적 대량 수집 패턴 발견:")
                for row in bulk_collections[:3]:
                    logger.warning(f"   • {row[0]}: {row[1]:,}개 (평균: {row[2]:.1f}개)")

            # 3. 단일 소스 대량 수집
            cursor.execute(
                """
                SELECT
                    data_source,
                    COALESCE(detection_date, created_at::date) as day,
                    COUNT(*) as count
                FROM blacklist_ips_with_auto_inactive
                GROUP BY data_source, COALESCE(detection_date, created_at::date)
                HAVING COUNT(*) > 10000
                ORDER BY count DESC
            """
            )

            single_source_bulk = cursor.fetchall()
            if single_source_bulk:
                patterns.append(
                    {
                        "type": "single_source_bulk",
                        "description": "단일 소스에서 1만개 이상 수집",
                        "severity": "high",
                        "count": len(single_source_bulk),
                        "examples": [
                            {"source": row[0], "date": str(row[1]), "ip_count": row[2]}
                            for row in single_source_bulk[:5]
                        ],
                    }
                )

                # 로그 출력
                logger.warning("🚨 단일 소스 대량 수집 패턴 발견:")
                for row in single_source_bulk[:3]:
                    logger.warning(f"   • {row[1]} {row[0]}: {row[2]:,}개")

            # 종합 위험도 평가
            total_issues = sum([p["count"] for p in patterns])
            risk_level = "low"
            if total_issues > 10:
                risk_level = "high"
            elif total_issues > 5:
                risk_level = "medium"

            logger.info(
                f"📊 수상한 패턴 분석 완료: {len(patterns)}가지 패턴, 총 {total_issues}건, 위험도: {risk_level}"
            )

            return jsonify(
                {
                    "success": True,
                    "data": {
                        "analysis": {
                            "total_pattern_types": len(patterns),
                            "total_issues": total_issues,
                            "risk_level": risk_level,
                            "generated_at": datetime.now().isoformat(),
                        },
                        "patterns": patterns,
                    },
                    "timestamp": datetime.now().isoformat(),
                    "request_id": g.request_id,
                }
            ), 200

        finally:
            cursor.close()

    except Exception as e:
        logger.error(f"Suspicious patterns analysis error: {e}", exc_info=True)
        raise DatabaseError(
            message="Failed to analyze suspicious patterns",
            details={"error_type": type(e).__name__},
        )
    finally:
        if conn:
            db_service.return_connection(conn)


@detection_bp.route("/detection-chart")
def detection_chart_page():
    """
    탐지일 데이터 시각화 페이지 (Phase 1.4: Standardized Error Handling)

    GET /analytics/detection-chart

    Raises:
        InternalServerError: Template rendering failed
    """
    try:
        return render_template("detection_chart.html")
    except Exception as e:
        logger.error(f"Detection chart page error: {e}", exc_info=True)
        raise InternalServerError(
            message="Failed to load detection chart page",
            details={"error_type": type(e).__name__},
        )


@detection_bp.route("/real-time-log", methods=["GET"])
def get_real_time_detection_log():
    """
    실시간 탐지 로그 스트림 (Phase 1.4: Standardized Error Handling)

    GET /analytics/real-time-log

    Raises:
        DatabaseError: Database query failed
    """
    try:
        db_service = current_app.extensions["db_service"]

        # 최근 24시간 내 수집된 데이터 로그
        conn = db_service.get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT
                created_at,
                ip_address,
                source,
                COALESCE(detection_date, created_at::date) as detection_day,
                confidence_level
            FROM blacklist_ips_with_auto_inactive
            WHERE created_at >= NOW() - INTERVAL '24 hours'
            ORDER BY created_at DESC
            LIMIT 10000
        """
        )

        results = cursor.fetchall()

        log_entries = []
        for row in results:
            entry = {
                "timestamp": row[0].isoformat() if row[0] else None,
                "ip_address": row[1],
                "source": row[2],
                "detection_day": str(row[3]) if row[3] else None,
                "confidence_level": row[4],
                "log_type": "detection",
            }
            log_entries.append(entry)

        cursor.close()
        conn.close()

        # 실시간 로그 출력
        logger.info(f"📡 실시간 탐지 로그: 최근 24시간 {len(log_entries)}건")
        for entry in log_entries[:5]:  # 최근 5건만 로그
            logger.info(f"   • {entry['timestamp']}: {entry['ip_address']} ({entry['source']})")

        return jsonify(
            {
                "success": True,
                "data": {
                    "log_entries": log_entries,
                    "metadata": {
                        "total_entries": len(log_entries),
                        "time_range": "24h",
                        "generated_at": datetime.now().isoformat(),
                    },
                },
                "timestamp": datetime.now().isoformat(),
                "request_id": g.request_id,
            }
        ), 200

    except Exception as e:
        logger.error(f"Real-time detection log error: {e}", exc_info=True)
        raise DatabaseError(
            message="Failed to retrieve real-time detection log",
            details={"error_type": type(e).__name__},
        )
