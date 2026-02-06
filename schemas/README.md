# 스키마 파일 구조 정리 문서

## 📋 개요

백엔드 스키마 파일(`schemas.py`)을 기능별로 분리하여 구조를 정리했습니다. 모든 스키마는 `schemas/__init__.py`를 통해 export되어 기존 import 경로와 완전히 호환됩니다.

## 📁 디렉토리 구조

```
schemas/
├── __init__.py              # 모든 스키마 export (기존 import 경로 호환)
├── enums.py                 # 모든 Enum 정의
├── common.py                # 공통 스키마 (MessageResponse, PaginatedResponse)
├── club.py                  # 클럽 관련 스키마
├── meeting.py               # 모임 관련 스키마
├── team.py                  # 팀 관련 스키마
├── user.py                  # 사용자 관련 스키마
├── payment.py               # 결제 관련 스키마 (플랜, 결제 수단, 구독, 결제 통합)
├── terms.py                 # 약관 관련 스키마
├── notice.py                # 공지사항 관련 스키마
├── inquiry.py               # 문의 관련 스키마
├── expense.py               # 비용 정산 관련 스키마
├── score.py                 # 스코어 관련 스키마
├── oauth.py                 # OAuth 관련 스키마
├── faq.py                   # FAQ 관련 스키마
├── admin.py                 # 백오피스 관련 스키마
├── personal_record.py       # 개인 기록 관련 스키마
└── user_schedule.py         # 사용자 일정 관련 스키마
```

## 🔄 변경 사항

### 1. 파일 분리

**원본 파일:**
- `schemas.py` (1,485줄) → `schemas.py.backup`으로 백업 후 삭제됨
- 모든 스키마가 `schemas/` 디렉토리로 이동 완료

**분리된 파일들:**
- `schemas/enums.py` - 모든 Enum 클래스 (25개)
- `schemas/common.py` - 공통 응답 스키마 (2개)
- `schemas/club.py` - 클럽 관련 스키마 (25개)
- `schemas/meeting.py` - 모임 관련 스키마 (5개)
- `schemas/team.py` - 팀 관련 스키마 (9개)
- `schemas/user.py` - 사용자 관련 스키마 (6개)
- `schemas/payment.py` - 결제 관련 스키마 (10개)
- `schemas/terms.py` - 약관 관련 스키마 (6개)
- `schemas/notice.py` - 공지사항 관련 스키마 (4개)
- `schemas/inquiry.py` - 문의 관련 스키마 (8개)
- `schemas/expense.py` - 비용 정산 관련 스키마 (6개)
- `schemas/score.py` - 스코어 관련 스키마 (7개)
- `schemas/oauth.py` - OAuth 관련 스키마 (3개)
- `schemas/faq.py` - FAQ 관련 스키마 (9개)
- `schemas/admin.py` - 백오피스 관련 스키마 (5개)
- `schemas/personal_record.py` - 개인 기록 관련 스키마 (4개)
- `schemas/user_schedule.py` - 사용자 일정 관련 스키마 (3개)

### 2. 통합된 파일

**결제 관련 스키마 통합:**
- `payment.py`에 다음 스키마들이 통합됨:
  - 플랜 관련 (PlanCreate, PlanUpdate, PlanResponse)
  - 결제 수단 관련 (PaymentMethodCreate, PaymentMethodUpdate, PaymentMethodResponse)
  - 구독 관련 (SubscriptionCreate, SubscriptionUpdate, SubscriptionResponse)
  - 결제 관련 (PaymentResponse)

### 3. Import 경로 호환성

**기존 코드:**
```python
from schemas import UserCreate, UserUpdate, UserResponse
from schemas import ClubCreate, ClubResponse
from schemas import MeetingType, MeetingStatus
```

**변경 후:**
- 기존 import 경로가 그대로 작동합니다
- `schemas/__init__.py`에서 모든 스키마를 export하여 호환성 유지

## 📝 각 파일별 상세 내용

### `enums.py`
모든 Enum 클래스 정의:
- `ClubType`, `ClubStatus`, `ClubRole`, `BillingCycle`
- `MeetingType`, `MeetingSubtype`, `SettlementMethod`, `SocialSettlementMethod`
- `MeetingStatus`
- `RegulationStatus`, `MembershipStatus`
- `TeamFormationMode`, `TeamStatus`
- `NotificationType`, `NotificationStatus`
- `PlanType`, `PaymentStatus`, `PaymentMethod`, `PaymentMethodStatus`, `SubscriptionStatus`
- `TermsType`, `UserRole`, `UserStatus`
- `NoticeType`, `InquiryType`, `InquiryStatus`, `Provider`

### `common.py`
공통 응답 스키마:
- `MessageResponse` - 기본 메시지 응답
- `PaginatedResponse` - 페이지네이션 응답 (Generic)

