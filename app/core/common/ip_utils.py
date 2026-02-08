#!/usr/bin/env python3
"""
IP 유틸리티 모듈
고도화된 GitHub Actions 워크플로우 테스트를 위한 변경사항 추가 (2025-01-09)
"""

import ipaddress
import logging

logger = logging.getLogger(__name__)


class IPUtils:
    """IP 주소 관련 유틸리티 클래스"""

    @staticmethod
    def is_valid_ip(ip_str: str) -> bool:
        """IP 주소 유효성 검사"""
        if not ip_str:
            return False

        try:
            ipaddress.ip_address(ip_str)
            return True
        except ValueError:
            return False

    @staticmethod
    def is_private_ip(ip_str: str) -> bool:
        """사설 IP 확인"""
        try:
            ip = ipaddress.ip_address(ip_str)
            return ip.is_private
        except ValueError:
            return False

    @staticmethod
    def get_ip_type(ip_str: str) -> str:
        """IP 타입 반환"""
        try:
            ip = ipaddress.ip_address(ip_str)
            if ip.is_private:
                return "private"
            elif ip.is_loopback:
                return "loopback"
            elif ip.is_multicast:
                return "multicast"
            else:
                return "public"
        except ValueError:
            return "invalid"
