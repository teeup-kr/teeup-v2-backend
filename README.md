# TeeupLink Backend

골프 모임 관리 플랫폼의 백엔드 API 서버입니다.

## 기술 스택

- **Python 3.10+**
- **FastAPI** - 웹 프레임워크
- **SQLAlchemy** - ORM
- **PyMySQL** - MySQL 드라이버
- **Pydantic** - 데이터 검증
- **Uvicorn** - ASGI 서버

## 설치 및 설정

### 1. 의존성 설치

```bash
pip install -r requirements.txt
```

### 2. 환경변수 설정

프로젝트 루트의 `.env` 파일을 설정하세요:

```env
# Database Configuration
DATABASE_HOST=localhost
DATABASE_PORT=3306
DATABASE_NAME=teeuprun
DATABASE_USER=your_user_here
DATABASE_PASSWORD=your_password_here

# JWT Secret Key
JWT_SECRET_KEY=your_jwt_secret_key_here

# Environment
ENVIRONMENT=development
```

### 3. MySQL 데이터베이스 설정

MySQL 서버가 실행 중인지 확인하고, 데이터베이스와 테이블을 생성합니다:

```bash
# 데이터베이스 초기화 (테이블 생성)
python scripts/init_db.py

# 또는 유틸리티 스크립트 사용
python utils/create_simple_users.py  # 테스트 사용자 생성
python utils/check_user.py           # 사용자 확인
```

### 4. 서버 실행

```bash
# 개발 서버 실행
python main.py

# 또는 uvicorn으로 직접 실행
uvicorn main:app --host 0.0.0.0 --port 8002 --reload
```

## API 엔드포인트

### 기본 엔드포인트
- `GET /` - 서버 상태 확인
- `GET /health` - 헬스 체크
- `GET /health/db` - 데이터베이스 연결 상태 확인
- `GET /docs` - Swagger UI (FastAPI 자동 생성)

### 구현된 API (52개 엔드포인트)

#### 인증 API (3개)
- `POST /api/v1/auth/login` - 로그인
- `POST /api/v1/auth/register` - 회원가입
- `GET /api/v1/auth/me` - 현재 사용자 정보

#### 클럽 관리 API (15개)
- `GET /api/v1/clubs` - 클럽 목록 조회
- `POST /api/v1/clubs` - 클럽 생성
- `GET /api/v1/clubs/{club_id}` - 클럽 상세 조회
- `PUT /api/v1/clubs/{club_id}` - 클럽 정보 수정
- `PUT /api/v1/clubs/{club_id}/approve` - 클럽 승인
- `POST /api/v1/clubs/{club_id}/join` - 클럽 가입
- `GET /api/v1/clubs/{club_id}/members` - 멤버 목록
- `PUT /api/v1/clubs/{club_id}/members/{user_id}/role` - 멤버 역할 변경
- `POST /api/v1/clubs/register` - 클럽 등록 신청
- `GET /api/v1/clubs/applications/my` - 클럽 신청내역 조회
- `DELETE /api/v1/clubs/{club_id}/members/{user_id}` - 회원 내보내기
- `DELETE /api/v1/clubs/{club_id}/leave` - 클럽 탈퇴
- `GET /api/v1/clubs/{club_id}/regular-fee` - 정기 회비 조회
- `PUT /api/v1/clubs/{club_id}/regular-fee` - 정기 회비 설정/수정

#### 공지사항 API (5개)
- `GET /api/v1/clubs/{club_id}/notices` - 클럽별 공지사항 조회
- `POST /api/v1/clubs/{club_id}/notices` - 클럽별 공지사항 작성
- `GET /api/v1/clubs/{club_id}/notices/{notice_id}` - 클럽별 공지사항 상세
- `PUT /api/v1/clubs/{club_id}/notices/{notice_id}` - 클럽별 공지사항 수정
- `DELETE /api/v1/clubs/{club_id}/notices/{notice_id}` - 클럽별 공지사항 삭제

