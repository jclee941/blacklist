# REGTECH Collector Rate Limiting

**작성일**: 2026-02-15
**버전**: 3.5.64
**목적**: 외부 API 차단 방지를 위한 지능형 레이트 리미팅

---

## 📋 개요

REGTECH 포털의 API 차단을 방지하기 위해 **Token Bucket 알고리즘** 기반 Rate Limiter를 도입했습니다.

### 주요 특징

- ✅ **Token Bucket 알고리즘**: 버스트 트래픽 허용하면서 평균 요청 속도 제어
- ✅ **적응형 속도 조절**: 성공/실패에 따라 자동으로 요청 속도 조절
- ✅ **Exponential Backoff**: 실패 시 지수적으로 대기 시간 증가
- ✅ **스레드 안전**: 멀티스레드 환경에서 안전한 동작
- ✅ **통계 추적**: 요청 횟수, 대기 시간, 실패 횟수 등 추적
- ✅ **무한 재시도 방지**: 최대 재시도 횟수 및 백오프 시간 제한

---

## 🔧 설정

### 기본 설정 (권장)

```python
regtech_rate_limiter = AdaptiveRateLimiter(
    initial_rate=2.0,    # 초당 2개 요청 (0.5초 간격)
    min_rate=0.5,        # 최소 초당 0.5개 (2초 간격)
    max_rate=5.0,        # 최대 초당 5개 (0.2초 간격)
    burst_size=5,        # 버스트 5개까지 허용
    backoff_factor=2.0,  # 실패 시 2배씩 증가
    max_backoff=300.0,   # 최대 5분 대기
)
```

### 재시도 제한

- **인증**: 최대 3번 시도
- **수집**: max_pages 제한 (기본 100페이지)
- **백오프**: 최대 5분 대기 후 종료

---

## 🚀 사용 방법

### 1. 인증 시 Rate Limiting

```python
def authenticate(self, username: str, password: str) -> bool:
    max_retries = 3
    for attempt in range(max_retries):
        # Rate Limiting 적용
        self.rate_limiter.wait_if_needed()

        # 인증 요청 수행
        result = subprocess.run(curl_cmd, ...)

        if success:
            # 성공 피드백
            self.rate_limiter.on_success()
            return True
        else:
            # 실패 피드백 (자동 백오프)
            self.rate_limiter.on_failure(error_code=status_code)

    return False
```

### 2. 데이터 수집 시 Rate Limiting

```python
def _collect_single_page(self, page_num: int, ...):
    # Rate Limiting 적용
    self.rate_limiter.wait_if_needed()

    # 데이터 요청
    response = self.session.post(data_url, ...)

    if response.status_code == 200:
        # 성공 피드백
        self.rate_limiter.on_success()
        return page_data
    else:
        # 실패 피드백 (429, 503 등 자동 감지)
        self.rate_limiter.on_failure(error_code=response.status_code)
        return []
```

### 3. 통계 확인

```python
# 세션 정보에 Rate Limiter 통계 포함
session_info = regtech_collector.get_session_info()
rate_stats = session_info["rate_limiter"]

# 출력 예시:
{
    "rate_limit": "2.0 req/s",
    "burst_size": 5,
    "current_tokens": 3.45,
    "total_requests": 152,
    "total_waits": 87,
    "avg_wait_time": 0.234,
    "failure_count": 2,
    "current_backoff": 4.0,
    "requests_last_minute": 18,
    "last_request": "2025-10-30T14:23:15.123456"
}
```

---

## 📊 알고리즘 상세

### Token Bucket 알고리즘

```
토큰 버킷 (최대 burst_size 개)
  ↓
시간 경과에 따라 토큰 재충전 (rate 속도)
  ↓
요청 시 토큰 소비 (1개)
  ↓
토큰 부족 시 대기 (자동 계산)
```

**특징**:
- **버스트 허용**: 버킷에 토큰이 있으면 연속 요청 가능
- **평균 속도 제어**: 장기적으로 rate 속도 유지
- **자동 대기**: 토큰 부족 시 자동으로 대기 시간 계산

### 적응형 속도 조절

```
연속 성공 10회 → 속도 20% 증가 (최대 max_rate)
  ↓
실패 발생 → 속도 50% 감소 (최소 min_rate)
  ↓
지속적으로 성공/실패에 따라 조절
```

### Exponential Backoff

```
실패 횟수 | 백오프 시간
---------|------------
1        | 0.5초 × 2^1 = 1초
2        | 0.5초 × 2^2 = 2초
3        | 0.5초 × 2^3 = 4초
4        | 0.5초 × 2^4 = 8초
5        | 0.5초 × 2^5 = 16초
...      | ...
최대     | 300초 (5분)
```

**특별 처리**:
- HTTP 429 (Too Many Requests) → 백오프 2배 증가
- HTTP 503 (Service Unavailable) → 백오프 2배 증가

---

## ⚠️ 주의사항

### 1. 무한 재시도 방지

