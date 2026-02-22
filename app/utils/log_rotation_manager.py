#!/usr/bin/env python3
"""
로그 순환 관리 시스템 - 대용량 JSON 로그 파일 자동 순환
"""

import os
import glob
import gzip
import shutil
from datetime import datetime, timedelta
from typing import Dict
import logging

logger = logging.getLogger(__name__)


class LogRotationManager:
    """로그 파일 순환 관리자"""

    def __init__(
        self,
        log_directory: str = "/app/logs",
        max_file_size_mb: int = 10,
        max_files: int = 5,
        max_age_days: int = 7,
        compress_old_logs: bool = True,
    ):
        self.log_directory = log_directory
        self.max_file_size = max_file_size_mb * 1024 * 1024  # MB to bytes
        self.max_files = max_files
        self.max_age_days = max_age_days
        self.compress_old_logs = compress_old_logs

    def get_file_size(self, filepath: str) -> int:
        """파일 크기 반환 (바이트)"""
        try:
            return os.path.getsize(filepath)
        except (OSError, FileNotFoundError):
            return 0

    def should_rotate_file(self, filepath: str) -> bool:
        """파일이 순환되어야 하는지 확인"""
        if not os.path.exists(filepath):
            return False

        file_size = self.get_file_size(filepath)
        return file_size > self.max_file_size

    def rotate_file(self, filepath: str) -> bool:
        """단일 파일 순환"""
        if not self.should_rotate_file(filepath):
            return False

        try:
            base_name = filepath
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            # .json 확장자 제거 후 타임스탬프 추가
            if filepath.endswith(".json"):
                base_name = filepath[:-5]  # .json 제거
                new_name = f"{base_name}_{timestamp}.json"
            else:
                new_name = f"{filepath}_{timestamp}"

            # 파일 이동
            shutil.move(filepath, new_name)
            logger.info(f"로그 파일 순환: {filepath} -> {new_name}")

            # 압축 (선택사항)
            if self.compress_old_logs:
                self.compress_file(new_name)

            # 빈 파일 생성 (로깅 계속을 위해)
            with open(filepath, "w") as f:
                f.write("")

            return True

        except Exception as e:
            logger.error(f"파일 순환 실패 ({filepath}): {e}")
            return False

    def compress_file(self, filepath: str) -> bool:
        """파일 압축"""
        try:
            compressed_path = filepath + ".gz"

            with open(filepath, "rb") as f_in:
                with gzip.open(compressed_path, "wb") as f_out:
                    shutil.copyfileobj(f_in, f_out)

            # 원본 파일 삭제
            os.remove(filepath)
            logger.info(f"로그 파일 압축: {filepath} -> {compressed_path}")
            return True

        except Exception as e:
            logger.error(f"파일 압축 실패 ({filepath}): {e}")
            return False

    def cleanup_old_files(self, pattern: str) -> int:
        """오래된 로그 파일 정리"""
        cleaned_count = 0
        cutoff_time = datetime.now() - timedelta(days=self.max_age_days)

        # 패턴에 맞는 파일들 찾기
        files = glob.glob(os.path.join(self.log_directory, pattern))

        for filepath in files:
            try:
                # 파일 수정 시간 확인
                mtime = datetime.fromtimestamp(os.path.getmtime(filepath))

                if mtime < cutoff_time:
                    os.remove(filepath)
                    logger.info(f"오래된 로그 파일 삭제: {filepath}")
                    cleaned_count += 1

            except Exception as e:
                logger.error(f"파일 삭제 실패 ({filepath}): {e}")

        return cleaned_count

    def manage_file_count(self, pattern: str) -> int:
        """파일 개수 관리 (최대 개수 초과 시 오래된 파일 삭제)"""
        files = glob.glob(os.path.join(self.log_directory, pattern))

        # 수정 시간으로 정렬 (새로운 것부터)
        files.sort(key=lambda x: os.path.getmtime(x), reverse=True)

        removed_count = 0
        if len(files) > self.max_files:
            files_to_remove = files[self.max_files :]

            for filepath in files_to_remove:
                try:
                    os.remove(filepath)
                    logger.info(f"개수 초과로 로그 파일 삭제: {filepath}")
                    removed_count += 1
                except Exception as e:
                    logger.error(f"파일 삭제 실패 ({filepath}): {e}")

        return removed_count

    def get_log_statistics(self) -> Dict[str, any]:
        """로그 디렉토리 통계"""
        stats = {
            "total_files": 0,
            "total_size_mb": 0,
            "json_files": 0,
            "compressed_files": 0,
            "large_files": [],
            "directory": self.log_directory,
        }

        if not os.path.exists(self.log_directory):
            return stats

        try:
            for filename in os.listdir(self.log_directory):
                filepath = os.path.join(self.log_directory, filename)

                if os.path.isfile(filepath):
                    stats["total_files"] += 1
                    file_size = self.get_file_size(filepath)
                    stats["total_size_mb"] += file_size / (1024 * 1024)

                    if filename.endswith(".json"):
                        stats["json_files"] += 1
                    elif filename.endswith(".gz"):
                        stats["compressed_files"] += 1

                    # 큰 파일 식별
                    if file_size > self.max_file_size:
                        stats["large_files"].append(
                            {
                                "name": filename,
                                "size_mb": round(file_size / (1024 * 1024), 2),
                            }
                        )

        except Exception as e:
            logger.error(f"로그 통계 수집 실패: {e}")

        return stats

    def rotate_all_large_files(self) -> Dict[str, int]:
        """모든 큰 파일들 순환"""
        results = {"rotated": 0, "compressed": 0, "cleaned": 0, "errors": 0}

        if not os.path.exists(self.log_directory):
            return results

        try:
            # JSON 파일들 순환
            json_files = glob.glob(os.path.join(self.log_directory, "*.json"))

            for json_file in json_files:
                if self.rotate_file(json_file):
                    results["rotated"] += 1

            # 오래된 파일들 정리
            patterns_to_clean = [
                "*.json.*",  # 순환된 JSON 파일들
                "*.gz",  # 압축된 파일들
                "*.log.*",  # 순환된 로그 파일들
            ]

            for pattern in patterns_to_clean:
                results["cleaned"] += self.cleanup_old_files(pattern)
                results["cleaned"] += self.manage_file_count(pattern)

        except Exception as e:
            logger.error(f"로그 순환 작업 실패: {e}")
            results["errors"] += 1

        return results

    def schedule_maintenance(self) -> None:
        """정기 유지보수 실행"""
        logger.info("🔄 로그 순환 유지보수 시작")

        # 현재 상태 확인
        stats_before = self.get_log_statistics()
        logger.info(f"유지보수 전 통계: {stats_before['total_files']}개 파일, {stats_before['total_size_mb']:.1f}MB")

        # 순환 작업 실행
        results = self.rotate_all_large_files()

        # 완료 후 통계
        stats_after = self.get_log_statistics()
        logger.info(f"유지보수 후 통계: {stats_after['total_files']}개 파일, {stats_after['total_size_mb']:.1f}MB")

        logger.info(
            f"✅ 로그 순환 완료: 순환 {results['rotated']}개, 정리 {results['cleaned']}개, 오류 {results['errors']}개"
        )


# 전역 로그 순환 관리자
log_rotation_manager = LogRotationManager()


def perform_log_maintenance():
    """로그 유지보수 실행"""
    log_rotation_manager.schedule_maintenance()


def get_log_stats():
    """로그 통계 조회"""
    return log_rotation_manager.get_log_statistics()


if __name__ == "__main__":
    # 테스트 실행
    logger.info("로그 순환 시스템 테스트:")

    # 통계 출력
    stats = get_log_stats()
    logger.info(f"통계: {stats}")

    # 유지보수 실행
    perform_log_maintenance()
