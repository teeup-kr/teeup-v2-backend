# 로드 테스트 스캐폴드

이 디렉터리는 온보딩, 클럽, 모임, 정산, 점수 입력 흐름을 Locust로 실행하기 위한 스크립트를 포함합니다.

## 사전 준비

- Python 3.11+
- 백엔드 서버 실행 상태

의존성 설치:

```bash
pip install -r scripts/loadtest/requirements.txt
```

## 서버 환경변수

내부 로드테스트 엔드포인트 활성화:

```bash
ENABLE_LOADTEST_AUTH_MOCK=true
LOADTEST_AUTH_MOCK_ALLOWED_IPS=127.0.0.1,::1
```

`AuthProvider.ensure_bootstrap()`가 테스트 시작 시 1회 실행되며 아래를 보장합니다.

- 최소 지역 시드 (`sido=11`, `gungu=11010`)
- 필수 약관 3종 + 선택 약관 1종

DB 커넥션 풀(로드테스트 시 권장 조정):

```bash
DB_POOL_SIZE=40
DB_MAX_OVERFLOW=80
DB_POOL_TIMEOUT=60
DB_POOL_RECYCLE=1800
DB_POOL_PRE_PING=true
```

## 클라이언트 환경변수

- `LOADTEST_BASE_URL`: API 호스트 (기본값: `http://127.0.0.1:8200`)
- `LOADTEST_RUN_ID`: 실행 식별자 (기본값: `local`)
- `LOADTEST_USER_WAIT_MIN`: 태스크 간 최소 대기(초, 기본값: `1`)
- `LOADTEST_USER_WAIT_MAX`: 태스크 간 최대 대기(초, 기본값: `3`)
- `LOADTEST_USERS`: 헤드리스 총 사용자 수 (기본값: `50`)
- `LOADTEST_SPAWN_RATE`: 헤드리스 초당 사용자 생성 수 (기본값: `5`)
- `LOADTEST_RUN_TIME`: 헤드리스 실행 시간 (기본값: `10m`)

## 테스트 시작 명령어

1) 의존성 설치

```bash
pip install -r scripts/loadtest/requirements.txt
```

2) 백엔드 실행 (로드테스트용 환경변수 포함)

```bash
export ENABLE_LOADTEST_AUTH_MOCK=true
export LOADTEST_AUTH_MOCK_ALLOWED_IPS=127.0.0.1,::1
export DB_POOL_SIZE=40
export DB_MAX_OVERFLOW=80
export DB_POOL_TIMEOUT=60
export DB_POOL_RECYCLE=1800
export DB_POOL_PRE_PING=true
python main.py
```

3) Locust UI 모드 시작

```bash
export LOADTEST_BASE_URL=http://127.0.0.1:8200
export LOADTEST_RUN_ID=run-001
locust -f scripts/loadtest/locustfile.py --host "$LOADTEST_BASE_URL"
```

4) Locust 헤드리스 모드 시작

```bash
export LOADTEST_BASE_URL=http://127.0.0.1:8200
export LOADTEST_RUN_ID=run-001
export LOADTEST_USERS=100
export LOADTEST_SPAWN_RATE=10
export LOADTEST_RUN_TIME=15m
scripts/loadtest/run_headless.sh
```

5) 결과 요약 리포트 생성

```bash
python scripts/loadtest/report_parser.py scripts/loadtest/output/loadtest_stats.csv
```

## 실행

UI 모드:

```bash
locust -f scripts/loadtest/locustfile.py --host "${LOADTEST_BASE_URL:-http://127.0.0.1:8200}"
```

헤드리스 모드:

```bash
scripts/loadtest/run_headless.sh
```

기본 CSV 출력 경로:

- `scripts/loadtest/output/`

요약 리포트 생성:

```bash
python scripts/loadtest/report_parser.py scripts/loadtest/output/loadtest_stats.csv
```

팀 편성 line-profiler 실행:

```bash
python scripts/loadtest/profile_team_formation.py --meeting-id <MEETING_ID> --mode GENDER_MIXED_RANDOM --team-size 4
```

## 포함 파일

- `scripts/loadtest/locustfile.py`: Locust 진입점 및 사용자 클래스
- `scripts/loadtest/lib/auth_provider.py`: bootstrap, OAuth mock, 온보딩 헬퍼
- `scripts/loadtest/lib/scenario_user.py`: 일반 사용자 시나리오
- `scripts/loadtest/lib/scenario_manager.py`: 리더/매니저 시나리오
- `scripts/loadtest/lib/state_store.py`: 공유 런타임 상태 저장
- `scripts/loadtest/report_parser.py`: Locust CSV 요약 파서
- `scripts/loadtest/run_headless.sh`: 헤드리스 실행 스크립트
- `scripts/loadtest/profile_team_formation.py`: 팀 편성 line-profiler 실행 스크립트