Rate Limiter는 **자동 백오프를 제공**하지만, **재시도 횟수는 제한하지 않습니다**.

```python
# ✅ CORRECT: 명시적 재시도 제한
max_retries = 3
for attempt in range(max_retries):
    self.rate_limiter.wait_if_needed()
    result = make_request()
    if result.success:
        self.rate_limiter.on_success()
        return result
    else:
        self.rate_limiter.on_failure()

# ❌ WRONG: 무한 재시도
while True:
    self.rate_limiter.wait_if_needed()
    result = make_request()
    if result.success:
        return result
```

### 2. 백오프 최대 시간

최대 백오프 시간은 **5분 (300초)**로 제한됩니다.

5분 동안 대기 후에도 실패하면 **재시도를 중단**해야 합니다.

### 3. 중복 sleep() 제거

Rate Limiter 도입 후 기존의 고정 sleep() 호출은 제거되었습니다:

```python
# ❌ BEFORE: 고정 대기 시간
time.sleep(0.5)  # 페이지 간 간격
time.sleep(1)    # 전략 간 간격

# ✅ AFTER: Rate Limiter가 자동 처리
self.rate_limiter.wait_if_needed()
```

---

## 📈 성능 최적화

### 적응형 조절 예시

```
초기 속도: 2.0 req/s
  ↓
연속 10회 성공 → 2.4 req/s (20% 증가)
  ↓
연속 10회 성공 → 2.88 req/s (20% 증가)
  ↓
실패 발생 → 1.44 req/s (50% 감소)
  ↓
연속 10회 성공 → 1.73 req/s (20% 증가)
  ↓
최종적으로 안정적인 속도 유지
```

### 통계 분석

```python
# Rate Limiter 통계로 성능 분석
rate_stats = rate_limiter.get_stats()

# 평균 대기 시간이 길면 → rate 증가 필요
if rate_stats["avg_wait_time"] > 1.0:
    print("⚠️ 평균 대기 시간이 길어 처리 속도 저하")

# 실패 횟수가 많으면 → rate 감소 필요
if rate_stats["failure_count"] > 5:
    print("⚠️ 실패 횟수 증가, API 과부하 가능성")
```

---

## 🔍 디버깅

### 로그 레벨 설정

```python
# Rate Limiter 디버그 로그 활성화
import logging
logging.getLogger("collector.core.rate_limiter").setLevel(logging.DEBUG)
```

### 주요 로그 메시지

```
✅ 토큰 획득: 1개 소비, 잔여=4.23, 대기=0.000초
⏳ 토큰 대기: 0.234초
✅ 요청 성공 - 백오프 리셋
⚠️ API Rate Limit 감지 (HTTP 429): 8.0초 대기
⚠️ 요청 실패 #3: 4.0초 백오프
⏸️  백오프 대기: 4.0초
📈 요청 속도 증가: 2.00 → 2.40 req/s (연속 성공 10회)
📉 요청 속도 감소: 2.40 → 1.20 req/s (실패 1회)
```

---

## 🛠️ 커스터마이징

### 보수적 설정 (안전 우선)

```python
regtech_rate_limiter = AdaptiveRateLimiter(
    initial_rate=1.0,    # 초당 1개 (1초 간격)
    min_rate=0.25,       # 최소 4초 간격
    max_rate=2.0,        # 최대 0.5초 간격
    burst_size=3,        # 버스트 3개
    backoff_factor=3.0,  # 실패 시 3배 증가
    max_backoff=600.0,   # 최대 10분 대기
)
```

### 공격적 설정 (성능 우선)

```python
regtech_rate_limiter = AdaptiveRateLimiter(
    initial_rate=5.0,    # 초당 5개 (0.2초 간격)
    min_rate=1.0,        # 최소 1초 간격
    max_rate=10.0,       # 최대 0.1초 간격
    burst_size=10,       # 버스트 10개
    backoff_factor=1.5,  # 실패 시 1.5배 증가
    max_backoff=60.0,    # 최대 1분 대기
)
```

---

## 📚 참고자료

- **Token Bucket Algorithm**: https://en.wikipedia.org/wiki/Token_bucket
- **Exponential Backoff**: https://en.wikipedia.org/wiki/Exponential_backoff
- **Rate Limiting Best Practices**: https://cloud.google.com/architecture/rate-limiting-strategies-techniques

---

## 🔄 버전 히스토리

### v3.5.64 (2026-02-15)
- ✅ 문서 현행화 (버전/날짜 반영)

### v3.3.8 (2025-10-30)
- ✅ Token Bucket 알고리즘 기반 Rate Limiter 도입
- ✅ 적응형 속도 조절 기능 추가
- ✅ Exponential Backoff 통합
- ✅ 통계 추적 및 디버깅 기능 추가
- ✅ 무한 재시도 방지 (최대 재시도 제한)
- ✅ 기존 고정 sleep() 제거

---

**마지막 업데이트**: 2026-02-15
**유지보수**: 정기적으로 rate_limiter 통계를 모니터링하여 최적 설정 유지
