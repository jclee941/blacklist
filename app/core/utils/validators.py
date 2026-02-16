"""
입력 검증 유틸리티
"""

import ipaddress
from typing import List, Tuple


def validate_ip(ip_str: str) -> bool:
    """IP 주소 유효성 검증"""
    try:
        ipaddress.ip_address(ip_str)
        return True
    except ValueError:
        return False


def is_private_ip(ip_str: str) -> bool:
    """
    사설 IP 대역 체크

    사설 IP 대역:
    - 10.0.0.0/8 (10.0.0.0 ~ 10.255.255.255)
    - 172.16.0.0/12 (172.16.0.0 ~ 172.31.255.255)
    - 192.168.0.0/16 (192.168.0.0 ~ 192.168.255.255)
    - 127.0.0.0/8 (Loopback)
    - 169.254.0.0/16 (Link-local)
    """
    try:
        ip = ipaddress.ip_address(ip_str)
        return ip.is_private or ip.is_loopback or ip.is_link_local
    except ValueError:
        return False


def is_public_ip(ip_str: str) -> bool:
    """공인 IP 체크 (사설 IP가 아닌 경우)"""
    try:
        ip = ipaddress.ip_address(ip_str)
        return not (ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved)
    except ValueError:
        return False


def filter_private_ips(ip_list: List[str]) -> Tuple[List[str], List[str]]:
    """
    IP 리스트에서 사설 IP 필터링

    Returns:
        (public_ips, private_ips): 공인 IP 리스트, 사설 IP 리스트
    """
    public_ips = []
    private_ips = []

    for ip in ip_list:
        if is_private_ip(ip):
            private_ips.append(ip)
        else:
            public_ips.append(ip)

    return public_ips, private_ips


def filter_public_ips_only(ip_list: List[str]) -> List[str]:
    """공인 IP만 필터링하여 반환"""
    return [ip for ip in ip_list if is_public_ip(ip)]


def validate_pagination(page: int, per_page: int, max_per_page: int = 1000) -> tuple:
    """Clamp pagination parameters to safe bounds.

    Returns:
        (page, per_page) clamped to valid ranges.
    """
    page = max(1, page)
    per_page = max(1, min(per_page, max_per_page))
    return page, per_page


def validate_string_length(value: str, field_name: str, min_len: int = 1, max_len: int = 255) -> str:
    """Validate string field length, raise ValidationError if out of bounds."""
    if not isinstance(value, str) or len(value) < min_len:
        raise ValidationError(f"{field_name} must be at least {min_len} characters")
    if len(value) > max_len:
        raise ValidationError(f"{field_name} must be at most {max_len} characters")
    return value


class ValidationError(Exception):
    """검증 오류 예외"""
