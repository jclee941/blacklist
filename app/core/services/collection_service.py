"""
수집 서비스
데이터 수집 트리거, 중지, 관리 기능 제공 - 모듈화된 아키텍처
"""

import time
from datetime import datetime
from typing import Any, Dict, List, Optional


# Enhanced logging with tagging
from ..utils.logger_config import collection_logger as logger
from .database_lease import connection_lease

# 모듈화된 컴포넌트 임포트
try:
    from .collection.collection_validator import validator
    from .collection.collection_history import history_manager
    from .collection.collection_persistence import save_collection_data
    from .collection.collection_status import status_manager
    from .collection.regtech_data import REGTECHDataCollector

    regtech_collector: Any = REGTECHDataCollector()
except ImportError as e:
    logger.warning(f"Some collection modules not available: {e}")
    validator: Any = None
    history_manager: Any = None
    save_collection_data: Any = None
    status_manager: Any = None
    regtech_collector: Any = None


class CollectionService:
    """데이터 수집 서비스 - 모듈화된 아키텍처"""

    def __init__(self, db_service: Any = None):
        self.db_service = db_service
        self.active_collections = set()
        self.collection_status = {
            "regtech": {"running": False, "last_run": None},
        }

    def trigger_collection(self, source: str) -> Dict[str, Any]:
        """개별 소스 수집 트리거 (모니터링 기능 포함)"""
        logger.log_operation("trigger_collection", "started", source=source)
        start_time = datetime.now()

        try:
            logger.info(f"Starting collection for source: {source}")

            if source in self.active_collections:
                return {
                    "success": False,
                    "error": f"{source.upper()} 수집이 이미 진행 중입니다.",
                }

            # 상태 관리자를 통한 수집 시작
            if status_manager and not status_manager.start_collection(source):
                return {
                    "success": False,
                    "error": f"{source.upper()} 수집 시작 실패",
                }

            self.active_collections.add(source)

            try:
                # 실제 수집 로직 실행
                result = self._perform_collection(source)

                # 실행 시간 계산
                execution_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)

                # 수집 이력 기록
                collected_count = result.get("collected_count", 0)
                actual_success = result.get("success", False) and collected_count > 0

                # 메트릭 로깅
                logger.log_metric("collection_time", execution_time_ms, "ms", source=source)
                logger.log_metric("collected_items", collected_count, "items", source=source)

                if history_manager:
                    history_manager.record_collection_history(
                        collection_type=source,
                        collected_count=collected_count,
                        additional_info={
                            "execution_time_ms": execution_time_ms,
                            "success": actual_success,
                            "error": (result.get("error") if not actual_success else None),
                        },
                    )

                # 수집 완료 후 데이터베이스에 저장
                if result.get("success") and result.get("data"):
                    try:
                        validated_data = (
                            validator.validate_collection_data(result["data"]) if validator else result["data"]
                        )
                        self._save_collection_data(source, validated_data)
                        logger.with_tags(action="save").info(f"데이터 저장 완료: {len(validated_data)}개")
                        result["validated_count"] = len(validated_data)
                    except Exception as save_error:
                        logger.with_tags(action="save_error").error(f"데이터 저장 실패: {save_error}")
                        if status_manager:
                            status_manager.update_collection_error(source, str(save_error))

                return result

            finally:
                self.active_collections.discard(source)
                if status_manager:
                    status_manager.stop_collection(source)

        except Exception as e:
            execution_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)

            logger.with_tags(exception=type(e).__name__).error(f"EXCEPTION in trigger_collection: {e}")

            # 오류 상태 업데이트
            if status_manager:
                status_manager.update_collection_error(source, str(e))

            # 오류 히스토리 기록
            if history_manager:
                history_manager.record_collection_history(
                    collection_type=source,
                    collected_count=0,
                    additional_info={
                        "execution_time_ms": execution_time_ms,
                        "success": False,
                        "error": str(e),
                    },
                )

            return {"success": False, "error": f"수집 중 오류 발생: {str(e)}"}

    def trigger_regtech_collection(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
    ) -> Dict[str, Any]:
        """REGTECH 수집 트리거 - Enhanced with connection validation"""
        start_time = time.time()

        try:
            logger.info(f"Starting REGTECH collection (Period: {start_date} to {end_date})")

            # Check if collection is already running
            if "regtech" in self.active_collections:
                return {
                    "success": False,
                    "error": "REGTECH 수집이 이미 진행 중입니다.",
                    "status": "already_running",
                }

            # Pre-collection validation using validator
            validation_result = (
                validator._validate_collection_prerequisites(username, password) if validator else {"valid": True}
            )
            if not validation_result["valid"]:
                return {
                    "success": False,
                    "error": "수집 전제조건 검증 실패",
                    "validation_errors": validation_result["errors"],
                    "status": "validation_failed",
                }

            # 상태 관리자를 통한 수집 시작
            if status_manager and not status_manager.start_collection("regtech"):
                return {"success": False, "error": "REGTECH 수집 상태 초기화 실패"}

            self.active_collections.add("regtech")

            try:
                # REGTECH 컬렉터를 통한 수집
                if username and password:
                    result: Dict[str, Any] = regtech_collector.collect_real_regtech_data(username, password)
                else:
                    collected_data = regtech_collector.collect_regtech_ips()
                    result = {
                        "success": len(collected_data) > 0,
                        "collected_count": len(collected_data),
                        "data": collected_data,
                        "message": f"REGTECH 수집 완료: {len(collected_data)}개 IP",
                    }

                # 실행 시간 및 메트릭 추가
                execution_time_ms = round((time.time() - start_time) * 1000, 2)
                collected_count = int(result.get("collected_count", 0) or 0)

                # 이력 기록
                if history_manager:
                    history_manager.record_collection_history(
                        collection_type="regtech",
                        collected_count=collected_count,
                        start_date=start_date,
                        end_date=end_date,
                        additional_info={
                            "execution_time_ms": execution_time_ms,
                            "success": result.get("success", False),
                            "authentication": result.get("authentication", "unknown"),
                        },
                    )

                # 성능 메트릭 추가
                result["execution_time_ms"] = execution_time_ms
                result["collected_count"] = collected_count

                return result

            finally:
                self.active_collections.discard("regtech")
                if status_manager:
                    status_manager.stop_collection("regtech")

        except Exception as e:
            execution_time_ms = round((time.time() - start_time) * 1000, 2)
            logger.error(f"REGTECH collection error: {e}")

            # 오류 상태 업데이트
            if status_manager:
                status_manager.update_collection_error("regtech", str(e))

            return {
                "success": False,
                "error": f"REGTECH 수집 중 오류 발생: {str(e)}",
                "execution_time_ms": execution_time_ms,
                "status": "system_error",
            }

    def trigger_all_collections(self) -> Dict[str, Any]:
        """전체 수집 트리거"""
        try:
            logger.info("Starting collection for all sources")

            results: Dict[str, Dict[str, Any]] = {}
            total_collected = 0
            overall_success = True

            for source in ["regtech"]:
                result = self.trigger_collection(source)
                results[source] = result

                if result.get("success"):
                    total_collected += result.get("collected_count", 0)
                else:
                    overall_success = False

            return {
                "success": overall_success,
                "results": results,
                "total_collected": total_collected,
                "message": (f"전체 수집 완료. 총 {total_collected}개 수집됨" if overall_success else "일부 수집 실패"),
            }

        except Exception as e:
            logger.error(f"All collections error: {e}")
            return {
                "success": False,
                "error": f"전체 수집 중 오류 발생: {str(e)}",
                "results": {},
            }

    def stop_all_collections(self) -> Dict[str, Any]:
        """모든 수집 중지"""
        try:
            logger.info("Stopping all collections")

            # 상태 관리자를 통한 모든 수집 중지
            result = status_manager.stop_all_collections() if status_manager else {"success": False}

            # 로컬 상태도 정리
            self.active_collections.clear()

            return result

        except Exception as e:
            logger.error(f"Stop collections error: {e}")
            return {
                "success": False,
                "error": f"수집 중지 중 오류 발생: {str(e)}",
                "stopped_sources": [],
            }

    def get_collection_stats(self) -> Dict[str, Any]:
        """수집 통계 조회 - 대시보드 및 모니터링 UI용"""
        try:
            with connection_lease(self.db_service) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    WITH stats AS (
                        SELECT
                            COUNT(*) as total_ips,
                            COUNT(*) FILTER (WHERE is_active = true) as active_ips,
                            MAX(created_at) as latest_collection
                        FROM blacklist_ips
                    ),
                    source_stats AS (
                        SELECT COALESCE(json_object_agg(data_source, cnt), '{}') as source_breakdown
                        FROM (
                            SELECT data_source, COUNT(*) as cnt
                            FROM blacklist_ips
                            GROUP BY data_source
                        ) s
                    )
                    SELECT s.total_ips, s.active_ips, s.latest_collection,
                           ss.source_breakdown
                    FROM stats s CROSS JOIN source_stats ss
                """)
                result = cursor.fetchone()
                cursor.close()

            if result:
                return {
                    "total_ips": result[0] or 0,
                    "active_ips": result[1] or 0,
                    "latest_collection": result[2].isoformat() if result[2] else None,
                    "source_breakdown": result[3] or {},
                    "success": True,
                }

            return {
                "total_ips": 0,
                "active_ips": 0,
                "latest_collection": None,
                "source_breakdown": {},
                "success": True,
            }

        except Exception as e:
            logger.error(f"Error getting collection statistics: {e}")
            return {
                "total_ips": 0,
                "active_ips": 0,
                "latest_collection": None,
                "source_breakdown": {},
                "success": False,
                "error": str(e),
            }

    def get_collection_history(self, days: int = 30, limit: int = 50) -> List[Dict[str, Any]]:
        """수집 이력 조회 - 웹 UI용"""
        try:
            if not history_manager:
                return []

            # history_manager의 get_recent_history 호출 (limit 파라미터 제거)
            return history_manager.get_recent_history(days=days)
        except Exception as e:
            logger.error(f"Error getting collection history: {e}")
            return []

    def get_collection_status(self) -> Dict[str, Any]:
        """수집 상태 조회"""
        try:
            # 상태 관리자에서 종합 상태 조회
            status_data: Dict[str, Any] = status_manager.get_collection_status() if status_manager else {}

            # 추가 통계 정보
            stats = history_manager.get_collection_statistics() if history_manager else {}
            status_data["statistics"] = stats

            # 최근 이력
            recent_history = history_manager.get_recent_history(days=7) if history_manager else []
            status_data["recent_history"] = recent_history

            return status_data

        except Exception as e:
            logger.error(f"Get collection status error: {e}")
            return {
                "collection_enabled": False,
                "error": str(e),
                "last_updated": datetime.now().isoformat(),
            }

    def expand_collection_scope(self) -> Dict[str, Any]:
        """수집 범위를 확대하여 더 많은 블랙리스트 IP 수집"""
        try:
            total_collected = 0
            collection_results = []

            # 1. REGTECH 확장 수집
            regtech_result = regtech_collector.expand_regtech_collection()
            collection_results.append(regtech_result)
            total_collected += regtech_result.get("collected_count", 0)

            # 2. 공개 위협 인텔리전스 소스 활용
            threat_intel_result = regtech_collector.collect_threat_intelligence_ips()
            collection_results.append(threat_intel_result)
            total_collected += threat_intel_result.get("collected_count", 0)

            # 3. 악성 도메인/IP 리스트 활용
            malicious_list_result = regtech_collector.collect_malicious_ip_lists()
            collection_results.append(malicious_list_result)
            total_collected += malicious_list_result.get("collected_count", 0)

            # 4. 실제 데이터만 수집 (시뮬레이션 데이터 제거됨)

            # 확장 수집 이력 기록
            if history_manager:
                history_manager.record_collection_history(
                    collection_type="expanded_scope",
                    collected_count=total_collected,
                    additional_info={
                        "sources": [r.get("source") for r in collection_results],
                        "success": total_collected > 0,
                    },
                )

            return {
                "success": True,
                "total_collected": total_collected,
                "sources": collection_results,
                "message": f"확대된 범위에서 총 {total_collected}개의 IP를 수집했습니다.",
            }

        except Exception as e:
            logger.error(f"Collection scope expansion error: {e}")
            return {
                "success": False,
                "error": f"수집 범위 확대 중 오류: {str(e)}",
                "total_collected": 0,
            }

    def test_regtech_collection(
        self, username: str, password: str, start_date: Optional[str] = None, end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """REGTECH 인증정보로 테스트 수집"""
        return regtech_collector.test_regtech_collection(username, password, start_date, end_date)

    def test_regtech_connection(self):
        """REGTECH 연결 테스트 메서드 (웹 UI 호환성)"""
        return regtech_collector.test_regtech_collection("", "")

    def _perform_collection(self, source: str) -> Dict[str, Any]:
        """실제 수집 로직 수행 (모듈화된 컬렉터 사용)"""
        try:
            logger.info(f"Performing collection for {source}")

            # 실제 IP 블랙리스트 데이터 수집
            if source.lower() == "regtech":
                collected_data = regtech_collector.collect_regtech_ips()
            else:
                logger.warning(f"Unsupported collection source: {source}")
                return {
                    "success": False,
                    "error": f"지원되지 않는 수집 소스: {source}. REGTECH만 지원됩니다.",
                    "collected_count": 0,
                }

            collected_count = len(collected_data)
            logger.info(f"Collection completed for {source}: {collected_count} real IP addresses")

            return {
                "success": True,
                "collected_count": collected_count,
                "data": collected_data,
                "message": f"{source.upper()} 실제 IP 수집 완료: {collected_count}개",
            }

        except Exception as e:
            logger.error(f"Collection performance error for {source}: {e}")
            return {
                "success": False,
                "error": f"{source} 수집 실패: {str(e)}",
                "collected_count": 0,
            }

    def _collect_regtech_ips(self) -> List[Dict[str, Any]]:
        """REGTECH IP 수집 - 스케줄러에서 호출"""
        try:
            if regtech_collector:
                return regtech_collector.collect_regtech_ips()
            else:
                logger.warning("REGTECH collector not available")
                return []
        except Exception as e:
            logger.error(f"_collect_regtech_ips error: {e}")
            return []

    def _save_collection_data(self, source: str, data: List[Dict[str, Any]]) -> bool:
        """수집된 데이터를 데이터베이스에 저장 (v3.3.5 - detection_date/removal_date 지원)"""
        if not save_collection_data:
            logger.error("Collection persistence helper not available")
            return False

        return save_collection_data(self.db_service, source, data)


from flask import current_app
from werkzeug.local import LocalProxy

collection_service = LocalProxy(lambda: current_app.extensions["collection_service"])
