# 라우터 파일 구조 정리 문서

## 📋 개요

백엔드 라우터 파일들을 기능별로 통합하여 구조를 정리했습니다. 모든 엔드포인트 경로는 기존과 동일하게 유지되어 프론트엔드 코드 변경 없이 동작합니다.

## 📁 디렉토리 구조

```
routers/
├── meetings/              # 모임 관련 API (통합됨)
│   ├── __init__.py
│   ├── base.py            # 기본 CRUD
│   ├── participants.py    # 참가자 관리
│   ├── workflow.py        # 워크플로우
│   ├── settlement.py      # 정산 관리
│   ├── teams.py           # 팀 관리
│   ├── scores.py          # 점수 관리
│   ├── expenses.py        # 비용 관리
│   └── types/
│       ├── rounds.py      # 라운딩 전용
│       └── socials.py    # 소셜 모임 전용
│
├── clubs/                 # 클럽 관련 API (통합됨)
│   ├── __init__.py
│   ├── base.py            # 기본 CRUD
│   ├── notices.py         # 공지사항
│   └── regulations.py    # 규정
│
├── auth.py                # 인증
├── oauth.py               # OAuth
├── users.py               # 사용자 관리
├── admin.py               # 관리자
├── faq.py                 # FAQ
├── inquiries.py           # 문의
├── notices.py             # 공지사항
├── terms.py               # 약관
├── personal_records.py    # 개인 기록
├── user_schedules.py      # 사용자 일정
├── plans.py               # 요금제
├── payments.py            # 결제
├── payment_methods.py     # 결제 수단
├── subscriptions.py       # 구독
└── upload.py              # 업로드
```

## 🔄 변경 사항

### 1. Meetings 관련 파일 통합

#### 이동된 파일들
- `meetings.py` → `meetings/base.py`
- `meeting_participants.py` → `meetings/participants.py`
- `meeting_workflow.py` → `meetings/workflow.py`
- `meeting_settlement.py` → `meetings/settlement.py`
- `rounds.py` → `meetings/types/rounds.py`
- `socials.py` → `meetings/types/socials.py`
- `teams.py` → `meetings/teams.py`
- `scores.py` → `meetings/scores.py`
- `expenses.py` → `meetings/expenses.py`

#### 삭제된 파일들
- `meeting_participants.py` (중복)
- `meeting_workflow.py` (중복)
- `meeting_settlement.py` (중복)
- `meetings.py` (중복)
- `rounds.py` (중복)
- `socials.py` (중복)
- `teams.py` (중복)
- `scores.py` (중복)
- `expenses.py` (중복)

#### 라우터 구조

**`meetings/__init__.py`**
```python
from .base import router as base_router
from .participants import router as participants_router
from .workflow import router as workflow_router
from .settlement import router as settlement_router
from .teams import router as teams_router
from .scores import router as scores_router
from .expenses import router as expenses_router
from .types.rounds import router as rounds_router
from .types.socials import router as socials_router
```

#### 엔드포인트 경로 (변경 없음)

**기본 모임 관리** (`base.py`)
- `GET /api/v1/meetings` - 모임 목록 조회
- `GET /api/v1/meetings/{meeting_id}` - 모임 상세 조회
- `POST /api/v1/meetings` - 모임 생성
- `PUT /api/v1/meetings/{meeting_id}` - 모임 수정
- `DELETE /api/v1/meetings/{meeting_id}` - 모임 삭제
- `POST /api/v1/meetings/{meeting_id}/cancel` - 모임 취소
- `GET /api/v1/meetings/my` - 내 모임 목록 조회

**참가자 관리** (`participants.py`)
- `GET /api/v1/meetings/{meeting_id}/participants` - 참가자 목록 조회
- `POST /api/v1/meetings/{meeting_id}/participants` - 참가자 추가
- `PUT /api/v1/meetings/{meeting_id}/participants/{participant_id}/status` - 참가자 상태 변경
- `PUT /api/v1/meetings/{meeting_id}/participants/{participant_id}/role` - 참가자 역할 변경
- `DELETE /api/v1/meetings/{meeting_id}/participants/{participant_id}` - 참가자 제거

