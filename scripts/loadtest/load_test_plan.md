# 로드 테스트 계획 (재구성)

## 1. 목적

- 실제 사용자 플로우(가입 → 약관 → 프로필 → 클럽/모임 활동 → 정산/점수)를 그대로 부하에 반영한다.
- 랜덤 가입 시점, 최대 사용자 수 `N`, 테스트 시간 `X분` 제약 안에서 병목 구간을 식별한다.
- API 응답 성능과 함께 권한/워크플로우 정책이 부하 상황에서도 깨지지 않는지 검증한다.

## 2. 현재 코드 기준 확정 정책 (테스트 전제)

아래는 현재 코드에서 확인된 사실이다.

### 2.1 인증/온보딩

- OAuth 가입/로그인: `POST /api/v1/auth/oauth/google/callback`
- 필수 약관 미동의 사용자는 `get_current_active_user` 의존 API에서 `403` 차단.
- 약관 동의 전용 흐름은 `check_terms_agreement=False`로 허용:
  - `GET /api/v1/terms/active/`
  - `POST /api/v1/terms/agreements/`
  - `POST /api/v1/terms/agreements/bulk`

### 2.2 프로필 완성 강제

- 클럽 가입 신청(`POST /api/v1/clubs/{club_id}/join`) 전 아래 필드 필수:
  - `realname`
  - `phone_number`
  - `birthdate`
  - `gender`
- 프로필 업데이트: `PUT /api/v1/users/me`

### 2.3 클럽/모임 권한

- 모임 생성은 클럽 `LEADER`/`MANAGER`만 가능:
  - `POST /api/v1/meetings`
  - `POST /api/v1/rounds`
  - `POST /api/v1/socials`
- 클럽 리더/매니저는 소속 클럽의 private 모임 조회 허용 로직이 반영되어 있다.
- 모임 진행 단계(모집 마감, 팀 편성, 진행 시작/종료, 정산 확정 등)는 개설자 또는 클럽 리더/매니저 권한 체크를 사용한다.

## 3. 테스트 단위 시나리오를 API 단계로 매핑

요청하신 사용자 단위를 상태 머신으로 정리한다.

### 3.1 공통 상태 머신

1. OAuth 신규 가입/로그인
2. 약관 동의
3. 프로필 완성
4. 클럽 탐색
5. 클럽 가입 신청 또는 클럽 생성
6. 클럽 소속 확정
7. 모임 생성(리더/매니저) 또는 모임 검색/참가
8. 모임 소속 확정
9. 모집 확정/팀 편성/라운딩 진행
10. 정산 생성/확정
11. 라운딩 종료 후 점수 입력(간단 점수 또는 홀별)
12. 6 또는 7 단계로 루프

### 3.2 단계별 주요 API

- 1단계
  - `POST /api/v1/auth/oauth/google/callback`
- 2단계
  - `GET /api/v1/terms/active/`
  - `POST /api/v1/terms/agreements/bulk`
- 3단계
  - `PUT /api/v1/users/me`
- 4단계
  - `GET /api/v1/clubs`
- 5단계
  - 가입 신청: `POST /api/v1/clubs/{club_id}/join`
  - 생성: `POST /api/v1/clubs`
- 6단계
  - 승인 플로우(리더/매니저 계정): `POST /api/v1/clubs/{club_id}/members/{user_id}/approve`
- 7단계
  - 생성: `POST /api/v1/meetings?club_id={club_display_id_or_id}`
  - 검색: `GET /api/v1/meetings`, `GET /api/v1/meetings/rounding`, `GET /api/v1/rounds`, `GET /api/v1/socials`
  - 참가: `POST /api/v1/meetings/{meeting_id}/apply`
