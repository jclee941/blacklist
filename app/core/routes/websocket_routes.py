#!/usr/bin/env python3
"""
WebSocket 실시간 통신 라우트
Flask-SocketIO를 사용한 실시간 업데이트
"""

import logging
from flask import current_app
from flask_socketio import emit, join_room, leave_room
from datetime import datetime

logger = logging.getLogger(__name__)


# WebSocket 이벤트 핸들러 (Blueprint 대신 직접 등록)
def register_websocket_handlers(socketio):
    """WebSocket 이벤트 핸들러 등록"""

    @socketio.on("connect")
    def handle_connect():
        """클라이언트 연결 처리"""
        logger.info("🔌 WebSocket 클라이언트 연결")
        emit("connected", {"message": "WebSocket 연결 성공", "timestamp": datetime.now().isoformat()})

    @socketio.on("disconnect")
    def handle_disconnect():
        """클라이언트 연결 해제 처리"""
        logger.info("🔌 WebSocket 클라이언트 연결 해제")

    @socketio.on("subscribe_stats")
    def handle_subscribe_stats():
        """실시간 통계 구독"""
        join_room("stats_room")
        logger.info("📊 통계 룸 구독")

        # 초기 통계 전송
        # Use dependency injection via app.extensions
        optimized_blacklist_service = current_app.extensions["optimized_blacklist_service"]
        stats = optimized_blacklist_service.get_unified_statistics()

        emit("stats_update", stats, room="stats_room")

    @socketio.on("unsubscribe_stats")
    def handle_unsubscribe_stats():
        """실시간 통계 구독 해제"""
        leave_room("stats_room")
        logger.info("📊 통계 룸 구독 해제")

    @socketio.on("subscribe_collection")
    def handle_subscribe_collection():
        """수집 상태 구독"""
        join_room("collection_room")
        logger.info("🔄 수집 룸 구독")

        # 초기 수집 상태 전송
        # Use dependency injection via app.extensions
        optimized_blacklist_service = current_app.extensions["optimized_blacklist_service"]
        status = optimized_blacklist_service.get_collection_status()

        emit("collection_status", status, room="collection_room")

    return socketio


def broadcast_stats_update(socketio, stats_data):
    """모든 구독자에게 통계 업데이트 브로드캐스트"""
    try:
        socketio.emit("stats_update", stats_data, room="stats_room")
        logger.info("📡 통계 업데이트 브로드캐스트")
    except Exception as e:
        logger.error(f"❌ 통계 브로드캐스트 실패: {e}")


def broadcast_new_blacklist(socketio, ip_data):
    """새로운 블랙리스트 알림 브로드캐스트"""
    try:
        socketio.emit("new_blacklist", ip_data, room="stats_room")
        logger.info(f"🚨 새 블랙리스트 알림: {ip_data.get('ip_address')}")
    except Exception as e:
        logger.error(f"❌ 블랙리스트 알림 실패: {e}")


def broadcast_collection_status(socketio, status_data):
    """수집 상태 업데이트 브로드캐스트"""
    try:
        socketio.emit("collection_status", status_data, room="collection_room")
        logger.info("📡 수집 상태 브로드캐스트")
    except Exception as e:
        logger.error(f"❌ 수집 상태 브로드캐스트 실패: {e}")