**워크플로우** (`workflow.py`)
- `POST /api/v1/meetings/{meeting_id}/apply` - 모임 신청
- `POST /api/v1/meetings/{meeting_id}/participants/{participant_id}/approve` - 참가자 승인
- `POST /api/v1/meetings/{meeting_id}/participants/{participant_id}/reject` - 참가자 거부
- `POST /api/v1/meetings/{meeting_id}/close-application` - 신청 마감
- `GET /api/v1/meetings/{meeting_id}/application-status` - 신청 상태 조회
- `POST /api/v1/meetings/{meeting_id}/start-team-formation` - 팀 편성 시작
- `POST /api/v1/meetings/{meeting_id}/teams/confirm` - 팀 편성 확정
- `POST /api/v1/meetings/{meeting_id}/start-rounding` - 라운딩 시작
- `POST /api/v1/meetings/{meeting_id}/complete-rounding` - 라운딩 종료
- `POST /api/v1/meetings/{meeting_id}/complete` - 모임 완료

**정산 관리** (`settlement.py`)
- `GET /api/v1/meetings/{meeting_id}/settlement` - 정산 정보 조회
- `POST /api/v1/meetings/{meeting_id}/settlement/calculate` - 정산 계산
- `POST /api/v1/meetings/{meeting_id}/settlement/confirm` - 정산 확정

**팀 관리** (`teams.py`)
- `GET /api/v1/meetings/{meeting_id}/teams` - 팀 목록 조회
- `POST /api/v1/meetings/{meeting_id}/teams` - 팀 생성
- `GET /api/v1/meetings/{meeting_id}/teams/{team_id}` - 팀 상세 조회
- `PUT /api/v1/meetings/{meeting_id}/teams/{team_id}` - 팀 수정
- `DELETE /api/v1/meetings/{meeting_id}/teams/{team_id}` - 팀 삭제
- `POST /api/v1/meetings/{meeting_id}/teams/auto-formation` - 자동 팀 편성

**점수 관리** (`scores.py`)
- `POST /api/v1/scores` - 스코어 등록
- `GET /api/v1/scores` - 스코어 목록 조회
- `GET /api/v1/scores/{score_id}` - 스코어 상세 조회
- `PUT /api/v1/scores/{score_id}` - 스코어 수정
- `DELETE /api/v1/scores/{score_id}` - 스코어 삭제
- `GET /api/v1/scores/stats/{participant_id}` - 스코어 통계 조회

**비용 관리** (`expenses.py`)
- `GET /api/v1/meetings/{meeting_id}/expenses` - 비용 목록 조회
- `POST /api/v1/meetings/{meeting_id}/expenses` - 비용 생성
- `GET /api/v1/meetings/{meeting_id}/expenses/{expense_id}` - 비용 상세 조회
- `PUT /api/v1/meetings/{meeting_id}/expenses/{expense_id}` - 비용 수정
- `DELETE /api/v1/meetings/{meeting_id}/expenses/{expense_id}` - 비용 삭제
- `GET /api/v1/meetings/{meeting_id}/expenses/{expense_id}/participants` - 비용 참가자 조회
- `PUT /api/v1/meetings/{meeting_id}/expenses/{expense_id}/participants/{participant_id}` - 비용 참가자 수정

**라운딩 전용** (`types/rounds.py`)
- `GET /api/v1/rounds` - 라운딩 목록 조회
- `GET /api/v1/rounds/{meeting_id}` - 라운딩 상세 조회
- `POST /api/v1/rounds` - 라운딩 생성
- `PUT /api/v1/rounds/{meeting_id}` - 라운딩 수정
- `GET /api/v1/rounds/{meeting_id}/participants` - 라운딩 참가자 조회
- `GET /api/v1/rounds/{meeting_id}/teams` - 라운딩 팀 조회

**소셜 모임 전용** (`types/socials.py`)
- `GET /api/v1/socials` - 소셜 모임 목록 조회
- `GET /api/v1/socials/{meeting_id}` - 소셜 모임 상세 조회
- `POST /api/v1/socials` - 소셜 모임 생성
- `PUT /api/v1/socials/{meeting_id}` - 소셜 모임 수정