- 9단계
  - 모집 조기 마감: `POST /api/v1/meetings/{meeting_id}/close-application`
  - 팀 편성 시작: `POST /api/v1/meetings/{meeting_id}/start-team-formation`
  - 자동 편성: `POST /api/v1/meetings/{meeting_id}/teams/auto-formation`
  - 편성 확정: `POST /api/v1/meetings/{meeting_id}/teams/confirm`
  - 진행 시작: `POST /api/v1/meetings/{meeting_id}/start-rounding`
  - 진행 종료: `POST /api/v1/meetings/{meeting_id}/complete-rounding`
- 10단계
  - 라운딩 정산: `POST /api/v1/meetings/{meeting_id}/settlement/rounding`
  - 소셜 정산: `POST /api/v1/meetings/{meeting_id}/settlement/social`
  - 정산 확정: `POST /api/v1/meetings/{meeting_id}/settlement/confirm`
  - 모임 완료: `POST /api/v1/meetings/{meeting_id}/complete`
- 11단계
  - 간단 점수: `POST /api/v1/meetings/{meeting_id}/participants/{participant_id}/simple-score`
  - 홀별 점수: `POST /api/v1/meetings/{meeting_id}/participants/{participant_id}/scores`

## 4. 워크로드 모델

### 4.1 입력 파라미터

- `N`: 테스트 중 최대 활성 회원 수
- `X`: 총 테스트 시간(분)
- `lambda_join`: 분당 신규 가입 도착률(랜덤 가입 제어)
- `club_create_ratio`: 클럽 생성 비율
- `meeting_create_ratio`: 모임 생성 비율(리더/매니저 계정에서만)
- `round_vs_social_ratio`: 라운딩/소셜 비중

### 4.2 추천 부하 단계

- Warm-up: 5분 (저강도)
- Ramp-up: 10~20분 (목표 동시 사용자까지 선형 증가)
- Steady: 30~60분 (핵심 측정)
- Spike: 5분 (2~3배 급증)
- Soak: 2~4시간 (메모리/커넥션 누수 확인)

### 4.3 사용자 행동 분포 예시

- 온보딩 신규 사용자: 20%
- 기존 사용자 클럽 활동(검색/가입/승인 대기): 25%
- 모임 활동(검색/참가): 35%
- 운영자 활동(생성/마감/편성/정산): 20%

## 5. OAuth만 있는 환경에서 테스트 계정 식별/생성 방안

### 5.1 계정 식별 규칙

- 이메일: `load+{run_id}-{vu_id}@teeup.run`
- provider_id: `load-{run_id}-{vu_id}`
- nickname: `load_{run_id}_{vu_id}`

`create_or_get_oauth_user`가 이메일/provider_id로 조회하므로 위 규칙이면 재실행 시 추적이 쉽다.

### 5.2 OAuth mock 전략 (권장 순서)

1. 권장: 로드테스트 전용 내부 엔드포인트 추가

- 예: `POST /api/v1/internal/loadtest/oauth-mock`
- 입력: `provider_id`, `email`, `name`
- 동작: `create_or_get_oauth_user` 재사용 + JWT 발급
- 보호: 환경변수 플래그(`ENABLE_LOADTEST_AUTH_MOCK=true`) + 내부망/IP 제한

1. 대안: 사전 시드 + 토큰 발급 스크립트

- DB에 테스트 사용자 대량 생성 후 JWT 사전 발급
- 단점: 실제 OAuth 진입 트래픽이 빠져 가입 병목을 못 본다.

1. 비권장: 실제 Google OAuth 연동으로 대량 트래픽

- 외부 의존성과 rate limit 때문에 부하 실험 재현성이 떨어진다.

## 6. 테스트 스크립트 구조 (권장)

### 6.1 파일 분리

- `scripts/loadtest/README.md`: 실행 절차/파라미터
- `scripts/loadtest/locustfile.py`: 사용자 시나리오 엔트리
- `scripts/loadtest/lib/auth_provider.py`: OAuth mock 또는 사전 토큰 공급
- `scripts/loadtest/lib/scenario_user.py`: 일반 사용자 흐름
- `scripts/loadtest/lib/scenario_manager.py`: 리더/매니저 흐름
- `scripts/loadtest/lib/state_store.py`: user/club/meeting/participant 캐시
- `scripts/loadtest/report_parser.py`: 결과 리포트 요약
- `scripts/loadtest/run_headless.sh`: headless 실행
- `scripts/loadtest/requirements.txt`: 로드테스트 의존성

