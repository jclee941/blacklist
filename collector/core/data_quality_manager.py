"""
데이터 품질 관리 시스템
기존 데이터 유지 및 품질 향상을 위한 통합 관리
"""

import logging
from datetime import datetime
from typing import Dict, List, Any
from core.database import db_service

logger = logging.getLogger(__name__)


class DataQualityManager:
    """데이터 품질 관리자"""

    def __init__(self):
        self.quality_metrics = {
            "total_ips": 0,
            "active_ips": 0,
            "inactive_ips": 0,
            "duplicate_ips": 0,
            "invalid_ips": 0,
            "missing_dates": 0,
            "data_freshness_score": 0,
            "last_quality_check": None,
        }

        self.quality_thresholds = {
            "max_age_days": 90,  # 최대 데이터 보존 기간
            "min_freshness_score": 70,  # 최소 신선도 점수
            "max_duplicate_rate": 0.05,  # 최대 중복률 5%
            "min_active_rate": 0.80,  # 최소 활성률 80%
        }

    def perform_comprehensive_quality_check(self) -> Dict[str, Any]:
        """포괄적 데이터 품질 검사"""
        logger.info("🔍 포괄적 데이터 품질 검사 시작")

        quality_report: Dict[str, Any] = {
            "check_timestamp": datetime.now().isoformat(),
            "metrics": {},
            "issues": [],
            "recommendations": [],
            "actions_taken": [],
        }

        try:
            # 1. 기본 통계 수집
            basic_stats = self._collect_basic_statistics()
            quality_report["metrics"].update(basic_stats)

            # 2. 데이터 무결성 검사
            integrity_issues = self._check_data_integrity()
            quality_report["issues"].extend(integrity_issues)

            # 3. 데이터 신선도 분석
            freshness_analysis = self._analyze_data_freshness()
            quality_report["metrics"].update(freshness_analysis)

            # 4. 중복 데이터 검사
            duplicate_analysis = self._detect_duplicates()
            quality_report["metrics"].update(duplicate_analysis)

            # 5. 자동 정제 수행
            cleanup_actions = self._perform_automatic_cleanup()
            quality_report["actions_taken"].extend(cleanup_actions)

            # 6. 권장사항 생성
            recommendations = self._generate_recommendations(quality_report)
            quality_report["recommendations"] = recommendations

            # 7. 품질 점수 계산
            quality_score = self._calculate_quality_score(quality_report)
            quality_report["overall_quality_score"] = quality_score

            logger.info(f"✅ 데이터 품질 검사 완료 (점수: {quality_score}/100)")

            # 품질 보고서 저장
            self._save_quality_report(quality_report)

            return quality_report

        except Exception as e:
            logger.error(f"❌ 데이터 품질 검사 중 오류: {e}")
            quality_report["error"] = str(e)
            return quality_report

    def _collect_basic_statistics(self) -> Dict[str, Any]:
        """기본 통계 수집"""
        try:
            with db_service.get_connection() as conn:
                cursor = conn.cursor()

                # 전체 IP 통계
                cursor.execute(
                    """
                    SELECT
                        COUNT(*) as total_ips,
                        COUNT(*) FILTER (WHERE is_active = true) as active_ips,
                        COUNT(*) FILTER (WHERE is_active = false) as inactive_ips,
                        COUNT(*) FILTER (WHERE detection_date IS NULL) as missing_detection_date,
                        COUNT(*) FILTER (WHERE removal_date IS NULL) as missing_removal_date,
                        COUNT(DISTINCT ip_address) as unique_ips,
                        COUNT(*) - COUNT(DISTINCT ip_address) as duplicate_count
                    FROM blacklist_ips
                """
                )

                stats = cursor.fetchone()
                cursor.close()

            return {
                "total_ips": stats[0],
                "active_ips": stats[1],
                "inactive_ips": stats[2],
                "missing_detection_date": stats[3],
                "missing_removal_date": stats[4],
                "unique_ips": stats[5],
                "duplicate_ips": stats[6],
                "active_rate": round(stats[1] / stats[0] * 100, 2) if stats[0] > 0 else 0,
                "duplicate_rate": round(stats[6] / stats[0] * 100, 2) if stats[0] > 0 else 0,
            }

        except Exception as e:
            logger.error(f"❌ 기본 통계 수집 실패: {e}")
            return {}

    def _check_data_integrity(self) -> List[str]:
        """데이터 무결성 검사"""
        issues = []

        try:
            with db_service.get_connection() as conn:
                cursor = conn.cursor()

                # 1. 잘못된 IP 주소 형식 검사
                cursor.execute(
                    r"""
                    SELECT COUNT(*) FROM blacklist_ips
                    WHERE ip_address !~ '^([0-9]{1,3}\.){3}[0-9]{1,3}$'
                    AND ip_address !~ '^([0-9a-fA-F]{0,4}:){1,7}[0-9a-fA-F]{0,4}$'
                """
                )
                invalid_ips = cursor.fetchone()[0]

                if invalid_ips > 0:
                    issues.append(f"잘못된 IP 주소 형식: {invalid_ips}개")

                # 2. 논리적 모순 검사 (removal_date < detection_date)
                cursor.execute(
                    """
                    SELECT COUNT(*) FROM blacklist_ips
                    WHERE detection_date IS NOT NULL
                    AND removal_date IS NOT NULL
                    AND removal_date < detection_date
                """
                )
                logical_errors = cursor.fetchone()[0]

                if logical_errors > 0:
                    issues.append(f"논리적 모순 (해제일 < 탐지일): {logical_errors}개")

                # 3. 만료된 IP가 여전히 활성 상태인 경우
                cursor.execute(
                    """
                    SELECT COUNT(*) FROM blacklist_ips
                    WHERE is_active = true
                    AND removal_date IS NOT NULL
                    AND removal_date < CURRENT_DATE
                """
                )
                expired_active = cursor.fetchone()[0]

                if expired_active > 0:
                    issues.append(f"만료되었지만 활성 상태인 IP: {expired_active}개")

                cursor.close()

        except Exception as e:
            logger.error(f"❌ 데이터 무결성 검사 실패: {e}")
            issues.append(f"무결성 검사 오류: {e}")

        return issues

    def _analyze_data_freshness(self) -> Dict[str, Any]:
        """데이터 신선도 분석"""
        try:
            with db_service.get_connection() as conn:
                cursor = conn.cursor()

                # 최신 데이터 분포 분석
                cursor.execute(
                    """
                    SELECT
                        COUNT(*) FILTER (WHERE created_at >= CURRENT_DATE - INTERVAL '7 days') as last_7_days,
                        COUNT(*) FILTER (WHERE created_at >= CURRENT_DATE - INTERVAL '30 days') as last_30_days,
                        COUNT(*) FILTER (WHERE created_at >= CURRENT_DATE - INTERVAL '90 days') as last_90_days,
                        COUNT(*) as total,
                        MAX(created_at) as latest_data,
                        MIN(created_at) as oldest_data
                    FROM blacklist_ips
                """
                )

                freshness_data = cursor.fetchone()
                cursor.close()

            # 신선도 점수 계산 (최근 30일 데이터 비율 기준)
            freshness_score = 0
            if freshness_data[3] > 0:  # total > 0
                recent_ratio = freshness_data[1] / freshness_data[3]  # last_30_days / total
                freshness_score = min(100, recent_ratio * 100 * 2)  # 최대 100점

            return {
                "data_last_7_days": freshness_data[0],
                "data_last_30_days": freshness_data[1],
                "data_last_90_days": freshness_data[2],
                "freshness_score": round(freshness_score, 2),
                "latest_data_date": freshness_data[4].isoformat() if freshness_data[4] else None,
                "oldest_data_date": freshness_data[5].isoformat() if freshness_data[5] else None,
            }

        except Exception as e:
            logger.error(f"❌ 데이터 신선도 분석 실패: {e}")
            return {"freshness_score": 0}

    def _detect_duplicates(self) -> Dict[str, Any]:
        """중복 데이터 검출"""
        try:
            with db_service.get_connection() as conn:
                cursor = conn.cursor()

                # 중복 IP 검출
                cursor.execute(
                    """
                    SELECT
                        ip_address,
                        source,
                        COUNT(*) as duplicate_count
                    FROM blacklist_ips
                    GROUP BY ip_address, source
                    HAVING COUNT(*) > 1
                    ORDER BY duplicate_count DESC
                    LIMIT 10
                """
                )

                duplicate_groups = cursor.fetchall()

                # 전체 중복 통계
                cursor.execute(
                    """
                    SELECT
                        COUNT(*) - COUNT(DISTINCT ip_address, source) as total_duplicates,
                        COUNT(DISTINCT ip_address, source) as unique_combinations,
                        COUNT(*) as total_records
                    FROM blacklist_ips
                """
                )

                duplicate_stats = cursor.fetchone()
                cursor.close()

            return {
                "total_duplicates": duplicate_stats[0],
                "unique_combinations": duplicate_stats[1],
                "duplicate_groups": duplicate_groups,
                "duplicate_percentage": round(duplicate_stats[0] / duplicate_stats[2] * 100, 2)
                if duplicate_stats[2] > 0
                else 0,
            }

        except Exception as e:
            logger.error(f"❌ 중복 데이터 검출 실패: {e}")
            return {"total_duplicates": 0}

    def _perform_automatic_cleanup(self) -> List[str]:
        """자동 데이터 정제"""
        actions = []

        try:
            with db_service.get_connection() as conn:
                cursor = conn.cursor()

                # 1. 만료된 IP 비활성화
                cursor.execute(
                    """
                    UPDATE blacklist_ips
                    SET is_active = false
                    WHERE is_active = true
                    AND removal_date IS NOT NULL
                    AND removal_date < CURRENT_DATE
                """
                )
                expired_deactivated = cursor.rowcount
                if expired_deactivated > 0:
                    actions.append(f"만료된 IP {expired_deactivated}개 비활성화")

                # 2. 오래된 비활성 데이터 정리 (90일 이상)
                cursor.execute(
                    """
                    DELETE FROM blacklist_ips
                    WHERE is_active = false
                    AND (removal_date IS NULL OR removal_date < CURRENT_DATE - INTERVAL '90 days')
                    AND created_at < CURRENT_DATE - INTERVAL '90 days'
                """
                )
                old_deleted = cursor.rowcount
                if old_deleted > 0:
                    actions.append(f"오래된 비활성 데이터 {old_deleted}개 정리")

                # 3. 중복 데이터 정리 (최신 데이터 유지)
                cursor.execute(
                    """
                    DELETE FROM blacklist_ips
                    WHERE id NOT IN (
                        SELECT DISTINCT ON (ip_address, source) id
                        FROM blacklist_ips
                        ORDER BY ip_address, source, created_at DESC
                    )
                """
                )
                duplicates_removed = cursor.rowcount
                if duplicates_removed > 0:
                    actions.append(f"중복 데이터 {duplicates_removed}개 정리")

                conn.commit()
                cursor.close()

        except Exception as e:
            logger.error(f"❌ 자동 정제 실패: {e}")
            actions.append(f"자동 정제 오류: {e}")

        return actions

    def _generate_recommendations(self, quality_report: Dict) -> List[str]:
        """품질 개선 권장사항 생성"""
        recommendations = []
        metrics = quality_report.get("metrics", {})

        # 활성률 체크
        if metrics.get("active_rate", 0) < self.quality_thresholds["min_active_rate"] * 100:
            recommendations.append("활성 IP 비율이 낮습니다. 데이터 수집 빈도를 늘리는 것을 고려하세요.")

        # 신선도 체크
        if metrics.get("freshness_score", 0) < self.quality_thresholds["min_freshness_score"]:
            recommendations.append("데이터 신선도가 낮습니다. 최근 데이터 수집을 강화하세요.")

        # 중복률 체크
        if metrics.get("duplicate_rate", 0) > self.quality_thresholds["max_duplicate_rate"] * 100:
            recommendations.append("중복 데이터 비율이 높습니다. 정기적인 중복 제거를 권장합니다.")

        # 누락 필드 체크
        if metrics.get("missing_detection_date", 0) > 0:
            recommendations.append("탐지일이 누락된 데이터가 있습니다. 수집 프로세스를 점검하세요.")

        return recommendations

    def _calculate_quality_score(self, quality_report: Dict) -> int:
        """전체 품질 점수 계산"""
        metrics = quality_report.get("metrics", {})

        # 각 지표별 점수 계산 (0-100)
        active_score = min(100, metrics.get("active_rate", 0))
        freshness_score = metrics.get("freshness_score", 0)
        duplicate_score = max(0, 100 - metrics.get("duplicate_rate", 0) * 20)  # 중복률이 높을수록 감점
        integrity_score = max(0, 100 - len(quality_report.get("issues", [])) * 10)  # 이슈 당 10점 감점

        # 가중 평균 (활성률 30%, 신선도 30%, 중복률 20%, 무결성 20%)
        overall_score = active_score * 0.3 + freshness_score * 0.3 + duplicate_score * 0.2 + integrity_score * 0.2

        return int(overall_score)

    def _save_quality_report(self, quality_report: Dict):
        """품질 보고서 저장"""
        try:
            # 품질 보고서를 로그에 요약 기록
            logger.info("📊 품질 보고서 요약:")
            logger.info(f"  - 전체 점수: {quality_report.get('overall_quality_score', 0)}/100")
            logger.info(f"  - 총 IP: {quality_report.get('metrics', {}).get('total_ips', 0)}개")
            logger.info(f"  - 활성 IP: {quality_report.get('metrics', {}).get('active_ips', 0)}개")
            logger.info(f"  - 신선도: {quality_report.get('metrics', {}).get('freshness_score', 0)}")
            logger.info(f"  - 이슈: {len(quality_report.get('issues', []))}개")
            logger.info(f"  - 권장사항: {len(quality_report.get('recommendations', []))}개")

        except Exception as e:
            logger.error(f"❌ 품질 보고서 저장 실패: {e}")

    def maintain_data_retention_policy(self):
        """데이터 보존 정책 유지"""
        logger.info("🗂️ 데이터 보존 정책 적용 시작")

        try:
            with db_service.get_connection() as conn:
                cursor = conn.cursor()

                # 50,000개 IP 데이터 보존 (최신순)
                cursor.execute(
                    """
                    DELETE FROM blacklist_ips
                    WHERE id NOT IN (
                        SELECT id FROM blacklist_ips
                        ORDER BY created_at DESC, id DESC
                        LIMIT 1000000
                    )
                """
                )

                deleted_count = cursor.rowcount
                conn.commit()
                cursor.close()

            if deleted_count > 0:
                logger.info(f"📦 데이터 보존 정책 적용: {deleted_count}개 오래된 레코드 삭제")
            else:
                logger.info("📦 데이터 보존 정책: 삭제할 데이터 없음")

        except Exception as e:
            logger.error(f"❌ 데이터 보존 정책 적용 실패: {e}")


# 글로벌 인스턴스
data_quality_manager = DataQualityManager()