### 2. Clubs 관련 파일 통합

#### 이동된 파일들
- `clubs.py` → `clubs/base.py`
- `clubs_notices.py` → `clubs/notices.py`
- `club_regulations.py` → `clubs/regulations.py`

#### 삭제된 파일들
- `clubs.py` (중복)
- `clubs_notices.py` (중복)
- `club_regulations.py` (중복)

#### 라우터 구조

**`clubs/__init__.py`**
```python
from .base import router as base_router
from .notices import router as notices_router
from .regulations import router as regulations_router
```

#### 엔드포인트 경로 (변경 없음)

**기본 클럽 관리** (`base.py`)
- `POST /api/v1/clubs` - 클럽 생성
- `GET /api/v1/clubs` - 클럽 목록 조회
- `GET /api/v1/clubs/my` - 내 클럽 목록 조회
- `GET /api/v1/clubs/{club_id}` - 클럽 상세 조회
- `PUT /api/v1/clubs/{club_id}` - 클럽 수정
- `PUT /api/v1/clubs/{club_id}/approve` - 클럽 승인
- `PUT /api/v1/clubs/{club_id}/reject` - 클럽 거부
- `GET /api/v1/clubs/{club_id}/members` - 클럽 멤버 목록 조회
- `POST /api/v1/clubs/{club_id}/join` - 클럽 가입 신청
- `POST /api/v1/clubs/{club_id}/members` - 클럽 멤버 추가
- `POST /api/v1/clubs/{club_id}/members/{user_id}/approve` - 멤버 승인
- `POST /api/v1/clubs/{club_id}/members/{user_id}/reject` - 멤버 거부
- `PUT /api/v1/clubs/{club_id}/members/{user_id}/role` - 멤버 역할 변경
- `POST /api/v1/clubs/register` - 클럽 가입 신청

**클럽 공지사항** (`notices.py`)
- `GET /api/v1/clubs/{club_id}/notices` - 공지사항 목록 조회
- `POST /api/v1/clubs/{club_id}/notices` - 공지사항 생성
- `GET /api/v1/clubs/{club_id}/notices/{notice_id}` - 공지사항 상세 조회
- `PUT /api/v1/clubs/{club_id}/notices/{notice_id}` - 공지사항 수정
- `DELETE /api/v1/clubs/{club_id}/notices/{notice_id}` - 공지사항 삭제

**클럽 규정** (`regulations.py`)
- `POST /api/v1/clubs/{club_id}/regulations/categories` - 규정 카테고리 생성
- `GET /api/v1/clubs/{club_id}/regulations/categories` - 규정 카테고리 목록 조회
- `PUT /api/v1/clubs/{club_id}/regulations/categories/{category_id}` - 규정 카테고리 수정
- `DELETE /api/v1/clubs/{club_id}/regulations/categories/{category_id}` - 규정 카테고리 삭제
- `POST /api/v1/clubs/{club_id}/regulations/categories/{category_id}/articles` - 규정 조항 생성
- `GET /api/v1/clubs/{club_id}/regulations/categories/{category_id}/articles` - 규정 조항 목록 조회
- `PUT /api/v1/clubs/{club_id}/regulations/categories/{category_id}/articles/{article_id}` - 규정 조항 수정
- `DELETE /api/v1/clubs/{club_id}/regulations/categories/{category_id}/articles/{article_id}` - 규정 조항 삭제
- `GET /api/v1/clubs/{club_id}/regulations/versions` - 규정 버전 목록 조회
- `GET /api/v1/clubs/{club_id}/regulations` - 전체 규정 조회

### 3. main.py 수정 사항

#### Import 변경

**이전:**
```python
from routers import clubs, clubs_notices, club_regulations, auth, personal_records, user_schedules, teams, plans, payments, payment_methods, subscriptions, users, terms, notices, inquiries, expenses, scores, upload, admin, oauth, faq
from routers.meetings import base_router, participants_router, workflow_router, settlement_router, teams_router, scores_router, expenses_router, rounds_router, socials_router
```