### 6.2 시나리오 핵심

- 일반 사용자
  - 온보딩(가입→약관→프로필)
  - 클럽 검색/가입 신청
  - 모임 검색/참가
  - 종료 후 본인 점수 입력
- 운영자 사용자(리더/매니저)
  - 클럽 생성 또는 가입 승인
  - 모임 생성
  - 모집 마감/팀 편성/진행 제어
  - 정산 생성/확정

## 7. 병목 식별을 위한 계측/프로파일링

### 7.1 필수 지표

- API: RPS, p50/p95/p99, 에러율(4xx/5xx 분리)
- DB: 쿼리 수, 평균/상위 쿼리 시간, 커넥션 풀 대기
- 시스템: CPU, 메모리, 디스크 I/O, 네트워크
- 워크플로우: 단계별 성공률(가입/약관/프로필/클럽/모임/정산/점수)

### 7.2 `lprof`(line_profiler) 적용 대상

- 팀 편성: `utils/team_formation.py`의 편성 함수
- 워크플로우: `auto_form_teams`, `confirm_team_formation`
- 정산: `create_rounding_settlement`, `create_social_settlement`
- 모임 목록 조회(특히 private 필터 포함): `get_rounding_meetings`, `get_meetings`

### 7.3 운영 프로파일러 병행

- 샘플링 기반(`py-spy`/`scalene`)으로 실부하 중 핫스팟 추적
- `lprof`는 리퀘스트 전체보다 핵심 함수 재현 스크립트에 집중 적용

## 8. 누락 없이 스크립트/문서 작성하려면 추가해야 할 항목

1. 테스트 데이터 수명주기 정의

- run_id 단위 생성/정리 정책
- 실패 중단 시 cleanup 재실행 정책

1. 권한 전이 규칙 고정

- 리더/매니저 계정 풀 별도 운영
- 가입 승인 지연 시간(즉시/지연/배치) 시뮬레이션

1. 오류 예산/종료 조건

- 예: 5xx > 1% 5분 지속 시 중단
- p95 목표 초과 기준

1. 재현성

- 랜덤 시드 고정 옵션
- 동일 파라미터 세트 저장(`run config`)

1. 리포트 표준화

- 빌드 버전/브랜치/DB 스냅샷/파라미터/N/X 포함
- 시나리오별 성공률과 느린 엔드포인트 TOP N

1. 보안 가드

- OAuth mock 엔드포인트는 운영 차단
- 테스트 계정 prefix 외 사용자 데이터 조작 금지

## 9. 바로 착수 가능한 1차 실행안

1. 서버 환경변수 설정  
   `ENABLE_LOADTEST_AUTH_MOCK=true`, `LOADTEST_AUTH_MOCK_ALLOWED_IPS=...`
2. `scripts/loadtest/` 실행  
   `scripts/loadtest/run_headless.sh` 또는 `locust -f scripts/loadtest/locustfile.py`
3. 테스트 시작 시 내부 bootstrap 자동 수행  
   `/api/v1/internal/loadtest/bootstrap`로 약관/지역 최소 시드 보장
4. 온보딩 + 클럽 + 모임 + 워크플로우 + 정산 + 점수 입력 시나리오 실행
5. CSV 결과 파싱  
   `python scripts/loadtest/report_parser.py <stats.csv>`
6. `lprof`/샘플러로 핫스팟 정밀 분석

## 10. 구현 시 주의 (현재 코드만으로 확정 불가 항목)

- `settlement/rounding`, `settlement/social`의 상세 body 조합은 dict 기반으로 유연하게 처리된다.
- 따라서 로드 테스트 스크립트 구현 시, payload는 실제 OpenAPI/실행 로그를 기준으로 고정하고 추측 필드 주입은 금지한다.
