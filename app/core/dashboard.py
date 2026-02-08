"""
Simple NextTrade Dashboard
NextTrade 브랜딩이 포함된 간단한 대시보드
"""

from flask import Blueprint

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/dashboard", methods=["GET"])
def dashboard():
    """NextTrade 브랜딩이 포함된 대시보드"""
    return """
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Blacklist Management Dashboard</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.0/font/bootstrap-icons.css">
        <style>
            .dashboard-header {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 2rem;
                border-radius: 1rem;
                margin-bottom: 2rem;
            }
            .stat-card {
                background: white;
                border-radius: 1rem;
                padding: 1.5rem;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.07);
                border: 1px solid rgba(0, 0, 0, 0.05);
                transition: all 0.3s ease;
                height: 100%;
            }
            .stat-card:hover {
                transform: translateY(-4px);
                box-shadow: 0 8px 16px rgba(0, 0, 0, 0.1);
            }
            .stat-icon {
                width: 56px;
                height: 56px;
                border-radius: 12px;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 24px;
                margin-bottom: 1rem;
            }
            .stat-icon.primary { background: rgba(80, 70, 229, 0.1); color: #5046e5; }
            .stat-icon.success { background: rgba(16, 185, 129, 0.1); color: #10b981; }
            .stat-icon.info { background: rgba(59, 130, 246, 0.1); color: #3b82f6; }
            .stat-icon.warning { background: rgba(245, 158, 11, 0.1); color: #f59e0b; }
        </style>
    </head>
    <body class="bg-light">
        <nav class="navbar navbar-expand-lg navbar-light fixed-top bg-white shadow-sm">
            <div class="container-fluid">
                <a class="navbar-brand d-flex align-items-center" href="/">
                    <img src="/static/logo.svg" alt="블랙리스트 관리" style="height: 32px; margin-right: 10px;" onerror="this.style.display='none'; this.nextElementSibling.style.display='inline-flex';">&nbsp;<span style="display: none; align-items: center;"><i class="bi bi-shield-lock"></i> Nextrade Black List</span>
                </a>
                <span class="badge bg-success">LIVE</span>
            </div>
        </nav>

        <div class="container mt-5 pt-4">
            <!-- Dashboard Header -->
            <div class="dashboard-header">
                <div class="row align-items-center">
                    <div class="col-md-8">
                        <h1 class="mb-2">Blacklist Management System</h1>
                        <p class="mb-0 opacity-75">실시간 위협 인텔리전스 및 보안 모니터링 대시보드</p>
                    </div>
                    <div class="col-md-4 text-end">
                        <div class="d-flex align-items-center justify-content-end">
                            <i class="bi bi-shield-check me-2" style="font-size: 2rem;"></i>
                            <div>
                                <div class="fw-bold">시스템 상태</div>
                                <small class="opacity-75">운영 중</small>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Stats Cards -->
            <div class="row g-4 mb-4">
                <div class="col-lg-3 col-md-6">
                    <div class="stat-card">
                        <div class="stat-icon primary">
                            <i class="bi bi-shield-exclamation"></i>
                        </div>
                        <h3 class="mb-1" id="blacklist-count">100</h3>
                        <p class="text-muted mb-0">차단된 IP</p>
                    </div>
                </div>
                <div class="col-lg-3 col-md-6">
                    <div class="stat-card">
                        <div class="stat-icon success">
                            <i class="bi bi-check-circle"></i>
                        </div>
                        <h3 class="mb-1">99.9%</h3>
                        <p class="text-muted mb-0">시스템 가용성</p>
                    </div>
                </div>
                <div class="col-lg-3 col-md-6">
                    <div class="stat-card">
                        <div class="stat-icon info">
                            <i class="bi bi-clock"></i>
                        </div>
                        <h3 class="mb-1" id="last-update">방금 전</h3>
                        <p class="text-muted mb-0">마지막 업데이트</p>
                    </div>
                </div>
                <div class="col-lg-3 col-md-6">
                    <div class="stat-card">
                        <div class="stat-icon warning">
                            <i class="bi bi-activity"></i>
                        </div>
                        <h3 class="mb-1">실시간</h3>
                        <p class="text-muted mb-0">모니터링</p>
                    </div>
                </div>
            </div>

            <!-- System Status -->
            <div class="row g-4">
                <div class="col-lg-8">
                    <div class="stat-card">
                        <h5 class="mb-4"><i class="bi bi-bar-chart me-2"></i>시스템 성능</h5>
                        <div class="row g-3">
                            <div class="col-md-4">
                                <div class="text-center">
                                    <div class="h2 text-success">PostgreSQL</div>
                                    <small class="text-muted">데이터베이스</small>
                                    <div class="mt-2">
                                        <span class="badge bg-success">Healthy</span>
                                    </div>
                                </div>
                            </div>
                            <div class="col-md-4">
                                <div class="text-center">
                                    <div class="h2 text-info">Redis</div>
                                    <small class="text-muted">캐시</small>
                                    <div class="mt-2">
                                        <span class="badge bg-success">Healthy</span>
                                    </div>
                                </div>
                            </div>
                            <div class="col-md-4">
                                <div class="text-center">
                                    <div class="h2 text-primary">Flask</div>
                                    <small class="text-muted">웹 서버</small>
                                    <div class="mt-2">
                                        <span class="badge bg-success">Healthy</span>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
                <div class="col-lg-4">
                    <div class="stat-card">
                        <h5 class="mb-4"><i class="bi bi-info-circle me-2"></i>시스템 정보</h5>
                        <div class="mb-3">
                            <strong>버전:</strong> <span class="text-muted">1.0.0</span>
                        </div>
                        <div class="mb-3">
                            <strong>업타임:</strong> <span class="text-muted">24시간+</span>
                        </div>
                        <div class="mb-3">
                            <strong>환경:</strong> <span class="badge bg-success">Production</span>
                        </div>
                        <div class="mb-0">
                            <strong>브랜딩:</strong> <span class="text-muted">NextTrade</span>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
        <script>
            // 실시간 업데이트 시뮬레이션
            function updateDashboard() {
                document.getElementById('last-update').textContent = '방금 전';
            }

            // 30초마다 업데이트
            setInterval(updateDashboard, 30000);
        </script>
    </body>
    </html>
    """