**이후:**
```python
from routers import auth, personal_records, user_schedules, plans, payments, payment_methods, subscriptions, users, terms, notices, inquiries, upload, admin, oauth, faq
from routers.clubs import base_router as clubs_router, notices_router as clubs_notices_router, regulations_router as club_regulations_router
from routers.meetings import base_router, participants_router, workflow_router, settlement_router, teams_router, scores_router, expenses_router, rounds_router, socials_router
```

#### 라우터 등록 변경

**이전:**
```python
app.include_router(clubs_notices.router, prefix="/api/v1")
app.include_router(clubs.router, prefix="/api/v1")
app.include_router(club_regulations.router, prefix="/api/v1")
```

**이후:**
```python
# 클럽 관련 라우터 - 기능별로 통합됨
app.include_router(clubs_router, prefix="/api/v1")              # /clubs - 기본 CRUD
app.include_router(clubs_notices_router, prefix="/api/v1")      # /clubs - 공지사항
app.include_router(club_regulations_router, prefix="/api/v1")    # /clubs - 규정
```

## ✅ 정리 완료 항목

1. ✅ Meetings 관련 파일 통합 및 중복 제거
2. ✅ Clubs 관련 파일 통합 및 중복 제거
3. ✅ main.py import 경로 수정
4. ✅ main.py 라우터 등록 경로 수정
5. ✅ 모든 엔드포인트 경로 유지 (프론트엔드 호환성 보장)

## 📝 주의사항

### 엔드포인트 경로 유지

모든 엔드포인트 경로는 기존과 동일하게 유지되었습니다. 따라서:
- ✅ 프론트엔드 코드 변경 불필요
- ✅ API 클라이언트 코드 변경 불필요
- ✅ 기존 API 문서와 호환

### 라우터 Prefix

각 라우터의 prefix는 다음과 같이 설정되어 있습니다:

**Meetings 관련:**
- `base.py`: `/meetings`
- `participants.py`: `/meetings`
- `workflow.py`: `/meetings`
- `settlement.py`: `/meetings`
- `teams.py`: `/meetings`
- `scores.py`: `/scores` (독립)
- `expenses.py`: `/meetings`
- `types/rounds.py`: `/rounds`
- `types/socials.py`: `/socials`

**Clubs 관련:**
- `base.py`: `/clubs`
- `notices.py`: `/clubs`
- `regulations.py`: `/clubs`

## 🔍 파일 구조 상세

### Meetings 폴더

```
meetings/
├── __init__.py           # 모든 라우터 export
├── base.py               # 기본 CRUD (31개 엔드포인트)
├── participants.py       # 참가자 관리
├── workflow.py           # 워크플로우 관리
├── settlement.py         # 정산 관리
├── teams.py              # 팀 관리 (6개 엔드포인트)
├── scores.py             # 점수 관리 (6개 엔드포인트)
├── expenses.py           # 비용 관리 (7개 엔드포인트)
└── types/
    ├── rounds.py         # 라운딩 전용
    └── socials.py        # 소셜 모임 전용
```

### Clubs 폴더

```
clubs/
├── __init__.py           # 모든 라우터 export
├── base.py               # 기본 CRUD (31개 엔드포인트)
├── notices.py            # 공지사항 (5개 엔드포인트)
└── regulations.py        # 규정 (24개 엔드포인트)
```

## 🎯 정리 효과

1. **코드 구조 개선**: 관련 기능을 한 폴더에 모아 관리 용이
2. **유지보수성 향상**: 기능별로 파일이 분리되어 수정 범위 명확
3. **가독성 향상**: 파일 구조가 직관적이고 이해하기 쉬움
4. **확장성**: 새로운 기능 추가 시 적절한 위치에 파일 추가 가능

## 📚 참고사항

- 모든 백업 파일(`.backup`, `.full`)은 보존되어 있습니다
- 엔드포인트 경로는 변경되지 않았으므로 기존 API 클라이언트와 호환됩니다
- 새로운 기능 추가 시 해당 폴더의 `__init__.py`에 라우터를 추가해야 합니다