## 현재 시나리오 범위

일반 사용자:
- OAuth mock 로그인
- 필수 약관 동의
- 프로필 완성
- 공유 클럽 가입 신청
- 공유 모임 참가 신청
- 라운딩 완료 모임 간단 점수 입력

매니저/리더 사용자:
- 관리 클럽 확보(없으면 생성)
- 대기 멤버 승인
- 라운딩 모임 생성
- 팀 편성 최소 인원 충족(게스트 추가)
- 모집 마감 -> 자동 팀 편성 -> 팀 확정
- 라운딩 시작 -> 라운딩 종료
- 라운딩 정산 생성 -> 정산 확정
- 모임 완료

## 로드테스트 추가요소 체크리스트

실행 전 체크:
- [ ] `ENABLE_LOADTEST_AUTH_MOCK`와 `LOADTEST_AUTH_MOCK_ALLOWED_IPS`가 올바르게 설정됨
- [ ] `LOADTEST_RUN_ID`를 실행 단위로 고유하게 지정함
- [ ] 목표 부하 파라미터(`LOADTEST_USERS`, `LOADTEST_SPAWN_RATE`, `LOADTEST_RUN_TIME`)를 기록함
- [ ] 테스트 대상 브랜치/커밋/DB 상태를 기록함

데이터/권한 운영 체크:
- [ ] run_id 기준 테스트 데이터 생성/정리 정책이 정해져 있음
- [ ] 리더/매니저 계정 전이 규칙(승인 지연, 배치 승인 포함)이 정해져 있음
- [ ] 테스트 계정 prefix 외 사용자 데이터는 조작하지 않음

성능/품질 기준 체크:
- [ ] 오류 예산(예: 5xx 비율, 지속 시간) 중단 조건이 정의됨
- [ ] p95/p99 목표값과 허용 임계치를 정의함
- [ ] 재현성 확보를 위해 실행 파라미터 세트(run config)를 저장함

리포트 체크:
- [ ] 총 요청/실패율과 엔드포인트별 p95, 실패 Top N을 수집함
- [ ] 워크플로우 단계별 성공률(가입/약관/프로필/클럽/모임/정산/점수)을 수집함
- [ ] 결과 리포트에 실행 시간, 사용자 수, spawn rate, run_id를 포함함

프로파일링 체크:
- [ ] `line-profiler`로 팀 편성 핵심 함수 프로파일링 수행
- [ ] 필요 시 `py-spy`/`scalene` 등 샘플링 프로파일러 결과를 병행 수집

## 참고

- `settlement/rounding` payload는 백엔드에서 dict 기반으로 처리됩니다.
- 정산 검증 규칙이 변경되면 `scripts/loadtest/lib/scenario_manager.py`의 payload를 먼저 갱신하세요.

## 본 코드 변경내역

서버 측 변경:
- `config.py`: 로드테스트 내부 인증 제어 환경변수 추가 (`ENABLE_LOADTEST_AUTH_MOCK`, `LOADTEST_AUTH_MOCK_ALLOWED_IPS`)
- `main.py`: 내부 로드테스트 라우터 등록 (`loadtest_router`)
- `routers/internal/__init__.py`: `loadtest_router` export 추가
- `routers/internal/loadtest.py`: 내부 테스트 API 추가
  - `POST /api/v1/internal/loadtest/oauth-mock` (OAuth mock 로그인/토큰 발급)
  - `POST /api/v1/internal/loadtest/bootstrap` (약관/지역 최소 시드 보장)
  - 플래그 + 허용 IP 기반 접근 가드

로드테스트 스크립트 변경:
- `scripts/loadtest/locustfile.py`: 사용자 타입(Regular/Manager) 및 태스크 구성
- `scripts/loadtest/lib/auth_provider.py`: bootstrap 1회 실행 + OAuth mock + 약관 동의 + 프로필 완성
- `scripts/loadtest/lib/scenario_user.py`: 일반 사용자 시나리오(클럽/모임/점수 입력)
- `scripts/loadtest/lib/scenario_manager.py`: 운영자 시나리오(클럽 관리/승인/워크플로우/정산/완료)
- `scripts/loadtest/lib/state_store.py`: 사용자/클럽/모임 공유 상태 저장소

실행/분석 보조 추가:
- `scripts/loadtest/run_headless.sh`: 헤드리스 실행 스크립트
- `scripts/loadtest/report_parser.py`: Locust CSV 요약 파서
- `scripts/loadtest/profile_team_formation.py`: 팀 편성 line-profiler 실행 스크립트
- `scripts/loadtest/requirements.txt`: 로드테스트 의존성 정의