### `club.py`
클럽 관련 스키마 (25개):
- 클럽 기본: `ClubCreate`, `ClubUpdate`, `ClubResponse`
- 클럽 멤버: `ClubMembersResponse`, `ClubMembershipResponse`, `ClubMemberAddRequest`, `ClubMemberRoleUpdateRequest`, `MemberNoteUpdate`, `MemberNoteResponse`
- 클럽 신청: `ClubApplicationCreate`, `ClubApplicationResponse`, `ClubApplicationUpdate`, `ClubApplicationCreateResponse`
- 회비: `RegularFeeUpdate`, `RegularFeeResponse`, `ClubFeeCreate`, `ClubFeeUpdate`, `ClubFeeResponse`
- 공지사항: `ClubNoticeCreate`, `ClubNoticeUpdate`, `ClubNoticeResponse`
- 규정: `RegulationVersionCreate`, `RegulationVersionUpdate`, `RegulationVersionResponse`, `RegulationVersionListResponse`, `RegulationCategoryCreate`, `RegulationCategoryUpdate`, `RegulationCategoryResponse`, `RegulationArticleCreate`, `RegulationArticleUpdate`, `RegulationArticleResponse`, `RegulationCategoryWithArticles`, `ClubRegulationsResponse`, `ClubRegulationResponse`, `ClubRegulationCreate`, `ClubRegulationUpdate`

### `meeting.py`
모임 관련 스키마 (5개):
- `RoundingMeetingCreate` - 라운딩 모임 생성
- `MeetingUpdate` - 모임 수정
- `MeetingResponse` - 모임 응답
- `MeetingParticipantResponse` - 모임 참가자 응답
- `SocialMeetingCreate` - 소셜 모임 생성

### `team.py`
팀 관련 스키마 (9개):
- `TeamCreate`, `TeamUpdate`, `TeamResponse` - 팀 기본
- `TeamMemberResponse` - 팀 멤버 응답
- `GuestCreate`, `GuestUpdate`, `GuestResponse` - 게스트 관리
- `TeamFormationRequest`, `TeamFormationResponse` - 팀 편성

**순환 참조 처리:**
- `TeamFormationResponse`에서 `MeetingParticipantResponse`를 문자열 타입으로 지정하여 순환 참조 방지

### `user.py`
사용자 관련 스키마 (6개):
- `UserCreate`, `UserUpdate`, `UserResponse` - 사용자 기본
- `NotificationResponse` - 알림 응답
- `NotificationSettingsResponse`, `NotificationSettingsUpdate` - 알림 설정

### `payment.py`
결제 관련 스키마 (10개):
- 플랜: `PlanCreate`, `PlanUpdate`, `PlanResponse`
- 결제 수단: `PaymentMethodCreate`, `PaymentMethodUpdate`, `PaymentMethodResponse`
- 구독: `SubscriptionCreate`, `SubscriptionUpdate`, `SubscriptionResponse`
- 결제: `PaymentResponse`

### `terms.py`
약관 관련 스키마 (6개):
- `TermsCreate`, `TermsUpdate`, `TermsResponse`, `TermsListResponse`
- `TermsAgreementCreate`, `TermsAgreementResponse`

### `notice.py`
공지사항 관련 스키마 (4개):
- `NoticeCreate`, `NoticeUpdate`, `NoticeResponse`, `NoticeListResponse`

### `inquiry.py`
문의 관련 스키마 (8개):
- `InquiryCreate`, `InquiryUpdate`, `InquiryResponse`, `InquiryListResponse`
- `InquiryResponseCreate`, `InquiryResponseUpdate`, `InquiryResponseResponse`, `InquiryDetailResponse`

### `expense.py`
비용 정산 관련 스키마 (6개):
- `ExpenseCreate`, `ExpenseUpdate`, `ExpenseResponse`, `ExpenseListResponse`
- `ExpenseParticipantResponse`, `ExpenseParticipantUpdate`

### `score.py`
스코어 관련 스키마 (7개):
- `ScoreCreate`, `ScoreUpdate`, `ScoreResponse`
- `SimpleScoreCreate`, `SimpleScoreResponse`, `ScoreListResponse`, `ScoreStats`

### `oauth.py`
OAuth 관련 스키마 (3개):
- `OAuthLoginRequest`, `OAuthCallbackRequest`, `OAuthUserInfo`

### `faq.py`
FAQ 관련 스키마 (9개):
- `FAQCategoryBase`, `FAQCategoryCreate`, `FAQCategoryUpdate`, `FAQCategoryResponse`
- `FAQBase`, `FAQCreate`, `FAQUpdate`, `FAQResponse`, `FAQPageResponse`

### `admin.py`
백오피스 관련 스키마 (5개):
- `UserMeetingItem`, `UserMeetingsResponse`
- `HandicapHistoryItem`, `HandicapInfo`, `UserHandicapHistoryResponse`

### `personal_record.py`
개인 기록 관련 스키마 (4개):
- `PersonalRecordCreate`, `PersonalRecordUpdate`, `PersonalRecordResponse`, `PersonalRecordStats`

### `user_schedule.py`
사용자 일정 관련 스키마 (3개):
- `UserScheduleCreate`, `UserScheduleUpdate`, `UserScheduleResponse`

## ✅ 정리 완료 항목