#### 약관 관리 API (9개)
- `POST /api/v1/clubs/{club_id}/regulations/categories` - 규정 카테고리 생성
- `GET /api/v1/clubs/{club_id}/regulations/categories` - 규정 카테고리 목록 조회
- `PUT /api/v1/clubs/{club_id}/regulations/categories/{category_id}` - 규정 카테고리 수정
- `DELETE /api/v1/clubs/{club_id}/regulations/categories/{category_id}` - 규정 카테고리 삭제
- `POST /api/v1/clubs/{club_id}/regulations/categories/{category_id}/articles` - 규정 항목 생성
- `GET /api/v1/clubs/{club_id}/regulations/categories/{category_id}/articles` - 규정 항목 목록 조회
- `PUT /api/v1/clubs/{club_id}/regulations/categories/{category_id}/articles/{article_id}` - 규정 항목 수정
- `DELETE /api/v1/clubs/{club_id}/regulations/categories/{category_id}/articles/{article_id}` - 규정 항목 삭제
- `GET /api/v1/clubs/{club_id}/regulations` - 클럽별 약관 조회

#### 모임 관리 API (9개)
- `POST /api/v1/meetings/` - 모임 생성
- `GET /api/v1/meetings/` - 모임 목록 조회
- `GET /api/v1/meetings/{meeting_id}` - 모임 상세 조회
- `PUT /api/v1/meetings/{meeting_id}` - 모임 정보 수정
- `POST /api/v1/meetings/{meeting_id}/join` - 모임 참가
- `DELETE /api/v1/meetings/{meeting_id}/leave` - 모임 탈퇴
- `POST /api/v1/meetings/{meeting_id}/cancel` - 모임 취소
- `DELETE /api/v1/meetings/{meeting_id}` - 모임 삭제
- `GET /api/v1/meetings/{meeting_id}/records` - 모임 참가자들의 기록 조회

#### 기록 관리 API (6개)
- `POST /api/v1/personal-records/` - 개인 기록 생성
- `GET /api/v1/personal-records/` - 개인 기록 목록 조회
- `GET /api/v1/personal-records/{record_id}` - 개인 기록 상세 조회
- `PUT /api/v1/personal-records/{record_id}` - 개인 기록 수정
- `DELETE /api/v1/personal-records/{record_id}` - 개인 기록 삭제
- `GET /api/v1/personal-records/stats/{user_id}` - 개인 기록 통계 조회

#### 사용자 개인 일정 관리 API (5개)
- `POST /api/v1/user-schedules/` - 개인 일정 생성
- `GET /api/v1/user-schedules/` - 개인 일정 목록 조회
- `GET /api/v1/user-schedules/{schedule_id}` - 개인 일정 상세 조회
- `PUT /api/v1/user-schedules/{schedule_id}` - 개인 일정 수정
- `DELETE /api/v1/user-schedules/{schedule_id}` - 개인 일정 삭제

## 데이터베이스 스키마

Prisma 스키마를 기반으로 MySQL 테이블이 생성됩니다 (총 25개 테이블):

### 핵심 테이블
- **users** - 사용자 정보
- **clubs** - 골프 모임 정보
- **club_memberships** - 모임 멤버십
- **club_applications** - 클럽 등록 신청
- **club_notices** - 클럽별 공지사항
- **regulation_categories** - 규정 카테고리
- **regulation_articles** - 규정 항목

### 구현된 테이블
- **meetings** - 모임 일정 ✅
- **meeting_participants** - 모임 참여자 ✅
- **teams** - 팀 구성 ✅
- **scores** - 점수 기록 ✅
- **personal_records** - 개인 기록 ✅
- **user_schedules** - 사용자 개인 일정 ✅
- **events** - 이벤트 ✅
- **event_participants** - 이벤트 참여자 ✅

### 향후 구현 예정
- **inquiries** - 문의사항
- 기타 관련 테이블들...

## 개발 가이드

### 새로운 API 엔드포인트 추가

1. `main.py`에 새로운 라우터 추가
2. 필요시 새로운 모델 파일 생성
3. 데이터베이스 모델은 SQLAlchemy 사용

### 데이터베이스 마이그레이션

현재는 `init_db.py`를 통해 테이블을 생성합니다. 
향후 Alembic을 사용한 마이그레이션 시스템으로 전환할 수 있습니다.

## 문제 해결

### 데이터베이스 연결 오류

1. MySQL 서버가 실행 중인지 확인
2. `.env` 파일의 데이터베이스 설정 확인
3. 방화벽 설정 확인 (포트 3306)

### 테이블 생성 오류

1. 데이터베이스 사용자 권한 확인
2. `teeup_db` 데이터베이스가 존재하는지 확인
3. `init_db.py`를 다시 실행
