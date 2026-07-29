# Blacklist 5.0.0 릴리즈 노트

정보보호팀 코드검토(2026-07-28) 지적사항 15건을 조치했습니다.

## 심각

| 항목 | 조치 |
| --- | --- |
| C-01 무결성 검증 fail-open | 목록 누락·빈 목록·목록에 있으나 없는 파일·검증 0건을 모두 설치 중단으로 처리 |
| C-02 무검증 관리자 권한 바이너리 설치 | 시스템 반영 직전 항목별 재검증. 목록에 없는 파일도 거부 |
| C-03 무결성 목록 미검증·미서명 | 설치 전 패키지 전체 검증. 목록 없으면 거부. 선택적 서명 검증 추가 |
| C-04 데이터스토어 전 인터페이스 노출 | 내부 bridge 전환. 공개 포트는 frontend 443 하나. Redis 비밀번호 필수화 |
| C-05 Collector 제어 API 무인증 | 제어 엔드포인트에 토큰 인증 구현. 상태 조회는 헬스체크용으로 개방 |
| C-06 관리자 권한 미검사 | 특권 작업 이전 검사 후 중단 |
| C-07 호스트 전체 컨테이너 중지 | 기본 동작에서 제외, `--stop-all-containers` 옵트인 |

C-05 관련하여, 4.1.0 릴리즈 노트의 "container-internal loopback 제한" 기술은 host 네트워킹 하에서 사실이 아니었으므로 정정했습니다.

## 중간

| 항목 | 조치 |
| --- | --- |
| M-01 상태 확인 오판정 | 응답 상태값 엄격 판정 |
| M-02 서비스 간 평문 통신 | 대상 서버 생성 CA로 전 구간 TLS. 상호 인증서 검증. 검증 생략 설정 없음 |
| M-03 `latest` 재태그·미동작 롤백 | 이미지 태그를 릴리즈 버전으로 고정. 죽은 롤백 코드 제거 |
| M-04 디스크 검사 위치 오류 | Docker 데이터 디렉터리 기준으로 변경, 파싱 실패 예외 처리 |
| M-05 포트 점유 경고 | 공개 포트 점유 시 중단 |
| M-06 배포 디렉터리 내 비밀 파일 | `/etc/blacklist/.env`로 이전(디렉터리 700, 파일 600) |
| M-07 특정 환경 의존 | 표준 방식으로 대체 |
| M-08 고정 시간 대기 | 컨테이너 상태 폴링(5초 간격, 180초 한도) |

## 확인 방법

설치 없이 패키지를 점검합니다. 관리자 권한이 필요 없고 시스템을 변경하지 않습니다.

```bash
bash install.sh --verify-only
```

변조 탐지는 아래 중 하나를 수행한 뒤 위 명령을 다시 실행해 확인합니다. 각각 해당 파일명과 함께 중단됩니다.

```bash
printf 'x' >> images/blacklist-app.tar.gz     # C-01
printf 'x' >> prereqs/docker-29.2.1.tgz       # C-02
rm MANIFEST.sha256                             # C-03
```

설치 후 확인합니다.

```bash
# C-04 — 출력이 없어야 정상
ss -tuln | grep -E ':(5432|6379|8545|2542)\b'

# C-05 — 토큰 없이 401
docker exec blacklist-app curl -sk --cacert /run/blacklist/ca.crt \
  -o /dev/null -w '%{http_code}\n' -X POST https://blacklist-collector:8545/trigger

# M-02 — 평문 접속 거부
docker exec blacklist-app curl -s --max-time 5 \
  -o /dev/null -w '%{http_code}\n' http://blacklist-app:2542/health
```

C-06은 일반 계정으로 `bash install.sh`를 실행해 시스템 변경 이전에 중단되는지 확인합니다. C-07은 무관한 컨테이너를 실행한 상태로 설치해 해당 컨테이너가 유지되는지 확인합니다.

## 잔여 사항

| 내용 | 상태 |
| --- | --- |
| C-03 패키지 서명 | 검증 기능은 구현 완료. 서명 생성은 조직 서명키 발급 후 적용 가능 |
| M-02 서버 계정 관리 | 서비스 간 통신은 암호화되나, 서버 접근 권한이 있으면 인증서와 설정 파일 열람 가능 |

## 업그레이드

4.1.0 설치는 그대로 올릴 수 없습니다. 설치 전에 두 가지가 필요합니다.

**1. 설정 파일 이전**

```bash
sudo install -d -m 700 /etc/blacklist
sudo cp <기존 배포 경로>/.env /etc/blacklist/.env
sudo chmod 600 /etc/blacklist/.env
```

**2. 추가된 필수 항목 입력**

필수 항목이 6개에서 9개로 늘었습니다. 아래가 없으면 검증 단계에서 중단됩니다.

```
REDIS_PASSWORD=
COLLECTOR_AUTH_TOKEN=
ADMIN_USERNAME=
ADMIN_PASSWORD=
```

기존 설정 파일을 지우고 새로 생성하면 암호화 키가 바뀌어 저장된 수집 자격증명을 복호화할 수 없습니다.

**설치**

```bash
sudo bash install.sh
```

최초 설치 시 관리자 비밀번호가 화면에 한 번 표시됩니다.