- [x] `schemas.py` 백업 (`schemas.py.backup`)
- [x] `schemas/` 디렉토리 생성
- [x] Enum 정의 분리 (`enums.py`)
- [x] 공통 스키마 분리 (`common.py`)
- [x] 클럽 관련 스키마 분리 (`club.py`)
- [x] 모임 관련 스키마 분리 (`meeting.py`)
- [x] 팀 관련 스키마 분리 (`team.py`)
- [x] 사용자 관련 스키마 분리 (`user.py`)
- [x] 결제 관련 스키마 통합 및 분리 (`payment.py`)
- [x] 약관 관련 스키마 분리 (`terms.py`)
- [x] 공지사항 관련 스키마 분리 (`notice.py`)
- [x] 문의 관련 스키마 분리 (`inquiry.py`)
- [x] 비용 정산 관련 스키마 분리 (`expense.py`)
- [x] 스코어 관련 스키마 분리 (`score.py`)
- [x] OAuth 관련 스키마 분리 (`oauth.py`)
- [x] FAQ 관련 스키마 분리 (`faq.py`)
- [x] 백오피스 관련 스키마 분리 (`admin.py`)
- [x] 개인 기록 관련 스키마 분리 (`personal_record.py`)
- [x] 사용자 일정 관련 스키마 분리 (`user_schedule.py`)
- [x] `__init__.py` 생성 및 모든 스키마 export
- [x] 순환 참조 처리 (team.py)
- [x] 기존 import 경로 호환성 확인

## ⚠️ 주의사항

### 1. Import 경로 유지
- 기존 코드에서 `from schemas import ...`를 사용하는 모든 곳이 그대로 작동합니다
- `schemas/__init__.py`에서 모든 스키마를 export하여 호환성 유지

### 2. 순환 참조 처리
- `team.py`에서 `MeetingParticipantResponse`를 사용할 때 문자열 타입(`"MeetingParticipantResponse"`)으로 지정하여 순환 참조 방지
- `TYPE_CHECKING`을 사용하여 타입 체크 시에만 import

### 3. Enum Import
- 각 파일에서 필요한 Enum만 명시적으로 import
- `from .enums import EnumName1, EnumName2` 형식 사용

### 4. 결제 관련 스키마 통합
- `payment.py`에 플랜, 결제 수단, 구독, 결제 스키마가 모두 포함됨
- 기존 import 경로는 변경되지 않음

## 📊 정리 효과

### Before (정리 전)
- 단일 파일: `schemas.py` (1,485줄)
- 모든 스키마가 한 파일에 집중
- 유지보수 어려움
- 파일 탐색 및 수정 불편

### After (정리 후)
- 17개 파일로 기능별 분리
- 각 파일이 명확한 책임을 가짐
- 유지보수 용이
- 파일 탐색 및 수정 편리
- 코드 가독성 향상
- 팀 협업 시 충돌 최소화

## 🔍 파일별 스키마 개수 요약

| 파일 | 스키마 개수 | 주요 내용 |
|------|------------|----------|
| `enums.py` | 25 | 모든 Enum 정의 |
| `common.py` | 2 | 공통 응답 스키마 |
| `club.py` | 25 | 클럽 관련 스키마 |
| `meeting.py` | 5 | 모임 관련 스키마 |
| `team.py` | 9 | 팀 관련 스키마 |
| `user.py` | 6 | 사용자 관련 스키마 |
| `payment.py` | 10 | 결제 관련 스키마 (통합) |
| `terms.py` | 6 | 약관 관련 스키마 |
| `notice.py` | 4 | 공지사항 관련 스키마 |
| `inquiry.py` | 8 | 문의 관련 스키마 |
| `expense.py` | 6 | 비용 정산 관련 스키마 |
| `score.py` | 7 | 스코어 관련 스키마 |
| `oauth.py` | 3 | OAuth 관련 스키마 |
| `faq.py` | 9 | FAQ 관련 스키마 |
| `admin.py` | 5 | 백오피스 관련 스키마 |
| `personal_record.py` | 4 | 개인 기록 관련 스키마 |
| `user_schedule.py` | 3 | 사용자 일정 관련 스키마 |
| **총계** | **142** | - |

## 📌 사용 예시

### 기존 코드 (변경 불필요)
```python
from schemas import UserCreate, UserUpdate, UserResponse
from schemas import ClubCreate, ClubResponse
from schemas import MeetingType, MeetingStatus
from schemas import PaymentResponse, SubscriptionResponse
```

### 새로운 방식 (선택적)
```python
# 특정 모듈에서만 필요한 경우
from schemas.user import UserCreate, UserUpdate, UserResponse
from schemas.club import ClubCreate, ClubResponse
from schemas.enums import MeetingType, MeetingStatus
from schemas.payment import PaymentResponse, SubscriptionResponse
```

## 🎯 다음 단계

1. **테스트**: 모든 API 엔드포인트가 정상 작동하는지 확인
2. **리팩토링**: 필요시 특정 모듈에서 직접 import하도록 변경 (선택적)
3. **문서화**: 각 스키마 파일에 상세 주석 추가 (선택적)

---

**작성일**: 2025-01-13  
**버전**: 1.0.0
