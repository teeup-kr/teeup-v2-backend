# TeeupLink API 명세서

## 📋 목차

1. [인증 (Auth)](#1-인증-auth)
2. [사용자 (Users)](#2-사용자-users)
3. [관리자 (Admin)](#3-관리자-admin)
4. [클럽 (Clubs)](#4-클럽-clubs)
5. [모임 (Meetings)](#5-모임-meetings)
6. [FAQ](#6-faq)
7. [공지사항 (Notices)](#7-공지사항-notices)
8. [문의 (Inquiries)](#8-문의-inquiries)
9. [약관 (Terms)](#9-약관-terms)
10. [업로드 (Upload)](#10-업로드-upload)
11. [OAuth](#11-oauth)
12. [요금제 (Plans)](#12-요금제-plans)
13. [결제 (Payments)](#13-결제-payments)
14. [결제 수단 (Payment Methods)](#14-결제-수단-payment-methods)
15. [구독 (Subscriptions)](#15-구독-subscriptions)
16. [지역 (Region)](#16-지역-region)

---

## 1. 인증 (Auth)

**파일:** `routers/auth.py`  
**Prefix:** `/api/v1/auth`  
**태그:** `인증`

### 엔드포인트

| Method | Path | 설명 | Request | Response | 인증 필요 |
|--------|------|------|---------|----------|----------|
| POST | `/login` | 로그인 | [LoginRequest](#loginrequest) | [LoginResponse](#loginresponse) | ❌ |
| POST | `/register` | 회원가입 | [RegisterRequest](#registerrequest) | [LoginResponse](#loginresponse) | ❌ |
| GET | `/me` | 현재 사용자 정보 조회 | - | [UserResponse](#userresponse) | ✅ |
| GET | `/check-email` | 이메일 중복 확인 | Query: `email` | `{available: bool}` | ❌ |
| GET | `/check-nickname` | 닉네임 중복 확인 | Query: `nickname` | `{available: bool}` | ❌ |
| POST | `/validate-password` | 비밀번호 유효성 검사 | `{password: str}` | `{is_valid: bool, errors: []}` | ❌ |
| POST | `/validate-average-score` | 평균 타수 유효성 검사 | `{score: int}` | `{is_valid: bool}` | ❌ |
| PUT | `/change-password` | 비밀번호 변경 | `{current_password: str, new_password: str}` | [MessageResponse](#messageresponse) | ✅ |
| DELETE | `/withdraw` | 회원 탈퇴 | - | [MessageResponse](#messageresponse) | ✅ |
| POST | `/logout` | 로그아웃 | - | [MessageResponse](#messageresponse) | ✅ |
| POST | `/refresh` | 토큰 갱신 | `{refresh_token: str}` | `{access_token: str, refresh_token: str}` | ❌ |
| POST | `/verify-token` | 토큰 검증 | `{token: str}` | `{valid: bool, payload: {}}` | ❌ |
| POST | `/revoke-token` | 토큰 무효화 | `{token: str}` | [MessageResponse](#messageresponse) | ✅ |
| POST | `/revoke-all-tokens` | 모든 토큰 무효화 | - | [MessageResponse](#messageresponse) | ✅ |
| GET | `/csrf-token` | CSRF 토큰 발급 | - | `{csrf_token: str}` | ❌ |
| POST | `/verify-admin-token` | 관리자 토큰 검증 | `{token: str}` | `{valid: bool}` | ❌ |
| GET | `/terms/{terms_type}` | 약관 조회 | Path: `terms_type` | [TermsResponse](#termsresponse) | ❌ |
| POST | `/request-password-reset` | 비밀번호 재설정 요청 | `{email: str}` | [MessageResponse](#messageresponse) | ❌ |
| POST | `/reset-password` | 비밀번호 재설정 | `{token: str, new_password: str}` | [MessageResponse](#messageresponse) | ❌ |

---

## 2. 사용자 (Users)

**파일:** `routers/users.py`  
**Prefix:** `/api/v1/users`  
**태그:** `users`

### 엔드포인트

| Method | Path | 설명 | Request | Response | 인증 필요 |
|--------|------|------|---------|----------|----------|
| GET | `/` | 사용자 목록 조회 (페이지네이션) | Query: `page, limit, search?` | [PaginatedResponse](#paginatedresponse)[[UserResponse](#userresponse)] | ✅ |
| POST | `/` | 사용자 생성 | [UserCreate](#usercreate) | [UserResponse](#userresponse) | ✅ |
| GET | `/profile` | 내 프로필 조회 | - | [UserResponse](#userresponse) | ✅ |
| PUT | `/me` | 내 정보 수정 | [UserUpdate](#userupdate) | [UserResponse](#userresponse) | ✅ |
| PUT | `/{user_id}` | 사용자 정보 수정 | [UserUpdate](#userupdate) | [UserResponse](#userresponse) | ✅ |
| DELETE | `/{user_id}` | 사용자 삭제 | - | [MessageResponse](#messageresponse) | ✅ |
| DELETE | `/account` | 계정 삭제 | - | [MessageResponse](#messageresponse) | ✅ |
| GET | `/{user_id}` | 사용자 상세 조회 | - | [UserResponse](#userresponse) | ✅ |
| GET | `/my-clubs` | 내 클럽 목록 조회 | - | `List`[[ClubResponse](#clubresponse)] | ✅ |
| GET | `/my-meetings` | 내 모임 목록 조회 | Query: `page, limit, status?` | [PaginatedResponse](#paginatedresponse)[[MeetingResponse](#meetingresponse)] | ✅ |
| GET | `/notifications` | 알림 목록 조회 | - | `List`[[NotificationResponse](#notificationresponse)] | ✅ |
| PUT | `/notifications/{notification_id}/read` | 알림 읽음 처리 | - | [MessageResponse](#messageresponse) | ✅ |
| DELETE | `/notifications/{notification_id}` | 알림 삭제 | - | [MessageResponse](#messageresponse) | ✅ |
| PUT | `/notifications/read-all` | 모든 알림 읽음 처리 | - | [MessageResponse](#messageresponse) | ✅ |
| GET | `/notification-settings` | 알림 설정 조회 | - | [NotificationSettingsResponse](#notificationsettingsresponse) | ✅ |
| PUT | `/notification-settings` | 알림 설정 수정 | [NotificationSettingsUpdate](#notificationsettingsupdate) | [NotificationSettingsResponse](#notificationsettingsresponse) | ✅ |
| GET | `/payments` | 결제 내역 조회 | - | `List`[[PaymentResponse](#paymentresponse)] | ✅ |
| GET | `/subscriptions` | 구독 내역 조회 | - | `List`[[SubscriptionResponse](#subscriptionresponse)] | ✅ |
| GET | `/payment-methods` | 결제 수단 목록 조회 | - | `List`[[PaymentMethodResponse](#paymentmethodresponse)] | ✅ |
| GET | `/{user_id}/handicap` | 핸디캡 조회 | - | [HandicapResponse](#handicapresponse) | ✅ |
| PUT | `/{user_id}/handicap` | 핸디캡 수정 | `{handicap: float}` | [MessageResponse](#messageresponse) | ✅ |
| GET | `/handicap/calculate/{user_id}` | 핸디캡 계산 | - | [HandicapResponse](#handicapresponse) | ✅ |
| GET | `/{user_id}/score-history` | 스코어 이력 조회 | - | `List`[[ScoreHistoryResponse](#scorehistoryresponse)] | ✅ |
| GET | `/{user_id}/last-meeting-result` | 최근 모임 결과 조회 | - | [MeetingResultResponse](#meetingresultresponse)? | ✅ |
| GET | `/me/schedule` | 내 일정 조회 | - | [UserScheduleResponse](#userscheduleresponse) | ✅ |
| GET | `/me/rounding-meetings` | 내 라운딩 모임 조회 | - | [RoundingMeetingsResponse](#roundingmeetingsresponse) | ✅ |
| GET | `/me/rounding-stats` | 라운딩 통계 조회 | - | [RoundingStatsResponse](#roundingstatsresponse) | ✅ |
| GET | `/stats` | 사용자 통계 조회 | - | [UserStatsResponse](#userstatsresponse) | ✅ |

---

## 3. 관리자 (Admin)

**파일:** `routers/admin.py`  
**Prefix:** `/api/v1/admin`  
**태그:** `admin`

### 엔드포인트

| Method | Path | 설명 | Request | Response | 인증 필요 |
|--------|------|------|---------|----------|----------|
| POST | `/login` | 관리자 로그인 | [AdminLoginRequest](#adminloginrequest) | [AdminLoginResponse](#adminloginresponse) | ❌ |
| POST | `/generate-client-token` | 클라이언트 토큰 생성 | - | `{token: str}` | ✅ |
| POST | `/logout` | 관리자 로그아웃 | - | [MessageResponse](#messageresponse) | ✅ |
| GET | `/me` | 현재 관리자 정보 조회 | - | `{id: int, email: str, name: str, type: str}` | ✅ |
| GET | `/settings` | 관리자 설정 조회 | - | `{settings: {}}` | ✅ |
| GET | `/dashboard` | 대시보드 조회 | - | `{stats: {}, activities: []}` | ✅ |
| GET | `/dashboard/stats` | 대시보드 통계 조회 | - | `{users: int, clubs: int, meetings: int, ...}` | ✅ |
| GET | `/dashboard/activities` | 대시보드 활동 조회 | - | `List`[[ActivityResponse](#activityresponse)] | ✅ |
| GET | `/debug/sessions` | 세션 디버그 조회 | - | `{sessions: []}` | ✅ |
| GET | `/profile` | 관리자 프로필 조회 | - | `{id: int, email: str, name: str, ...}` | ✅ |
| PUT | `/profile` | 관리자 프로필 수정 | `{name?: str, email?: str}` | `{id: int, email: str, name: str, ...}` | ✅ |
| PUT | `/password` | 비밀번호 변경 | `{current_password: str, new_password: str}` | [MessageResponse](#messageresponse) | ✅ |
| GET | `/clubs` | 클럽 목록 조회 | Query: `page?, limit?, search?` | `List`[[ClubResponse](#clubresponse)] | ✅ |
| GET | `/clubs/{club_id}` | 클럽 상세 조회 | - | [ClubResponse](#clubresponse) | ✅ |
| POST | `/clubs` | 클럽 생성 | [ClubCreate](#clubcreate) | [ClubResponse](#clubresponse) | ✅ |
| PUT | `/clubs/{club_id}` | 클럽 수정 | [ClubUpdate](#clubupdate) | [ClubResponse](#clubresponse) | ✅ |
| DELETE | `/clubs/{club_id}` | 클럽 삭제 | - | [MessageResponse](#messageresponse) | ✅ |
| GET | `/clubs/{club_id}/pending-members` | 대기 중인 멤버 조회 | - | `List`[[ClubMembersResponse](#clubmembersresponse)] | ✅ |
| GET | `/clubs/{club_id}/members` | 클럽 멤버 목록 조회 | - | `List`[[ClubMembersResponse](#clubmembersresponse)] | ✅ |
| POST | `/clubs/{club_id}/members` | 클럽 멤버 추가 | [ClubMemberAddRequest](#clubmemberaddrequest) | [MessageResponse](#messageresponse) | ✅ |
| PUT | `/clubs/{club_id}/members/{user_id}/approve` | 멤버 승인 | - | [MessageResponse](#messageresponse) | ✅ |
| PUT | `/clubs/{club_id}/members/{user_id}/reject` | 멤버 거부 | - | [MessageResponse](#messageresponse) | ✅ |
| PUT | `/clubs/{club_id}/members/{user_id}/role` | 멤버 역할 변경 | [ClubMemberRoleUpdateRequest](#clubmemberroleupdaterequest) | [MessageResponse](#messageresponse) | ✅ |
| DELETE | `/clubs/{club_id}/members/{user_id}` | 멤버 제거 | - | [MessageResponse](#messageresponse) | ✅ |
| GET | `/users` | 사용자 목록 조회 | Query: `page?, limit?, search?, status?` | [PaginatedResponse](#paginatedresponse)[[UserResponse](#userresponse)] | ✅ |
| GET | `/users/search` | 사용자 검색 | Query: `q, page?, limit?` | [PaginatedResponse](#paginatedresponse)[[UserResponse](#userresponse)] | ✅ |
| GET | `/users/create` | 사용자 생성 페이지 데이터 | - | `{roles: [], statuses: []}` | ✅ |
| GET | `/users/create/clubs` | 사용자 생성 시 클럽 목록 | - | `List`[[ClubResponse](#clubresponse)] | ✅ |
| GET | `/users/{user_id}` | 사용자 상세 조회 | - | [UserResponse](#userresponse) | ✅ |
| GET | `/users/{user_id}/clubs` | 사용자 클럽 목록 조회 | - | `List`[[ClubResponse](#clubresponse)] | ✅ |
| GET | `/users/{user_id}/meetings` | 사용자 모임 목록 조회 | - | [UserMeetingsResponse](#usermeetingsresponse) | ✅ |
| GET | `/users/{user_id}/handicap-history` | 사용자 핸디캡 이력 조회 | - | [UserHandicapHistoryResponse](#userhandicaphistoryresponse) | ✅ |
| POST | `/users` | 사용자 생성 | [UserCreate](#usercreate) | [UserResponse](#userresponse) | ✅ |
| PUT | `/users/{user_id}` | 사용자 수정 | [UserUpdate](#userupdate) | [UserResponse](#userresponse) | ✅ |
| DELETE | `/users/{user_id}` | 사용자 삭제 | - | [MessageResponse](#messageresponse) | ✅ |
| GET | `/meetings/rounding` | 라운딩 모임 목록 조회 | Query: `page?, limit?, club_id?` | [PaginatedResponse](#paginatedresponse)[[MeetingResponse](#meetingresponse)] | ✅ |
| GET | `/meetings/event` | 이벤트 모임 목록 조회 | Query: `page?, limit?, club_id?` | [PaginatedResponse](#paginatedresponse)[[MeetingResponse](#meetingresponse)] | ✅ |
| GET | `/meetings/{meeting_id}` | 모임 상세 조회 | - | [MeetingResponse](#meetingresponse) | ✅ |
| POST | `/meetings/rounding` | 라운딩 모임 생성 | [RoundingMeetingCreate](#roundingmeetingcreate) + Query: `club_id` | [MeetingResponse](#meetingresponse) | ✅ |
| POST | `/meetings/event` | 이벤트 모임 생성 | [SocialMeetingCreate](#socialmeetingcreate) + Query: `club_id` | [MeetingResponse](#meetingresponse) | ✅ |
| POST | `/meetings` | 모임 생성 | [RoundingMeetingCreate](#roundingmeetingcreate) 또는 [SocialMeetingCreate](#socialmeetingcreate) | [MeetingResponse](#meetingresponse) | ✅ |
| PUT | `/meetings/{meeting_id}` | 모임 수정 | [MeetingUpdate](#meetingupdate) | [MeetingResponse](#meetingresponse) | ✅ |
| DELETE | `/meetings/{meeting_id}` | 모임 삭제 | - | [MessageResponse](#messageresponse) | ✅ |
| GET | `/payments` | 결제 목록 조회 | Query: `page?, limit?` | `List`[[PaymentResponse](#paymentresponse)] | ✅ |
| POST | `/payments/{payment_id}/cancel` | 결제 취소 | `{cancel_reason?: str}` | [PaymentResponse](#paymentresponse) | ✅ |
| GET | `/refunds` | 환불 목록 조회 | Query: `page?, limit?` | `List`[[RefundResponse](#refundresponse)] | ✅ |
| GET | `/plans` | 요금제 목록 조회 | - | `List`[[PlanResponse](#planresponse)] | ✅ |
| POST | `/plans` | 요금제 생성 | [PlanCreate](#plancreate) | [PlanResponse](#planresponse) | ✅ |
| PUT | `/plans/{plan_id}` | 요금제 수정 | [PlanUpdate](#planupdate) | [PlanResponse](#planresponse) | ✅ |
| DELETE | `/plans/{plan_id}` | 요금제 삭제 | - | [MessageResponse](#messageresponse) | ✅ |
| GET | `/subscriptions` | 구독 목록 조회 | Query: `page?, limit?` | `List`[[SubscriptionResponse](#subscriptionresponse)] | ✅ |
| GET | `/terms` | 약관 목록 조회 | Query: `type?` | [TermsListResponse](#termslistresponse) | ✅ |
| POST | `/terms` | 약관 생성 | [TermsCreate](#termscreate) | [TermsResponse](#termsresponse) | ✅ |
| PUT | `/terms/{terms_type}` | 약관 수정 (타입별) | [TermsUpdate](#termsupdate) | [TermsResponse](#termsresponse) | ✅ |
| PUT | `/terms/id/{term_id}` | 약관 수정 (ID별) | [TermsUpdate](#termsupdate) | [TermsResponse](#termsresponse) | ✅ |
| PUT | `/terms/{term_id}/activate` | 약관 활성화 | - | [MessageResponse](#messageresponse) | ✅ |
| PUT | `/terms/{term_id}/deactivate` | 약관 비활성화 | - | [MessageResponse](#messageresponse) | ✅ |
| GET | `/notices` | 공지사항 목록 조회 | Query: `page?, limit?` | [NoticeListResponse](#noticelistresponse) | ✅ |
| POST | `/notices` | 공지사항 생성 | [NoticeCreate](#noticecreate) | [NoticeResponse](#noticeresponse) | ✅ |
| PUT | `/notices/{notice_id}` | 공지사항 수정 | [NoticeUpdate](#noticeupdate) | [NoticeResponse](#noticeresponse) | ✅ |
| DELETE | `/notices/{notice_id}` | 공지사항 삭제 | - | [MessageResponse](#messageresponse) | ✅ |
| GET | `/inquiries` | 문의 목록 조회 | Query: `page?, limit?, status?` | [InquiryListResponse](#inquirylistresponse) | ✅ |
| GET | `/inquiries/{inquiry_id}` | 문의 상세 조회 | - | [InquiryDetailResponse](#inquirydetailresponse) | ✅ |
| PUT | `/inquiries/{inquiry_id}/status` | 문의 상태 변경 | `{status: str}` | [MessageResponse](#messageresponse) | ✅ |
| POST | `/inquiries/{inquiry_id}/responses` | 문의 답변 작성 | [InquiryResponseCreate](#inquiryresponsecreate) | [InquiryResponseResponse](#inquiryresponseresponse) | ✅ |
| GET | `/notifications` | 알림 목록 조회 | Query: `page?, limit?` | `List`[[NotificationResponse](#notificationresponse)] | ✅ |
| PUT | `/notifications/{notification_id}/read` | 알림 읽음 처리 | - | [MessageResponse](#messageresponse) | ✅ |
| PUT | `/notifications/read-all` | 모든 알림 읽음 처리 | - | [MessageResponse](#messageresponse) | ✅ |
| GET | `/scores` | 스코어 목록 조회 | Query: `page?, limit?` | [ScoreListResponse](#scorelistresponse) | ✅ |
| GET | `/meeting_participants` | 모임 참가자 목록 조회 | Query: `meeting_id?` | `List`[[MeetingParticipantResponse](#meetingparticipantresponse)] | ✅ |
| POST | `/upload` | 파일 업로드 | FormData: `file` | `{url: str, file_id: int}` | ✅ |

---

## 4. 클럽 (Clubs)

### 4.1 기본 CRUD

**파일:** `routers/clubs/base.py`  
**Prefix:** `/api/v1/clubs`  
**태그:** `클럽 관리`

| Method | Path | 설명 | Request | Response | 인증 필요 |
|--------|------|------|---------|----------|----------|
| POST | `/` | 클럽 생성 | [ClubCreate](#clubcreate) | [ClubResponse](#clubresponse) | ✅ |
| GET | `/` | 클럽 목록 조회 | Query: `page?, limit?, status_filter?, sido_code?, gungu_codes?` | `{clubs: [], total: int}` | ✅ |
| GET | `/my` | 내 클럽 목록 조회 | - | `{clubs: []}` | ✅ |
| GET | `/{club_id}` | 클럽 상세 조회 | - | [ClubResponse](#clubresponse) | ✅ |
| PUT | `/{club_id}` | 클럽 수정 | [ClubUpdate](#clubupdate) | [ClubResponse](#clubresponse) | ✅ |
| DELETE | `/{club_id}` | 클럽 삭제 | - | [MessageResponse](#messageresponse) | ✅ |
| GET | `/{club_id}/active-meetings-check` | 활성 모임 확인 | - | `{has_active_meetings: bool}` | ✅ |

### 4.2 멤버 관리

**파일:** `routers/clubs/members.py`  
**Prefix:** `/api/v1/clubs`  
**태그:** `클럽 멤버 관리`

| Method | Path | 설명 | Request | Response | 인증 필요 |
|--------|------|------|---------|----------|----------|
| GET | `/members/search` | 내가 속한 클럽 구성원 이름 검색 | Query: `name(required), limit?(default:100,max:500)` | [ClubMemberSearchResponse](#clubmembersearchresponse) | ✅ |
| GET | `/{club_id}/members` | 클럽 멤버 목록 조회 | Query: `status?, role?` | `{members: [], total: int}` | ✅ |
| POST | `/{club_id}/join` | 클럽 가입 신청 | - | [MessageResponse](#messageresponse) | ✅ |
| POST | `/{club_id}/members` | 클럽 멤버 추가 | [ClubMemberAddRequest](#clubmemberaddrequest) | [MessageResponse](#messageresponse) | ✅ |
| POST | `/{club_id}/members/{user_id}/approve` | 멤버 승인 | - | [MessageResponse](#messageresponse) | ✅ |
| POST | `/{club_id}/members/{user_id}/reject` | 멤버 거부 | - | [MessageResponse](#messageresponse) | ✅ |
| PUT | `/{club_id}/members/{user_id}/role` | 멤버 역할 변경 | [ClubMemberRoleUpdateRequest](#clubmemberroleupdaterequest) | [MessageResponse](#messageresponse) | ✅ |
| DELETE | `/{club_id}/members/{user_id}` | 멤버 제거 | - | [MessageResponse](#messageresponse) | ✅ |
| DELETE | `/{club_id}/membership` | 멤버십 삭제 | - | [MessageResponse](#messageresponse) | ✅ |
| DELETE | `/{club_id}/leave` | 클럽 탈퇴 | - | [MessageResponse](#messageresponse) | ✅ |
| GET | `/{club_id}/members/{user_id}/note` | 멤버 노트 조회 | - | [MemberNoteResponse](#membernoteresponse) | ✅ |
| PUT | `/{club_id}/members/{user_id}/note` | 멤버 노트 수정 | [MemberNoteUpdate](#membernoteupdate) | [MessageResponse](#messageresponse) | ✅ |

### 4.3 회비 관리

**파일:** `routers/clubs/fees.py`  
**Prefix:** `/api/v1/clubs`  
**태그:** `클럽 회비 관리`

| Method | Path | 설명 | Request | Response | 인증 필요 |
|--------|------|------|---------|----------|----------|
| GET | `/{club_id}/regular-fee` | 정기 회비 조회 | - | [RegularFeeResponse](#regularfeeresponse) | ✅ |
| PUT | `/{club_id}/regular-fee` | 정기 회비 수정 | [RegularFeeUpdate](#regularfeeupdate) | [MessageResponse](#messageresponse) | ✅ |
| GET | `/{club_id}/fees` | 회비 목록 조회 | - | `List`[[ClubFeeResponse](#clubfeeresponse)] | ✅ |
| POST | `/{club_id}/fees` | 회비 생성 | [ClubFeeCreate](#clubfeecreate) | [ClubFeeResponse](#clubfeeresponse) | ✅ |
| PUT | `/{club_id}/fees/{fee_id}` | 회비 수정 | [ClubFeeUpdate](#clubfeeupdate) | [ClubFeeResponse](#clubfeeresponse) | ✅ |
| DELETE | `/{club_id}/fees/{fee_id}` | 회비 삭제 | - | [MessageResponse](#messageresponse) | ✅ |

### 4.4 공지사항

**파일:** `routers/clubs/notices.py`  
**Prefix:** `/api/v1/clubs`  
**태그:** `클럽 공지사항`

| Method | Path | 설명 | Request | Response | 인증 필요 |
|--------|------|------|---------|----------|----------|
| GET | `/{club_id}/notices` | 공지사항 목록 조회 | Query: `page?, limit?` | [PaginatedResponse](#paginatedresponse)[[ClubNoticeResponse](#clubnoticeresponse)] | ✅ |
| POST | `/{club_id}/notices` | 공지사항 생성 | [ClubNoticeCreate](#clubnoticecreate) | [ClubNoticeResponse](#clubnoticeresponse) | ✅ |
| GET | `/{club_id}/notices/{notice_id}` | 공지사항 상세 조회 | - | [ClubNoticeResponse](#clubnoticeresponse) | ✅ |
| PUT | `/{club_id}/notices/{notice_id}` | 공지사항 수정 | [ClubNoticeUpdate](#clubnoticeupdate) | [ClubNoticeResponse](#clubnoticeresponse) | ✅ |
| DELETE | `/{club_id}/notices/{notice_id}` | 공지사항 삭제 | - | [MessageResponse](#messageresponse) | ✅ |

### 4.5 규정

**파일:** `routers/clubs/regulations.py`  
**Prefix:** `/api/v1/clubs`  
**태그:** `클럽 규정`

| Method | Path | 설명 | Request | Response | 인증 필요 |
|--------|------|------|---------|----------|----------|
| POST | `/{club_id}/regulations/categories` | 규정 카테고리 생성 | [RegulationCategoryCreate](#regulationcategorycreate) | [RegulationCategoryResponse](#regulationcategoryresponse) | ✅ |
| GET | `/{club_id}/regulations/categories` | 규정 카테고리 목록 조회 | - | `List`[[RegulationCategoryResponse](#regulationcategoryresponse)] | ✅ |
| PUT | `/{club_id}/regulations/categories/{category_id}` | 규정 카테고리 수정 | [RegulationCategoryUpdate](#regulationcategoryupdate) | [RegulationCategoryResponse](#regulationcategoryresponse) | ✅ |
| DELETE | `/{club_id}/regulations/categories/{category_id}` | 규정 카테고리 삭제 | - | [MessageResponse](#messageresponse) | ✅ |
| POST | `/{club_id}/regulations/categories/{category_id}/articles` | 규정 조항 생성 | [ClubRegulationCreate](#clubregulationcreate) | [ClubRegulationResponse](#clubregulationresponse) | ✅ |
| GET | `/{club_id}/regulations/categories/{category_id}/articles` | 규정 조항 목록 조회 | - | `List`[[ClubRegulationResponse](#clubregulationresponse)] | ✅ |
| PUT | `/{club_id}/regulations/categories/{category_id}/articles/{article_id}` | 규정 조항 수정 | [ClubRegulationUpdate](#clubregulationupdate) | [ClubRegulationResponse](#clubregulationresponse) | ✅ |
| DELETE | `/{club_id}/regulations/categories/{category_id}/articles/{article_id}` | 규정 조항 삭제 | - | [MessageResponse](#messageresponse) | ✅ |
| GET | `/{club_id}/regulations/versions` | 규정 버전 목록 조회 | - | `List`[[RegulationVersionResponse](#regulationversionresponse)] | ✅ |
| GET | `/{club_id}/regulations` | 전체 규정 조회 | - | [ClubRegulationsResponse](#clubregulationsresponse) | ✅ |

---

## 5. 모임 (Meetings)

### 5.1 기본 CRUD

**파일:** `routers/meetings/base.py`  
**Prefix:** `/api/v1/meetings`  
**태그:** `모임 관리`

| Method | Path | 설명 | Request | Response | 인증 필요 |
|--------|------|------|---------|----------|----------|
| POST | `/` | 모임 생성 | [RoundingMeetingCreate](#roundingmeetingcreate) + Query: `club_id` | [MeetingResponse](#meetingresponse) | ✅ |
| GET | `/rounding` | 라운딩 모임 목록 조회 | Query: `page?, limit?, club_id?` | [PaginatedResponse](#paginatedresponse)[[MeetingResponse](#meetingresponse)] | ✅ |
| GET | `/` | 모임 목록 조회 (페이지네이션) | Query: `page?, limit?, status?, club_id?` | [PaginatedResponse](#paginatedresponse)[[MeetingResponse](#meetingresponse)] | ✅ |
| GET | `/my` | 내 모임 목록 조회 | Query: `page?, limit?, status?` | [PaginatedResponse](#paginatedresponse)[[MeetingResponse](#meetingresponse)] | ✅ |
| GET | `/{meeting_id}` | 모임 상세 조회 | - | [MeetingResponse](#meetingresponse) | ✅ |
| PUT | `/{meeting_id}` | 모임 수정 | [MeetingUpdate](#meetingupdate) | [MeetingResponse](#meetingresponse) | ✅ |
| DELETE | `/{meeting_id}` | 모임 삭제 | - | [MessageResponse](#messageresponse) | ✅ |
| POST | `/{meeting_id}/cancel` | 모임 취소 | `{cancel_reason?: str}` | [MessageResponse](#messageresponse) | ✅ |
| GET | `/clubs/{club_id}` | 클럽별 모임 목록 조회 | Query: `page?, limit?` | [PaginatedResponse](#paginatedresponse)[[MeetingResponse](#meetingresponse)] | ✅ |
| GET | `/stats` | 모임 통계 조회 | - | [MeetingStatsResponse](#meetingstatsresponse) | ✅ |
| POST | `/{meeting_id}/notify` | 모임 알림 전송 | `{message?: str, type?: str}` | [MeetingNotificationResponse](#meetingnotificationresponse) | ✅ |
| POST | `/{meeting_id}/remind` | 모임 리마인더 전송 | - | [MessageResponse](#messageresponse) | ✅ |

### 5.2 참가자 관리

**파일:** `routers/meetings/participants.py`  
**Prefix:** `/api/v1/meetings`  
**태그:** `모임 참가자 관리`

| Method | Path | 설명 | Request | Response | 인증 필요 |
|--------|------|------|---------|----------|----------|
| GET | `/` | 참가자 목록 조회 | Query: `meeting_id?` | `List`[[MeetingParticipantResponse](#meetingparticipantresponse)] | ✅ |
| GET | `/{participant_id}` | 참가자 상세 조회 | - | [MeetingParticipantResponse](#meetingparticipantresponse) | ✅ |

### 5.3 워크플로우

**파일:** `routers/meetings/workflow.py`  
**Prefix:** `/api/v1/meetings`  
**태그:** `meeting-workflow`

| Method | Path | 설명 | Request | Response | 인증 필요 |
|--------|------|------|---------|----------|----------|
| POST | `/{meeting_id}/apply` | 모임 참가 | - | [MeetingParticipantResponse](#meetingparticipantresponse) | ✅ |
| POST | `/{meeting_id}/guests` | 라운딩 게스트 추가 (생성 후) | [GuestCreate](#guestcreate) | `{message: string, participant_id: int, guest_id: int}` | ✅ |
| POST | `/{meeting_id}/close-application` | 신청 마감 | - | [MessageResponse](#messageresponse) | ✅ |
| GET | `/{meeting_id}/application-status` | 참가 현황 조회 | - | `{participant_count: int, ...}` | ✅ |
| POST | `/{meeting_id}/start-team-formation` | 팀 편성 시작 | - | [MessageResponse](#messageresponse) | ✅ |
| POST | `/{meeting_id}/teams/auto-formation` | 자동 팀 편성 | [TeamFormationRequest](#teamformationrequest) | [TeamFormationResponse](#teamformationresponse) | ✅ |
| POST | `/{meeting_id}/teams/confirm` | 팀 편성 확정 | - | [MessageResponse](#messageresponse) | ✅ |
| POST | `/{meeting_id}/teams/{team_id}/members/{member_id}/confirm` | 팀 멤버 확정 | - | [MessageResponse](#messageresponse) | ✅ |
| POST | `/{meeting_id}/start-rounding` | 라운딩 시작 | - | [MessageResponse](#messageresponse) | ✅ |
| POST | `/{meeting_id}/complete-rounding` | 라운딩 종료 | - | [MessageResponse](#messageresponse) | ✅ |
| POST | `/{meeting_id}/complete` | 모임 완료 | - | [MessageResponse](#messageresponse) | ✅ |
| GET | `/{meeting_id}/results` | 모임 결과 조회 | - | `List`[[MeetingResultResponse](#meetingresultresponse)] | ✅ |
| POST | `/{meeting_id}/settlement/confirm` | 정산 확정 | - | [MessageResponse](#messageresponse) | ✅ |

### 5.4 정산 관리

**파일:** `routers/meetings/settlement.py`  
**Prefix:** `/api/v1/meetings`  
**태그:** `meeting-settlement`

| Method | Path | 설명 | Request | Response | 인증 필요 |
|--------|------|------|---------|----------|----------|
| POST | `/{meeting_id}/settlement/rounding` | 라운딩 정산 | `{participant_ids?: int[]}` | [SettlementResponse](#settlementresponse) | ✅ |
| POST | `/{meeting_id}/settlement/social` | 소셜 모임 정산 | `{participant_ids?: int[]}` | [SettlementResponse](#settlementresponse) | ✅ |
| GET | `/{meeting_id}/settlement` | 정산 정보 조회 | - | [SettlementResponse](#settlementresponse) | ✅ |
| GET | `/{meeting_id}/settlement/my` | 내 정산 정보 조회 | - | [MySettlementResponse](#mysettlementresponse) | ✅ |
| GET | `/{meeting_id}/settlement/available-participants` | 정산 가능 참가자 조회 | - | `List`[[ParticipantResponse](#participantresponse)] | ✅ |

### 5.5 팀 관리

**파일:** `routers/meetings/teams.py`  
**Prefix:** `/api/v1/teams`  
**태그:** `teams`

| Method | Path | 설명 | Request | Response | 인증 필요 |
|--------|------|------|---------|----------|----------|
| GET | `/` | 팀 목록 조회 | Query: `meeting_id` | `List`[[TeamResponse](#teamresponse)] | ✅ |
| POST | `/` | 팀 생성 | [TeamCreate](#teamcreate) + Query: `meeting_id` | [TeamResponse](#teamresponse) | ✅ |
| GET | `/{team_id}` | 팀 상세 조회 | - | [TeamResponse](#teamresponse) | ✅ |
| PUT | `/{team_id}` | 팀 수정 | [TeamUpdate](#teamupdate) | [TeamResponse](#teamresponse) | ✅ |
| DELETE | `/{team_id}` | 팀 삭제 | - | [MessageResponse](#messageresponse) | ✅ |
| POST | `/auto-formation` | 자동 팀 편성 | [TeamFormationRequest](#teamformationrequest) + Query: `meeting_id` | [TeamFormationResponse](#teamformationresponse) | ✅ |

### 5.6 점수 관리

**파일:** `routers/meetings/scores.py`  
**Prefix:** `/api/v1/scores` (일반), `/api/v1/meetings` (모임 관련)  
**태그:** `scores`, `모임 스코어`

#### 일반 스코어 관리

| Method | Path | 설명 | Request | Response | 인증 필요 |
|--------|------|------|---------|----------|----------|
| POST | `/` | 스코어 등록 | [ScoreCreate](#scorecreate) | [ScoreResponse](#scoreresponse) | ✅ |
| GET | `/` | 스코어 목록 조회 | Query: `participant_id?, meeting_id?` | [ScoreListResponse](#scorelistresponse) | ✅ |
| GET | `/{score_id}` | 스코어 상세 조회 | - | [ScoreResponse](#scoreresponse) | ✅ |
| PUT | `/{score_id}` | 스코어 수정 | [ScoreUpdate](#scoreupdate) | [ScoreResponse](#scoreresponse) | ✅ |
| DELETE | `/{score_id}` | 스코어 삭제 | - | [MessageResponse](#messageresponse) | ✅ |
| GET | `/stats/{participant_id}` | 참가자 스코어 통계 조회 | - | [ScoreStats](#scorestats) | ✅ |

#### 모임 스코어 관리

| Method | Path | 설명 | Request | Response | 인증 필요 |
|--------|------|------|---------|----------|----------|
| GET | `/{meeting_id}/participants/{participant_id}/scores` | 참가자 스코어 조회 | Query: `page?, limit?` | [ScoreListResponse](#scorelistresponse) | ✅ |
| GET | `/{meeting_id}/participants/{participant_id}/scores/stats` | 참가자 스코어 통계 조회 | - | [ScoreStats](#scorestats) | ✅ |
| POST | `/{meeting_id}/participants/{participant_id}/simple-score` | 간단 스코어 등록 | [SimpleScoreCreate](#simplescorecreate) | [SimpleScoreResponse](#simplescoreresponse) | ✅ |
| PUT | `/{meeting_id}/participants/{participant_id}/simple-score` | 간단 스코어 수정 | [SimpleScoreCreate](#simplescorecreate) | [SimpleScoreResponse](#simplescoreresponse) | ✅ |

### 5.7 비용 관리

**파일:** `routers/meetings/expenses.py`  
**Prefix:** `/api/v1/meetings`  
**태그:** `비용 정산`

| Method | Path | 설명 | Request | Response | 인증 필요 |
|--------|------|------|---------|----------|----------|
| GET | `/{meeting_id}/expenses` | 비용 목록 조회 | - | [ExpenseListResponse](#expenselistresponse) | ✅ |
| POST | `/{meeting_id}/expenses` | 비용 생성 | [ExpenseCreate](#expensecreate) | [ExpenseResponse](#expenseresponse) | ✅ |
| GET | `/{meeting_id}/expenses/{expense_id}` | 비용 상세 조회 | - | [ExpenseResponse](#expenseresponse) | ✅ |
| PUT | `/{meeting_id}/expenses/{expense_id}` | 비용 수정 | [ExpenseUpdate](#expenseupdate) | [ExpenseResponse](#expenseresponse) | ✅ |
| DELETE | `/{meeting_id}/expenses/{expense_id}` | 비용 삭제 | - | [MessageResponse](#messageresponse) | ✅ |
| GET | `/{meeting_id}/expenses/{expense_id}/participants` | 비용 참가자 목록 조회 | - | `List`[[ExpenseParticipantResponse](#expenseparticipantresponse)] | ✅ |
| PUT | `/{meeting_id}/expenses/{expense_id}/participants/{participant_id}` | 비용 참가자 수정 | [ExpenseParticipantUpdate](#expenseparticipantupdate) | [ExpenseParticipantResponse](#expenseparticipantresponse) | ✅ |

### 5.8 라운딩 전용

**파일:** `routers/meetings/types/rounds.py`  
**Prefix:** `/api/v1/rounds`  
**태그:** `라운딩 관리`

| Method | Path | 설명 | Request | Response | 인증 필요 |
|--------|------|------|---------|----------|----------|
| GET | `/` | 라운딩 모임 목록 조회 | Query: `page?, limit?, club_id?` | [PaginatedResponse](#paginatedresponse)[[MeetingResponse](#meetingresponse)] | ✅ |
| POST | `/` | 라운딩 모임 생성 | [RoundingMeetingCreate](#roundingmeetingcreate) + Query: `club_id` | [MeetingResponse](#meetingresponse) | ✅ |
| GET | `/{meeting_id}` | 라운딩 모임 상세 조회 | - | [MeetingResponse](#meetingresponse) | ✅ |
| PUT | `/{meeting_id}` | 라운딩 모임 수정 | [MeetingUpdate](#meetingupdate) | [MeetingResponse](#meetingresponse) | ✅ |
| DELETE | `/{meeting_id}` | 라운딩 모임 삭제 | - | [MessageResponse](#messageresponse) | ✅ |
| POST | `/{meeting_id}/join` | 라운딩 모임 참가 | - | [MeetingParticipantResponse](#meetingparticipantresponse) | ✅ |
| DELETE | `/{meeting_id}/leave` | 라운딩 모임 탈퇴 | - | [MessageResponse](#messageresponse) | ✅ |
| GET | `/{meeting_id}/participants` | 참가자 목록 조회 | - | `List`[[MeetingParticipantResponse](#meetingparticipantresponse)] | ✅ |
| GET | `/{meeting_id}/teams` | 팀 목록 조회 | - | `List`[[TeamResponse](#teamresponse)] | ✅ |
| POST | `/{meeting_id}/teams/{team_id}/members` | 팀 멤버 추가 | `{participant_id: int, order?: int}` | [TeamMemberResponse](#teammemberresponse) | ✅ |
| DELETE | `/{meeting_id}/teams/{team_id}/members/{member_id}` | 팀 멤버 제거 | - | [MessageResponse](#messageresponse) | ✅ |

### 5.9 소셜 모임 전용

**파일:** `routers/meetings/types/socials.py`  
**Prefix:** `/api/v1/socials`  
**태그:** `소셜 모임 관리`

| Method | Path | 설명 | Request | Response | 인증 필요 |
|--------|------|------|---------|----------|----------|
| GET | `/` | 소셜 모임 목록 조회 | Query: `page?, limit?, club_id?` | [PaginatedResponse](#paginatedresponse)[[MeetingResponse](#meetingresponse)] | ✅ |
| POST | `/` | 소셜 모임 생성 | [SocialMeetingCreate](#socialmeetingcreate) + Query: `club_id` | [MeetingResponse](#meetingresponse) | ✅ |
| GET | `/{meeting_id}` | 소셜 모임 상세 조회 | - | [MeetingResponse](#meetingresponse) | ✅ |
| PUT | `/{meeting_id}` | 소셜 모임 수정 | [MeetingUpdate](#meetingupdate) | [MeetingResponse](#meetingresponse) | ✅ |
| DELETE | `/{meeting_id}` | 소셜 모임 삭제 | - | [MessageResponse](#messageresponse) | ✅ |
| POST | `/{meeting_id}/join` | 소셜 모임 참가 | `{guest_info?: object}` | [MeetingParticipantResponse](#meetingparticipantresponse) | ✅ |
| DELETE | `/{meeting_id}/leave` | 소셜 모임 탈퇴 | - | [MessageResponse](#messageresponse) | ✅ |
| POST | `/{meeting_id}/cancel` | 소셜 모임 취소 | `{cancel_reason?: str}` | [MessageResponse](#messageresponse) | ✅ |

---

## 6. FAQ

**파일:** `routers/faq.py`  
**Prefix:** `/api/v1/admin` (관리자), `/api/v1` (클라이언트)  
**태그:** `admin`, `faq`

### 관리자 API

| Method | Path | 설명 | Request | Response | 인증 필요 |
|--------|------|------|---------|----------|----------|
| GET | `/admin/faq/categories` | FAQ 카테고리 목록 조회 | - | `List`[[FAQCategoryResponse](#faqcategoryresponse)] | ✅ |
| POST | `/admin/faq/categories` | FAQ 카테고리 생성 | [FAQCategoryCreate](#faqcategorycreate) | [FAQCategoryResponse](#faqcategoryresponse) | ✅ |
| PUT | `/admin/faq/categories/{category_id}` | FAQ 카테고리 수정 | [FAQCategoryUpdate](#faqcategoryupdate) | [FAQCategoryResponse](#faqcategoryresponse) | ✅ |
| DELETE | `/admin/faq/categories/{category_id}` | FAQ 카테고리 삭제 | - | [MessageResponse](#messageresponse) | ✅ |
| GET | `/admin/faq` | FAQ 목록 조회 | Query: `page?, limit?, category_id?` | [PaginatedResponse](#paginatedresponse)[[FAQResponse](#faqresponse)] | ✅ |
| POST | `/admin/faq` | FAQ 생성 | [FAQCreate](#faqcreate) | [FAQResponse](#faqresponse) | ✅ |
| GET | `/admin/faq/{faq_id}` | FAQ 상세 조회 | - | [FAQResponse](#faqresponse) | ✅ |
| PUT | `/admin/faq/{faq_id}` | FAQ 수정 | [FAQUpdate](#faqupdate) | [FAQResponse](#faqresponse) | ✅ |
| DELETE | `/admin/faq/{faq_id}` | FAQ 삭제 | - | [MessageResponse](#messageresponse) | ✅ |

### 클라이언트 API

| Method | Path | 설명 | Request | Response | 인증 필요 |
|--------|------|------|---------|----------|----------|
| GET | `/faq/categories` | FAQ 카테고리 목록 조회 | - | `List`[[FAQCategoryResponse](#faqcategoryresponse)] | ❌ |
| GET | `/faq` | FAQ 목록 조회 | Query: `page?, limit?, category_id?` | [FAQPageResponse](#faqpageresponse) | ❌ |
| GET | `/faq/{faq_id}` | FAQ 상세 조회 | - | [FAQResponse](#faqresponse) | ❌ |

---

## 7. 공지사항 (Notices)

**파일:** `routers/notices.py`  
**Prefix:** `/api/v1/notices`  
**태그:** `notices`

| Method | Path | 설명 | Request | Response | 인증 필요 |
|--------|------|------|---------|----------|----------|
| GET | `/` | 공지사항 목록 조회 | Query: `page?, limit?, type?` | [NoticeListResponse](#noticelistresponse) | ✅ |
| POST | `/upload` | 공지사항 파일 업로드 | FormData: `file` | `{url: str}` | ✅ |
| POST | `/` | 공지사항 생성 | [NoticeCreate](#noticecreate) | [NoticeResponse](#noticeresponse) | ✅ |
| GET | `/{notice_id}` | 공지사항 상세 조회 | - | [NoticeResponse](#noticeresponse) | ✅ |
| PUT | `/{notice_id}` | 공지사항 수정 | [NoticeUpdate](#noticeupdate) | [NoticeResponse](#noticeresponse) | ✅ |
| DELETE | `/{notice_id}` | 공지사항 삭제 | - | [MessageResponse](#messageresponse) | ✅ |
| GET | `/types/` | 공지사항 타입 목록 조회 | - | `List[{id, name}]` | ✅ |

---

## 8. 문의 (Inquiries)

**파일:** `routers/inquiries.py`  
**Prefix:** `/api/v1/inquiries`  
**태그:** `inquiries`

| Method | Path | 설명 | Request | Response | 인증 필요 |
|--------|------|------|---------|----------|----------|
| GET | `/` | 문의 목록 조회 | Query: `page?, limit?, status?` | [InquiryListResponse](#inquirylistresponse) | ✅ |
| POST | `/` | 문의 생성 | [InquiryCreate](#inquirycreate) | [InquiryResponse](#inquiryresponse) | ✅ |
| GET | `/{inquiry_id}` | 문의 상세 조회 | - | [InquiryDetailResponse](#inquirydetailresponse) | ✅ |
| PUT | `/{inquiry_id}` | 문의 수정 | [InquiryUpdate](#inquiryupdate) | [InquiryResponse](#inquiryresponse) | ✅ |
| DELETE | `/{inquiry_id}` | 문의 삭제 | - | [MessageResponse](#messageresponse) | ✅ |
| POST | `/{inquiry_id}/response` | 문의 답변 | [InquiryResponseCreate](#inquiryresponsecreate) | [InquiryResponseResponse](#inquiryresponseresponse) | ✅ |
| PUT | `/{inquiry_id}/response/{response_id}` | 문의 답변 수정 | [InquiryResponseUpdate](#inquiryresponseupdate) | [InquiryResponseResponse](#inquiryresponseresponse) | ✅ |
| DELETE | `/{inquiry_id}/response/{response_id}` | 문의 답변 삭제 | - | [MessageResponse](#messageresponse) | ✅ |

---

## 9. 약관 (Terms)

**파일:** `routers/terms.py`  
**Prefix:** `/api/v1/terms`  
**태그:** `terms`

| Method | Path | 설명 | Request | Response | 인증 필요 |
|--------|------|------|---------|----------|----------|
| GET | `/` | 약관 목록 조회 | Query: `type?` | [TermsListResponse](#termslistresponse) | ❌ |
| GET | `/{terms_id}` | 약관 상세 조회 | - | [TermsResponse](#termsresponse) | ❌ |

---

## 10. 업로드 (Upload)

**파일:** `routers/upload.py`  
**Prefix:** `/api/v1/upload`  
**태그:** `upload`

| Method | Path | 설명 | Request | Response | 인증 필요 |
|--------|------|------|---------|----------|----------|
| POST | `/` | 파일 업로드 | FormData: `file` | `{url: str, file_id: int}` | ✅ |
| DELETE | `/{file_id}` | 파일 삭제 | - | [MessageResponse](#messageresponse) | ✅ |

---

## 11. OAuth

**파일:** `routers/oauth.py`  
**Prefix:** `/api/v1/auth/oauth`  
**태그:** `OAuth`

| Method | Path | 설명 | Request | Response | 인증 필요 |
|--------|------|------|---------|----------|----------|
| GET | `/google` | Google OAuth 로그인 | Query: `redirect_uri?` | Redirect to Google | ❌ |
| GET | `/google/callback` | Google OAuth 콜백 | Query: `code, state?` | [LoginResponse](#loginresponse) | ❌ |
| GET | `/kakao` | Kakao OAuth 로그인 | Query: `redirect_uri?` | Redirect to Kakao | ❌ |
| GET | `/kakao/callback` | Kakao OAuth 콜백 | Query: `code, state?` | [LoginResponse](#loginresponse) | ❌ |
| GET | `/naver` | Naver OAuth 로그인 | Query: `redirect_uri?` | Redirect to Naver | ❌ |
| GET | `/naver/callback` | Naver OAuth 콜백 | Query: `code, state?` | [LoginResponse](#loginresponse) | ❌ |

---

## 12. 요금제 (Plans)

**파일:** `routers/plans.py`  
**Prefix:** `/api/v1/plans`  
**태그:** `plans`

| Method | Path | 설명 | Request | Response | 인증 필요 |
|--------|------|------|---------|----------|----------|
| GET | `/` | 요금제 목록 조회 | Query: `active?` | `List`[[PlanResponse](#planresponse)] | ❌ |
| GET | `/{plan_id}` | 요금제 상세 조회 | - | [PlanResponse](#planresponse) | ❌ |

---

## 13. 결제 (Payments)

**파일:** `routers/payments.py`  
**Prefix:** `/api/v1/payments`  
**태그:** `payments`

| Method | Path | 설명 | Request | Response | 인증 필요 |
|--------|------|------|---------|----------|----------|
| POST | `/confirm` | 결제 확인 | [PaymentConfirmRequest](#paymentconfirmrequest) | [PaymentResponse](#paymentresponse) | ✅ |
| GET | `/{payment_key}` | 결제 상세 조회 | - | [PaymentResponse](#paymentresponse) | ✅ |
| POST | `/cancel` | 결제 취소 | [PaymentCancelRequest](#paymentcancelrequest) | [PaymentResponse](#paymentresponse) | ✅ |
| GET | `/` | 결제 목록 조회 | Query: `page?, limit?` | `List`[[PaymentResponse](#paymentresponse)] | ✅ |
| GET | `/statistics` | 결제 통계 조회 | Query: `start_date?, end_date?` | `{total_amount, count, ...}` | ✅ |

---

## 14. 결제 수단 (Payment Methods)

**파일:** `routers/payment_methods.py`  
**Prefix:** `/api/v1/payment-methods`  
**태그:** `payment-methods`

| Method | Path | 설명 | Request | Response | 인증 필요 |
|--------|------|------|---------|----------|----------|
| GET | `/` | 결제 수단 목록 조회 | - | `List`[[PaymentMethodResponse](#paymentmethodresponse)] | ✅ |
| POST | `/` | 결제 수단 등록 | [PaymentMethodCreate](#paymentmethodcreate) | [PaymentMethodResponse](#paymentmethodresponse) | ✅ |
| PUT | `/{method_id}` | 결제 수단 수정 | [PaymentMethodUpdate](#paymentmethodupdate) | [PaymentMethodResponse](#paymentmethodresponse) | ✅ |
| DELETE | `/{method_id}` | 결제 수단 삭제 | - | [MessageResponse](#messageresponse) | ✅ |
| PUT | `/{method_id}/set-default` | 기본 결제 수단 설정 | - | [MessageResponse](#messageresponse) | ✅ |

---

## 15. 구독 (Subscriptions)

**파일:** `routers/subscriptions.py`  
**Prefix:** `/api/v1/subscriptions`  
**태그:** `subscriptions`

| Method | Path | 설명 | Request | Response | 인증 필요 |
|--------|------|------|---------|----------|----------|
| GET | `/` | 구독 목록 조회 | Query: `status?` | `List`[[SubscriptionResponse](#subscriptionresponse)] | ✅ |
| POST | `/` | 구독 생성 | [SubscriptionCreate](#subscriptioncreate) | [SubscriptionResponse](#subscriptionresponse) | ✅ |
| GET | `/{subscription_id}` | 구독 상세 조회 | - | [SubscriptionResponse](#subscriptionresponse) | ✅ |
| PUT | `/{subscription_id}` | 구독 수정 | [SubscriptionUpdate](#subscriptionupdate) | [SubscriptionResponse](#subscriptionresponse) | ✅ |
| DELETE | `/{subscription_id}` | 구독 취소 | - | [MessageResponse](#messageresponse) | ✅ |
| POST | `/{subscription_id}/renew` | 구독 갱신 | - | [SubscriptionResponse](#subscriptionresponse) | ✅ |

---

## 16. 지역 (Region)

**파일:** `routers/region.py`  
**Prefix:** `/api/v1`  
**태그:** `region`

| Method | Path | 설명 | Request | Response | 인증 필요 |
|--------|------|------|---------|----------|----------|
| GET | `/sido-list` | 시도 목록 조회 | - | `List`[{code, name}] | ❌ |
| GET | `/gungu-list` | 시군구 목록 조회 | Query: `sido_code` | `List`[{code, name}] | ❌ |
| POST | `/region-list` | [TEST]공공 API 기반 지역 데이터 동기화 | - | `{success: bool, fetchedCount: int, syncedCount: int?, message: str}` | ❌ |

---

## 📝 참고사항

- 모든 API는 `/api/v1` prefix를 사용합니다.
- 인증이 필요한 API는 JWT 토큰을 `Authorization: Bearer {token}` 헤더에 포함해야 합니다.
- 응답 형식은 JSON입니다.
- 에러 응답은 HTTP 상태 코드와 함께 에러 메시지를 포함합니다.

---

**문서 생성일:** 2025-01-XX  
**API 버전:** 1.0.0

---

## 📦 Request/Response 스키마 상세

### 인증 (Auth)

#### LoginRequest

**사용되는 엔드포인트:**

- [POST `/api/v1/auth/login`](#1-인증-auth) - 로그인

```json
{
  "email": string,
  "password": string
}
```

#### LoginResponse

**사용되는 엔드포인트:**

- [POST `/api/v1/auth/login`](#1-인증-auth) - 로그인
- [POST `/api/v1/auth/register`](#1-인증-auth) - 회원가입
- [GET `/api/v1/auth/oauth/google/callback`](#11-oauth) - Google OAuth 콜백
- [GET `/api/v1/auth/oauth/kakao/callback`](#11-oauth) - Kakao OAuth 콜백
- [GET `/api/v1/auth/oauth/naver/callback`](#11-oauth) - Naver OAuth 콜백

```json
{
  "access_token": string,
  "refresh_token": string,
  "token_type": string,
  "expires_in": int,
  "user": {
    "id": int,
    "email": string,
    "nickname": string,
    "type": string
  }
}
```

#### RegisterRequest

**사용되는 엔드포인트:**

- [POST `/api/v1/auth/register`](#1-인증-auth) - 회원가입

```json
{
  "email": string,
  "password": string,
  "nickname": string,
  "average_score": int,
  "terms_agreement": boolean,
  "privacy_policy": boolean,
  "privacy_collection": boolean,
  "marketing_consent": boolean
}
```

#### AdminLoginRequest

**사용되는 엔드포인트:**

- [POST `/api/v1/admin/login`](#3-관리자-admin) - 관리자 로그인

```json
{
  "email": string,
  "password": string
}
```

#### AdminLoginResponse

**사용되는 엔드포인트:**

- [POST `/api/v1/admin/login`](#3-관리자-admin) - 관리자 로그인

```json
{
  "access_token": string,
  "refresh_token": string,
  "token_type": string,
  "user": {
    "id": int,
    "email": string,
    "name": string,
    "type": string
  }
}
```

---

### 사용자 (Users)

#### UserCreate

**status**: `string` (optional) → enum: [UserStatus](#userstatus)

**사용되는 엔드포인트:**

- [POST `/api/v1/users/`](#2-사용자-users) - 사용자 생성
- [POST `/api/v1/admin/users`](#3-관리자-admin) - 사용자 생성

```json
{
  "email": string,
  "realname": string,
  "nickname": string,
  "password": string,
  "phone_number": string,
  "birthdate": string (YYYY-MM-DD, optional),
  "gender": string (M/F, optional),
  "handicap": float (optional),
  "average_score": int (optional),
  "role": string (optional),
  "status": "ACTIVE",
  "needs_terms_agreement": boolean (optional),
  "terms_agreement": boolean (optional),
  "privacy_policy": boolean (optional),
  "privacy_collection": boolean (optional),
  "marketing_consent": boolean (optional)
}
```

#### UserUpdate

**사용되는 엔드포인트:**

- [PUT `/api/v1/users/me`](#2-사용자-users) - 내 정보 수정
- [PUT `/api/v1/users/{user_id}`](#2-사용자-users) - 사용자 정보 수정
- [PUT `/api/v1/admin/users/{user_id}`](#3-관리자-admin) - 사용자 수정

```json
{
  "nickname": string (optional),
  "phone_number": string (optional),
  "birthdate": string (YYYY-MM-DD, optional),
  "gender": string (M/F, optional),
  "handicap": float (optional),
  "average_score": int (optional)
}
```

#### UserResponse

**status**: `string` → enum: [UserStatus](#userstatus)  
**provider**: `string` (optional) → enum: [Provider](#provider)

**사용되는 엔드포인트:**

- [GET `/api/v1/auth/me`](#1-인증-auth) - 현재 사용자 정보 조회
- [GET `/api/v1/users/`](#2-사용자-users) - 사용자 목록 조회
- [POST `/api/v1/users/`](#2-사용자-users) - 사용자 생성
- [GET `/api/v1/users/profile`](#2-사용자-users) - 내 프로필 조회
- [PUT `/api/v1/users/me`](#2-사용자-users) - 내 정보 수정
- [PUT `/api/v1/users/{user_id}`](#2-사용자-users) - 사용자 정보 수정
- [GET `/api/v1/users/{user_id}`](#2-사용자-users) - 사용자 상세 조회
- [GET `/api/v1/admin/users`](#3-관리자-admin) - 사용자 목록 조회
- [GET `/api/v1/admin/users/search`](#3-관리자-admin) - 사용자 검색
- [GET `/api/v1/admin/users/{user_id}`](#3-관리자-admin) - 사용자 상세 조회
- [POST `/api/v1/admin/users`](#3-관리자-admin) - 사용자 생성
- [PUT `/api/v1/admin/users/{user_id}`](#3-관리자-admin) - 사용자 수정

```json
{
  "id": int,
  "email": string,
  "realname": string (optional),
  "nickname": string,
  "phone_number": string (optional),
  "birthdate": datetime (ISO 8601, optional),
  "gender": string (M/F, optional),
  "handicap": float (optional),
  "average_score": int (optional),
  "role": string,
  "status": "ACTIVE",
  "provider": "LOCAL",
  "email_verified": datetime (ISO 8601, optional),
  "needs_terms_agreement": boolean,
  "terms_agreement": boolean (optional),
  "privacy_policy": boolean (optional),
  "privacy_collection": boolean (optional),
  "marketing_consent": boolean (optional),
  "club_count": int (optional),
  "deactivated_at": datetime (ISO 8601, optional),
  "created_at": datetime (ISO 8601),
  "updated_at": datetime (ISO 8601)
}
```

---

### 클럽 (Clubs)

#### ClubCreate

**type**: `string` → enum: [ClubType](#clubtype)
**필수**: `sido_code` (1개), `gungu_codes` (1~4개)

**사용되는 엔드포인트:**

- [POST `/api/v1/clubs/`](#4-클럽-clubs) - 클럽 생성
- [POST `/api/v1/admin/clubs`](#3-관리자-admin) - 클럽 생성

```json
{
  "name": string,
  "sido_code": string,
  "gungu_codes": [string], // 1~4개
  "type": "REGULAR",
  "description": string,
  "member_count": int,
  "contact_info": string,
  "representative_name": string,
  "additional_info": string
}
```

#### ClubUpdate

**사용되는 엔드포인트:**

- [PUT `/api/v1/clubs/{club_id}`](#4-클럽-clubs) - 클럽 수정
- [PUT `/api/v1/admin/clubs/{club_id}`](#3-관리자-admin) - 클럽 수정

**필수**: `sido_code` (1개), `gungu_codes` (1~4개)

```json
{
  "name": string,
  "sido_code": string,
  "gungu_codes": [string], // 1~4개
  "description": string,
  "member_count": int
}
```

#### ClubResponse

**type**: `string` → enum: [ClubType](#clubtype)  
**status**: `string` → enum: [ClubStatus](#clubstatus)  
**membership_status**: `string` (optional) → enum: [MembershipStatus](#membershipstatus)  
**membership_role**: `string` (optional) → enum: [ClubRole](#clubrole)

**사용되는 엔드포인트:**

- [GET `/api/v1/auth/me`](#1-인증-auth) - 현재 사용자 정보 조회
- [GET `/api/v1/users/my-clubs`](#2-사용자-users) - 내 클럽 목록 조회
- [GET `/api/v1/users/{user_id}/clubs`](#2-사용자-users) - 사용자 클럽 목록 조회
- [GET `/api/v1/admin/clubs`](#3-관리자-admin) - 클럽 목록 조회
- [GET `/api/v1/admin/clubs/{club_id}`](#3-관리자-admin) - 클럽 상세 조회
- [GET `/api/v1/admin/users/create/clubs`](#3-관리자-admin) - 사용자 생성 시 클럽 목록
- [GET `/api/v1/admin/users/{user_id}/clubs`](#3-관리자-admin) - 사용자 클럽 목록 조회
- [GET `/api/v1/clubs/`](#4-클럽-clubs) - 클럽 목록 조회
- [GET `/api/v1/clubs/my`](#4-클럽-clubs) - 내 클럽 목록 조회
- [GET `/api/v1/clubs/{club_id}`](#4-클럽-clubs) - 클럽 상세 조회
- [POST `/api/v1/clubs/`](#4-클럽-clubs) - 클럽 생성
- [PUT `/api/v1/clubs/{club_id}`](#4-클럽-clubs) - 클럽 수정
- [POST `/api/v1/admin/clubs`](#3-관리자-admin) - 클럽 생성
- [PUT `/api/v1/admin/clubs/{club_id}`](#3-관리자-admin) - 클럽 수정

```json
{
  "id": int,
  "display_id": string (optional),
  "name": string,
  "sido_code": string (optional),
  "gungu_codes": [string] (optional),
  "type": "REGULAR",
  "description": string (optional),
  "member_count": int (optional),
  "current_member_count": int (optional),
  "contact_info": string (optional),
  "representative_name": string (optional),
  "additional_info": string (optional),
  "status": "ACTIVE",
  "created_at": datetime (ISO 8601),
  "updated_at": datetime (ISO 8601),
  "membership_status": "ACTIVE",
  "membership_role": "MEMBER"
}
```

#### ClubMemberSearchResponse

**사용되는 엔드포인트:**

- [GET `/api/v1/clubs/members/search`](#4-클럽-clubs) - 내가 속한 클럽 구성원 이름 검색

**요청 예시:**

```http
GET /api/v1/clubs/members/search?name=홍&limit=50
Authorization: Bearer {access_token}
```

**응답 규칙:**

- `data[].members[].handicap` 값은 `handicap`이 있으면 해당 값을 사용합니다.
- `handicap`이 없으면 `handicap_init` 값을 `handicap` 필드로 내려줍니다.

```json
{
  "keyword": string,
  "data": [
    {
      "club_id": int,
      "club_display_id": string (optional),
      "club_name": string,
      "members": [
        {
          "id": int,
          "name": string,
          "gender": string (optional),
          "handicap": float (optional)
        }
      ]
    }
  ],
  "total_clubs": int,
  "total_members": int
}
```

#### ClubMemberAddRequest

**role**: `string` (optional, default: MEMBER) → enum: [ClubRole](#clubrole)

**사용되는 엔드포인트:**

- [POST `/api/v1/admin/clubs/{club_id}/members`](#3-관리자-admin) - 클럽 멤버 추가

```json
{
  "user_id": int,
  "role": "MEMBER"
}
```

#### ClubMemberRoleUpdateRequest

**role**: `string` → enum: [ClubRole](#clubrole)

**사용되는 엔드포인트:**

- [PUT `/api/v1/admin/clubs/{club_id}/members/{user_id}/role`](#3-관리자-admin) - 멤버 역할 변경
- [PUT `/api/v1/clubs/{club_id}/members/{user_id}/role`](#4-클럽-clubs) - 멤버 역할 변경

```json
{
  "role": "MEMBER"
}
```

#### RegularFeeUpdate

**regular_fee_cycle**: `string` (optional) → enum: [BillingCycle](#billingcycle)

**사용되는 엔드포인트:**

- [PUT `/api/v1/clubs/{club_id}/regular-fee`](#4-클럽-clubs) - 정기 회비 수정

```json
{
  "has_regular_fee": boolean,
  "regular_fee_amount": float (optional, ge=0),
  "regular_fee_cycle": "MONTHLY",
  "regular_fee_description": string (optional)
}
```

#### RegularFeeResponse

**regular_fee_cycle**: `string` → enum: [BillingCycle](#billingcycle)

**사용되는 엔드포인트:**

- [GET `/api/v1/clubs/{club_id}/regular-fee`](#4-클럽-clubs) - 정기 회비 조회

```json
{
  "has_regular_fee": boolean,
  "regular_fee_amount": int,
  "regular_fee_cycle": "MONTHLY",
  "regular_fee_description": string
}
```

#### ClubFeeCreate

**사용되는 엔드포인트:**

- [POST `/api/v1/clubs/{club_id}/fees`](#4-클럽-clubs) - 회비 생성

```json
{
  "name": string,
  "amount": int,
  "due_date": datetime (ISO 8601),
  "description": string
}
```

#### ClubFeeUpdate

**사용되는 엔드포인트:**

- [PUT `/api/v1/clubs/{club_id}/fees/{fee_id}`](#4-클럽-clubs) - 회비 수정

```json
{
  "name": string,
  "amount": int,
  "due_date": datetime (ISO 8601),
  "description": string
}
```

#### ClubFeeResponse

**사용되는 엔드포인트:**

- [GET `/api/v1/clubs/{club_id}/fees`](#4-클럽-clubs) - 회비 목록 조회
- [POST `/api/v1/clubs/{club_id}/fees`](#4-클럽-clubs) - 회비 생성
- [PUT `/api/v1/clubs/{club_id}/fees/{fee_id}`](#4-클럽-clubs) - 회비 수정

```json
{
  "id": int,
  "club_id": int,
  "name": string,
  "amount": int,
  "due_date": datetime (ISO 8601),
  "description": string,
  "created_at": datetime (ISO 8601),
  "updated_at": datetime (ISO 8601)
}
```

#### ClubNoticeCreate

**사용되는 엔드포인트:**

- [POST `/api/v1/clubs/{club_id}/notices`](#4-클럽-clubs) - 공지사항 생성

```json
{
  "title": string,
  "content": string,
  "is_pinned": boolean
}
```

#### ClubNoticeUpdate

**사용되는 엔드포인트:**

- [PUT `/api/v1/clubs/{club_id}/notices/{notice_id}`](#4-클럽-clubs) - 공지사항 수정

```json
{
  "title": string,
  "content": string,
  "is_pinned": boolean
}
```

#### ClubNoticeResponse

**사용되는 엔드포인트:**

- [GET `/api/v1/clubs/{club_id}/notices`](#4-클럽-clubs) - 공지사항 목록 조회
- [POST `/api/v1/clubs/{club_id}/notices`](#4-클럽-clubs) - 공지사항 생성
- [GET `/api/v1/clubs/{club_id}/notices/{notice_id}`](#4-클럽-clubs) - 공지사항 상세 조회
- [PUT `/api/v1/clubs/{club_id}/notices/{notice_id}`](#4-클럽-clubs) - 공지사항 수정

```json
{
  "id": int,
  "club_id": int,
  "title": string,
  "content": string,
  "is_pinned": boolean,
  "view_count": int,
  "created_at": datetime (ISO 8601),
  "updated_at": datetime (ISO 8601)
}
```

#### MemberNoteUpdate

**사용되는 엔드포인트:**

- [PUT `/api/v1/clubs/{club_id}/members/{user_id}/note`](#4-클럽-clubs) - 멤버 노트 수정

```json
{
  "note": string
}
```

#### MemberNoteResponse

**사용되는 엔드포인트:**

- [GET `/api/v1/clubs/{club_id}/members/{user_id}/note`](#4-클럽-clubs) - 멤버 노트 조회

```json
{
  "note": string,
  "updated_at": datetime (ISO 8601)
}
```

---

### 모임 (Meetings)

#### RoundingMeetingCreate

**meeting_type**: `string` → enum: [MeetingType](#meetingtype)  
**meeting_subtype**: `string` → enum: [MeetingSubtype](#meetingsubtype)  
**settlement_method**: `string` → enum: [SettlementMethod](#settlementmethod)  
**team_formation_mode**: `string` → enum: [TeamFormationMode](#teamformationmode)

**사용되는 엔드포인트:**

- [POST `/api/v1/admin/meetings/rounding`](#3-관리자-admin) - 라운딩 모임 생성
- [POST `/api/v1/admin/meetings`](#3-관리자-admin) - 모임 생성
- [POST `/api/v1/meetings/`](#5-모임-meetings) - 모임 생성
- [POST `/api/v1/meetings/rounding/`](#5-모임-meetings) - 라운딩 모임 생성

```json
{
  "name": string,
  "description": string,
  "location": string,
  "meeting_time": datetime (ISO 8601),
  "tee_times": array[string],
  "max_participants": int,
  "meeting_type": "ROUND",
  "meeting_subtype": "REGULAR",
  "total_cost": int,
  "green_fee": int,
  "caddy_fee": int,
  "cart_fee": int,
  "settlement_method": "EQUAL_SPLIT",
  "course_name": string,
  "hole_count": int,
  "reservation_name": string,
  "application_deadline": datetime (ISO 8601),
  "team_formation_mode": "GENDER_MIXED_HANDICAP",
  "team_size": int
}
```

- `selected_guests`는 라운딩 생성 시 받지 않습니다. 게스트는 생성 후 `POST /api/v1/meetings/{meeting_id}/guests`로 추가합니다.

#### SocialMeetingCreate

**social_settlement_method**: `string` → enum: [SocialSettlementMethod](#socialsettlementmethod)

**사용되는 엔드포인트:**

- [POST `/api/v1/admin/meetings/event`](#3-관리자-admin) - 이벤트 모임 생성
- [POST `/api/v1/admin/meetings`](#3-관리자-admin) - 모임 생성
- [POST `/api/v1/meetings/`](#5-모임-meetings) - 모임 생성
- [POST `/api/v1/meetings/social/`](#5-모임-meetings) - 소셜 모임 생성

```json
{
  "name": string,
  "description": string,
  "meeting_time": datetime (ISO 8601),
  "max_participants": int,
  "venue_name": string,
  "social_cost": int,
  "social_settlement_method": "EQUAL_SPLIT",
  "club_id": int,
  "application_deadline": datetime (ISO 8601),
  "social_notes": string
}
```

#### MeetingUpdate

**사용되는 엔드포인트:**

- [PUT `/api/v1/admin/meetings/{meeting_id}`](#3-관리자-admin) - 모임 수정
- [PUT `/api/v1/meetings/{meeting_id}`](#5-모임-meetings) - 모임 수정
- [PUT `/api/v1/meetings/rounding/{meeting_id}`](#5-모임-meetings) - 라운딩 모임 수정
- [PUT `/api/v1/meetings/social/{meeting_id}`](#5-모임-meetings) - 소셜 모임 수정

```json
{
  "name": string,
  "description": string,
  "meeting_time": datetime (ISO 8601),
  "max_participants": int,
  "total_cost": int
}
```

#### MeetingResponse

**meeting_type**: `string` → enum: [MeetingType](#meetingtype)  
**meeting_subtype**: `string` → enum: [MeetingSubtype](#meetingsubtype)  
**team_formation_mode**: `string` → enum: [TeamFormationMode](#teamformationmode)  
**settlement_method**: `string` → enum: [SettlementMethod](#settlementmethod)  
**status**: `string` → enum: [MeetingStatus](#meetingstatus)

**사용되는 엔드포인트:**

- [GET `/api/v1/users/my-meetings`](#2-사용자-users) - 내 모임 목록 조회
- [GET `/api/v1/admin/meetings/rounding`](#3-관리자-admin) - 라운딩 모임 목록 조회
- [GET `/api/v1/admin/meetings/event`](#3-관리자-admin) - 이벤트 모임 목록 조회
- [GET `/api/v1/admin/meetings/{meeting_id}`](#3-관리자-admin) - 모임 상세 조회
- [POST `/api/v1/admin/meetings/rounding`](#3-관리자-admin) - 라운딩 모임 생성
- [POST `/api/v1/admin/meetings/event`](#3-관리자-admin) - 이벤트 모임 생성
- [POST `/api/v1/admin/meetings`](#3-관리자-admin) - 모임 생성
- [PUT `/api/v1/admin/meetings/{meeting_id}`](#3-관리자-admin) - 모임 수정
- [GET `/api/v1/meetings/rounding`](#5-모임-meetings) - 라운딩 모임 목록 조회
- [GET `/api/v1/meetings/`](#5-모임-meetings) - 모임 목록 조회
- [GET `/api/v1/meetings/my`](#5-모임-meetings) - 내 모임 목록 조회
- [GET `/api/v1/meetings/{meeting_id}`](#5-모임-meetings) - 모임 상세 조회
- [PUT `/api/v1/meetings/{meeting_id}`](#5-모임-meetings) - 모임 수정
- [GET `/api/v1/meetings/clubs/{club_id}`](#5-모임-meetings) - 클럽별 모임 목록 조회
- [POST `/api/v1/meetings/`](#5-모임-meetings) - 모임 생성
- [GET `/api/v1/meetings/rounding/`](#5-모임-meetings) - 라운딩 모임 목록 조회
- [POST `/api/v1/meetings/rounding/`](#5-모임-meetings) - 라운딩 모임 생성
- [GET `/api/v1/meetings/rounding/{meeting_id}`](#5-모임-meetings) - 라운딩 모임 상세 조회
- [PUT `/api/v1/meetings/rounding/{meeting_id}`](#5-모임-meetings) - 라운딩 모임 수정
- [GET `/api/v1/meetings/social/`](#5-모임-meetings) - 소셜 모임 목록 조회
- [POST `/api/v1/meetings/social/`](#5-모임-meetings) - 소셜 모임 생성
- [GET `/api/v1/meetings/social/{meeting_id}`](#5-모임-meetings) - 소셜 모임 상세 조회
- [PUT `/api/v1/meetings/social/{meeting_id}`](#5-모임-meetings) - 소셜 모임 수정

```json
{
  "id": int,
  "name": string,
  "description": string,
  "location": string,
  "meeting_time": datetime (ISO 8601),
  "application_deadline": datetime (ISO 8601),
  "tee_times": array[string],
  "max_participants": int,
  "meeting_type": "ROUND",
  "meeting_subtype": "REGULAR",
  "team_formation_mode": "GENDER_MIXED_HANDICAP",
  "team_size": int,
  "total_cost": int,
  "green_fee": int,
  "caddy_fee": int,
  "cart_fee": int,
  "settlement_method": "EQUAL_SPLIT",
  "social_settlement_method": null (optional),
  "course_name": string,
  "hole_count": int,
  "reservation_name": string,
  "venue_name": null (optional),
  "club_id": int,
  "status": "SCHEDULED",
  "cancel_reason": null (optional),
  "created_at": datetime (ISO 8601),
  "updated_at": datetime (ISO 8601),
  "club_name": string,
  "participant_count": int,
  "social_cost": null (optional),
  "social_notes": null (optional),
  "application_closed_early": boolean,
  "team_formation_confirmed_at": null (optional),
  "rounding_started_at": null (optional),
  "rounding_completed_at": null (optional),
  "settlement_confirmed": boolean
}
```

#### MeetingParticipantResponse

**participant_type**: `string` → enum: [ParticipantType](#participanttype)  

**사용되는 엔드포인트:**

- [GET `/api/v1/admin/meeting_participants`](#3-관리자-admin) - 모임 참가자 목록 조회
- [GET `/api/v1/meetings/`](#5-모임-meetings) - 참가자 목록 조회
- [GET `/api/v1/meetings/{participant_id}`](#5-모임-meetings) - 참가자 상세 조회
- [POST `/api/v1/meetings/{meeting_id}/apply`](#5-모임-meetings) - 모임 신청

```json
{
  "id": int,
  "user_id": int,
  "guest_id": null (optional),
  "participant_type": "USER",
  "user_name": string,
  "user_nickname": string,
  "handicap": int,
  "average_score": int,
  "pace_preference": string,
  "tee_preference": string,
  "is_newbie": boolean,
  "prefer_with": array[string],
  "avoid_with": array,
  "created_at": datetime (ISO 8601)
}
```

#### TeamCreate

**formation_mode**: `string` → enum: [TeamFormationMode](#teamformationmode)

**사용되는 엔드포인트:**

- [POST `/api/v1/teams/`](#5-모임-meetings) - 팀 생성

```json
{
  "name": string,
  "formation_mode": "GENDER_MIXED_HANDICAP",
  "formation_notes": string
}
```

#### TeamUpdate

**status**: `string` → enum: [TeamStatus](#teamstatus)

**사용되는 엔드포인트:**

- [PUT `/api/v1/teams/{team_id}`](#5-모임-meetings) - 팀 수정

```json
{
  "name": string,
  "status": "CONFIRMED",
  "formation_notes": string
}
```

#### TeamResponse

**formation_mode**: `string` → enum: [TeamFormationMode](#teamformationmode)  
**status**: `string` → enum: [TeamStatus](#teamstatus)

**사용되는 엔드포인트:**

- [GET `/api/v1/teams/`](#5-모임-meetings) - 팀 목록 조회
- [GET `/api/v1/teams/{team_id}`](#5-모임-meetings) - 팀 상세 조회
- [POST `/api/v1/teams/`](#5-모임-meetings) - 팀 생성
- [PUT `/api/v1/teams/{team_id}`](#5-모임-meetings) - 팀 수정

```json
{
  "id": int,
  "name": string,
  "meeting_id": int,
  "formation_mode": "GENDER_MIXED_HANDICAP",
  "status": "CONFIRMED",
  "formation_notes": string,
  "created_at": datetime (ISO 8601),
  "updated_at": datetime (ISO 8601),
  "members": array[object]
}
```

#### TeamFormationRequest

**formation_mode**: `string` → enum: [TeamFormationMode](#teamformationmode)

**사용되는 엔드포인트:**

- [POST `/api/v1/meetings/{meeting_id}/teams/auto-formation`](#5-모임-meetings) - 자동 팀 편성
- [POST `/api/v1/teams/auto-formation`](#5-모임-meetings) - 자동 팀 편성

```json
{
  "formation_mode": "GENDER_MIXED_HANDICAP",
  "team_size": int,
  "preferences": object,
  "guests": null (optional)
}
```

#### TeamFormationResponse

**사용되는 엔드포인트:**

- [POST `/api/v1/meetings/{meeting_id}/teams/auto-formation`](#5-모임-meetings) - 자동 팀 편성
- [POST `/api/v1/teams/auto-formation`](#5-모임-meetings) - 자동 팀 편성

```json
{
  "teams": array[object],
  "total_teams": int,
  "unassigned_participants": array,
  "total_participants": int,
  "formation_summary": object
}
```

#### TeamMemberResponse

**사용되는 엔드포인트:**

- [POST `/api/v1/meetings/{meeting_id}/teams/{team_id}/members`](#5-모임-meetings) - 팀 멤버 추가

```json
{
  "id": int,
  "team_id": int,
  "user_id": int (nullable),
  "order": int,
  "user_name": string,
  "user_nickname": string,
  "gender": string (nullable),
  "handicap": int (nullable),
  "average_score": int (nullable),
  "is_guest": boolean (nullable),
  "created_at": datetime (ISO 8601)
}
```

---

### FAQ

#### FAQCategoryCreate

**사용되는 엔드포인트:**

- [POST `/api/v1/admin/faq/categories`](#6-faq) - FAQ 카테고리 생성

```json
{
  "title": string,
  "order": int,
  "is_active": boolean
}
```

#### FAQCategoryUpdate

**사용되는 엔드포인트:**

- [PUT `/api/v1/admin/faq/categories/{category_id}`](#6-faq) - FAQ 카테고리 수정

```json
{
  "title": string,
  "order": int,
  "is_active": boolean
}
```

#### FAQCategoryResponse

**사용되는 엔드포인트:**

- [GET `/api/v1/admin/faq/categories`](#6-faq) - FAQ 카테고리 목록 조회
- [POST `/api/v1/admin/faq/categories`](#6-faq) - FAQ 카테고리 생성
- [PUT `/api/v1/admin/faq/categories/{category_id}`](#6-faq) - FAQ 카테고리 수정
- [GET `/api/v1/faq/categories`](#6-faq) - FAQ 카테고리 목록 조회

```json
{
  "id": int,
  "title": string,
  "order": int,
  "is_active": boolean,
  "created_at": datetime (ISO 8601),
  "updated_at": datetime (ISO 8601)
}
```

#### FAQCreate

**사용되는 엔드포인트:**

- [POST `/api/v1/admin/faq`](#6-faq) - FAQ 생성

```json
{
  "question": string,
  "answer": string,
  "category_id": int,
  "order": int,
  "is_active": boolean
}
```

#### FAQUpdate

**사용되는 엔드포인트:**

- [PUT `/api/v1/admin/faq/{faq_id}`](#6-faq) - FAQ 수정

```json
{
  "question": string,
  "answer": string,
  "category_id": int,
  "order": int,
  "is_active": boolean
}
```

#### FAQResponse

**사용되는 엔드포인트:**

- [GET `/api/v1/admin/faq`](#6-faq) - FAQ 목록 조회
- [POST `/api/v1/admin/faq`](#6-faq) - FAQ 생성
- [GET `/api/v1/admin/faq/{faq_id}`](#6-faq) - FAQ 상세 조회
- [PUT `/api/v1/admin/faq/{faq_id}`](#6-faq) - FAQ 수정
- [GET `/api/v1/faq/{faq_id}`](#6-faq) - FAQ 상세 조회

```json
{
  "id": int,
  "question": string,
  "answer": string,
  "category_id": int,
  "category_title": string,
  "order": int,
  "is_active": boolean,
  "is_deleted": boolean,
  "view_count": int,
  "created_at": datetime (ISO 8601),
  "updated_at": datetime (ISO 8601),
  "deleted_at": null (optional)
}
```

#### FAQPageResponse

**사용되는 엔드포인트:**

- [GET `/api/v1/faq`](#6-faq) - FAQ 목록 조회

```json
{
  "items": array[object],
  "total": int,
  "page": int,
  "limit": int,
  "total_pages": int
}
```

---

### 공지사항 (Notices)

#### NoticeCreate

**type**: `string` → enum: [NoticeType](#noticetype)

**사용되는 엔드포인트:**

- [POST `/api/v1/admin/notices`](#3-관리자-admin) - 공지사항 생성
- [POST `/api/v1/notices/`](#7-공지사항-notices) - 공지사항 생성

```json
{
  "title": string,
  "content": string,
  "type": "GENERAL",
  "is_important": boolean,
  "is_published": boolean,
  "attachment_file": null (optional),
  "web_view_link": null (optional)
}
```

#### NoticeUpdate

**사용되는 엔드포인트:**

- [PUT `/api/v1/admin/notices/{notice_id}`](#3-관리자-admin) - 공지사항 수정
- [PUT `/api/v1/notices/{notice_id}`](#7-공지사항-notices) - 공지사항 수정

```json
{
  "title": string,
  "content": string,
  "type": string,
  "is_important": boolean,
  "is_published": boolean
}
```

#### NoticeResponse

**type**: `string` → enum: [NoticeType](#noticetype)

**사용되는 엔드포인트:**

- [GET `/api/v1/admin/notices`](#3-관리자-admin) - 공지사항 목록 조회
- [POST `/api/v1/admin/notices`](#3-관리자-admin) - 공지사항 생성
- [GET `/api/v1/admin/notices/{notice_id}`](#3-관리자-admin) - 공지사항 상세 조회
- [PUT `/api/v1/admin/notices/{notice_id}`](#3-관리자-admin) - 공지사항 수정
- [GET `/api/v1/notices/`](#7-공지사항-notices) - 공지사항 목록 조회
- [POST `/api/v1/notices/`](#7-공지사항-notices) - 공지사항 생성
- [GET `/api/v1/notices/{notice_id}`](#7-공지사항-notices) - 공지사항 상세 조회
- [PUT `/api/v1/notices/{notice_id}`](#7-공지사항-notices) - 공지사항 수정

```json
{
  "id": int,
  "title": string,
  "content": string,
  "type": "GENERAL",
  "is_important": boolean,
  "is_published": boolean,
  "view_count": int,
  "published_at": datetime (ISO 8601),
  "attachment_file": null (optional),
  "web_view_link": null (optional),
  "created_at": datetime (ISO 8601),
  "updated_at": datetime (ISO 8601)
}
```

#### NoticeListResponse

**사용되는 엔드포인트:**

- [GET `/api/v1/admin/notices`](#3-관리자-admin) - 공지사항 목록 조회
- [GET `/api/v1/notices/`](#7-공지사항-notices) - 공지사항 목록 조회

```json
{
  "notices": array[object],
  "total": int,
  "page": int,
  "size": int,
  "total_pages": int
}
```

---

### 문의 (Inquiries)

#### InquiryCreate

**type**: `string` → enum: [InquiryType](#inquirytype)

**사용되는 엔드포인트:**

- [POST `/api/v1/inquiries/`](#8-문의-inquiries) - 문의 생성

```json
{
  "title": string,
  "content": string,
  "type": "GENERAL",
  "priority": int
}
```

#### InquiryUpdate

**status**: `string` → enum: [InquiryStatus](#inquirystatus)

**사용되는 엔드포인트:**

- [PUT `/api/v1/inquiries/{inquiry_id}`](#8-문의-inquiries) - 문의 수정

```json
{
  "title": string,
  "content": string,
  "type": string,
  "status": "SUBMITTED",
  "priority": int
}
```

#### InquiryResponse

**type**: `string` → enum: [InquiryType](#inquirytype)  
**status**: `string` → enum: [InquiryStatus](#inquirystatus)

**사용되는 엔드포인트:**

- [GET `/api/v1/admin/inquiries`](#3-관리자-admin) - 문의 목록 조회
- [GET `/api/v1/admin/inquiries/{inquiry_id}`](#3-관리자-admin) - 문의 상세 조회
- [GET `/api/v1/inquiries/`](#8-문의-inquiries) - 문의 목록 조회
- [POST `/api/v1/inquiries/`](#8-문의-inquiries) - 문의 생성
- [GET `/api/v1/inquiries/{inquiry_id}`](#8-문의-inquiries) - 문의 상세 조회
- [PUT `/api/v1/inquiries/{inquiry_id}`](#8-문의-inquiries) - 문의 수정

```json
{
  "id": int,
  "user_id": int,
  "user_name": string,
  "user_nickname": string,
  "title": string,
  "content": string,
  "type": "GENERAL",
  "status": "SUBMITTED",
  "priority": int,
  "created_at": datetime (ISO 8601),
  "updated_at": datetime (ISO 8601)
}
```

#### InquiryListResponse

**사용되는 엔드포인트:**

- [GET `/api/v1/admin/inquiries`](#3-관리자-admin) - 문의 목록 조회
- [GET `/api/v1/inquiries/`](#8-문의-inquiries) - 문의 목록 조회

```json
{
  "inquiries": array[object],
  "total": int,
  "page": int,
  "size": int,
  "total_pages": int
}
```

#### InquiryResponseCreate

**사용되는 엔드포인트:**

- [POST `/api/v1/admin/inquiries/{inquiry_id}/responses`](#3-관리자-admin) - 문의 답변 작성
- [POST `/api/v1/inquiries/{inquiry_id}/response`](#8-문의-inquiries) - 문의 답변

```json
{
  "inquiry_id": int,
  "content": string,
  "is_internal": boolean
}
```

#### InquiryResponseResponse

**사용되는 엔드포인트:**

- [POST `/api/v1/admin/inquiries/{inquiry_id}/responses`](#3-관리자-admin) - 문의 답변 작성
- [POST `/api/v1/inquiries/{inquiry_id}/response`](#8-문의-inquiries) - 문의 답변
- [PUT `/api/v1/inquiries/{inquiry_id}/response/{response_id}`](#8-문의-inquiries) - 문의 답변 수정

```json
{
  "id": int,
  "inquiry_id": int,
  "admin_id": int,
  "admin_name": string,
  "content": string,
  "is_internal": boolean,
  "created_at": datetime (ISO 8601)
}
```

#### InquiryDetailResponse

**사용되는 엔드포인트:**

- [GET `/api/v1/admin/inquiries/{inquiry_id}`](#3-관리자-admin) - 문의 상세 조회
- [GET `/api/v1/inquiries/{inquiry_id}`](#8-문의-inquiries) - 문의 상세 조회

```json
{
  "inquiry": object,
  "responses": array[object],
  "total_responses": int
}
```

---

### 약관 (Terms)

#### TermsCreate

**type**: `string` → enum: [TermsType](#termstype)

**사용되는 엔드포인트:**

- [POST `/api/v1/admin/terms`](#3-관리자-admin) - 약관 생성

```json
{
  "type": "SERVICE",
  "title": string,
  "content": string,
  "is_active": boolean
}
```

#### TermsUpdate

**type**: `string` → enum: [TermsType](#termstype)

**사용되는 엔드포인트:**

- [PUT `/api/v1/admin/terms/{terms_type}`](#3-관리자-admin) - 약관 수정 (타입별)
- [PUT `/api/v1/admin/terms/id/{term_id}`](#3-관리자-admin) - 약관 수정 (ID별)

```json
{
  "type": "SERVICE",
  "title": string,
  "content": string,
  "is_active": boolean
}
```

#### TermsResponse

**type**: `string` → enum: [TermsType](#termstype)

**사용되는 엔드포인트:**

- [GET `/api/v1/auth/terms/{terms_type}`](#1-인증-auth) - 약관 조회
- [GET `/api/v1/admin/terms`](#3-관리자-admin) - 약관 목록 조회
- [POST `/api/v1/admin/terms`](#3-관리자-admin) - 약관 생성
- [PUT `/api/v1/admin/terms/{terms_type}`](#3-관리자-admin) - 약관 수정 (타입별)
- [PUT `/api/v1/admin/terms/id/{term_id}`](#3-관리자-admin) - 약관 수정 (ID별)
- [GET `/api/v1/terms/`](#9-약관-terms) - 약관 목록 조회
- [GET `/api/v1/terms/{terms_id}`](#9-약관-terms) - 약관 상세 조회

```json
{
  "id": int,
  "type": "SERVICE",
  "title": string,
  "content": string,
  "is_active": boolean,
  "is_required": boolean,
  "published_at": datetime (ISO 8601),
  "created_at": datetime (ISO 8601),
  "updated_at": datetime (ISO 8601)
}
```

#### TermsListResponse

**사용되는 엔드포인트:**

- [GET `/api/v1/admin/terms`](#3-관리자-admin) - 약관 목록 조회
- [GET `/api/v1/terms/`](#9-약관-terms) - 약관 목록 조회

```json
{
  "terms": array[object],
  "total": int,
  "page": int,
  "size": int,
  "total_pages": int
}
```

---

### 알림 (Notifications)

#### NotificationResponse

**type**: `string` → enum: [NotificationType](#notificationtype)  
**status**: `string` → enum: [NotificationStatus](#notificationstatus)

**사용되는 엔드포인트:**

- [GET `/api/v1/users/notifications`](#2-사용자-users) - 알림 목록 조회
- [GET `/api/v1/admin/notifications`](#3-관리자-admin) - 알림 목록 조회

```json
{
  "id": int,
  "user_id": int,
  "type": "GENERAL",
  "title": string,
  "content": string,
  "status": "UNREAD",
  "read_at": null (optional),
  "created_at": datetime (ISO 8601)
}
```

#### NotificationSettingsResponse

**사용되는 엔드포인트:**

- [GET `/api/v1/users/notification-settings`](#2-사용자-users) - 알림 설정 조회
- [PUT `/api/v1/users/notification-settings`](#2-사용자-users) - 알림 설정 수정

```json
{
  "user_id": int,
  "push_enabled": boolean,
  "email_enabled": boolean,
  "meeting_reminders": boolean,
  "payment_notifications": boolean,
  "club_updates": boolean,
  "marketing_emails": boolean
}
```

#### NotificationSettingsUpdate

**사용되는 엔드포인트:**

- [PUT `/api/v1/users/notification-settings`](#2-사용자-users) - 알림 설정 수정

```json
{
  "push_enabled": boolean,
  "email_enabled": boolean,
  "meeting_reminders": boolean,
  "payment_notifications": boolean,
  "club_updates": boolean,
  "marketing_emails": boolean
}
```

---

### 관리자 (Admin)

#### UserMeetingsResponse

**사용되는 엔드포인트:**

- [GET `/api/v1/admin/users/{user_id}/meetings`](#3-관리자-admin) - 사용자 모임 목록 조회

```json
{
  "rounding_meetings": array[object],
  "social_meetings": array,
  "total_rounding": int,
  "total_social": int
}
```

#### UserHandicapHistoryResponse

**사용되는 엔드포인트:**

- [GET `/api/v1/admin/users/{user_id}/handicap-history`](#3-관리자-admin) - 사용자 핸디캡 이력 조회

```json
{
  "handicap_info": object,
  "score_history": array[object],
  "total": int,
  "page": int,
  "limit": int,
  "total_pages": int
}
```

---

### 핸디캡 및 통계 (Handicap & Statistics)

#### HandicapResponse

**사용되는 엔드포인트:**

- [GET `/api/v1/users/{user_id}/handicap`](#2-사용자-users) - 핸디캡 조회
- [GET `/api/v1/users/handicap/calculate/{user_id}`](#2-사용자-users) - 핸디캡 계산

```json
{
  "user_id": int,
  "nickname": string,
  "handicap": float,
  "average_score": int,
  "initial_handicap": float,
  "calculated_handicap": float,
  "handicap_update_method": string,
  "handicap_calculation_count": int,
  "is_auto_calculated": boolean
}
```

#### ScoreHistoryResponse

**사용되는 엔드포인트:**

- [GET `/api/v1/users/{user_id}/score-history`](#2-사용자-users) - 스코어 이력 조회

```json
{
  "id": int,
  "meeting_id": int,
  "meeting_name": string,
  "gross_score": int,
  "net_score": float,
  "handicap_used": float,
  "played_at": datetime (ISO 8601),
  "created_at": datetime (ISO 8601)
}
```

#### MeetingResultResponse

**사용되는 엔드포인트:**

- [GET `/api/v1/users/{user_id}/last-meeting-result`](#2-사용자-users) - 최근 모임 결과 조회
- [GET `/api/v1/meetings/{meeting_id}/results`](#5-모임-meetings) - 모임 결과 조회

```json
{
  "id": int,
  "meeting_id": int,
  "meeting_name": string,
  "user_id": int,
  "gross_score": int,
  "net_score": float,
  "rank": int,
  "handicap_used": float,
  "completed_at": datetime (ISO 8601),
  "created_at": datetime (ISO 8601)
}
```

#### UserScheduleResponse

**사용되는 엔드포인트:**

- [GET `/api/v1/users/me/schedule`](#2-사용자-users) - 내 일정 조회

```json
{
  "total_meetings": int,
  "date_range": object,
  "schedules": array[object]
}
```

#### RoundingMeetingsResponse

**사용되는 엔드포인트:**

- [GET `/api/v1/users/me/rounding-meetings`](#2-사용자-users) - 내 라운딩 모임 조회

```json
{
  "data": array[object],
  "total": int,
  "page": int,
  "limit": int,
  "total_pages": int
}
```

#### RoundingStatsResponse

**사용되는 엔드포인트:**

- [GET `/api/v1/users/me/rounding-stats`](#2-사용자-users) - 라운딩 통계 조회

```json
{
  "total_games": int,
  "average_score": float,
  "recent_5_avg": float,
  "best_score": int,
  "worst_score": int,
  "current_handicap": float,
  "initial_handicap": float
}
```

#### UserStatsResponse

**사용되는 엔드포인트:**

- [GET `/api/v1/users/stats`](#2-사용자-users) - 사용자 통계 조회

```json
{
  "total_users": int,
  "active_users": int,
  "inactive_users": int,
  "deleted_users": int,
  "admin_users": int,
  "regular_users": int,
  "users_by_gender": object,
  "users_by_provider": object,
  "users_by_month": array[object],
  "average_handicap": float,
  "users_with_handicap": int,
  "users_without_handicap": int
}
```

---

### 공통 (Common)

#### MessageResponse

**사용되는 엔드포인트:**

- 대부분의 POST, PUT, DELETE 엔드포인트에서 사용 (성공/실패 메시지 응답)

```json
{
  "message": string,
  "success": boolean
}
```

#### PaginatedResponse

**사용되는 엔드포인트:**

- 페이지네이션이 필요한 목록 조회 엔드포인트에서 사용 (예: [GET `/api/v1/users/`](#2-사용자-users), [GET `/api/v1/clubs/`](#4-클럽-clubs), [GET `/api/v1/meetings/`](#5-모임-meetings) 등)

```json
{
  "data": array[object],
  "total": int,
  "page": int,
  "limit": int,
  "total_pages": int
}
```

---

### 클럽 규정 (Club Regulations)

#### RegulationCategoryCreate

**사용되는 엔드포인트:**

- [POST `/api/v1/clubs/{club_id}/regulations/categories`](#4-클럽-clubs) - 규정 카테고리 생성

```json
{
  "name": string,
  "description": string,
  "order": int
}
```

#### RegulationCategoryUpdate

**사용되는 엔드포인트:**

- [PUT `/api/v1/clubs/{club_id}/regulations/categories/{category_id}`](#4-클럽-clubs) - 규정 카테고리 수정

```json
{
  "name": string,
  "description": string,
  "order": int
}
```

#### RegulationCategoryResponse

**사용되는 엔드포인트:**

- [POST `/api/v1/clubs/{club_id}/regulations/categories`](#4-클럽-clubs) - 규정 카테고리 생성
- [GET `/api/v1/clubs/{club_id}/regulations/categories`](#4-클럽-clubs) - 규정 카테고리 목록 조회
- [PUT `/api/v1/clubs/{club_id}/regulations/categories/{category_id}`](#4-클럽-clubs) - 규정 카테고리 수정

```json
{
  "id": int,
  "club_id": int,
  "name": string,
  "order": int,
  "description": string,
  "created_at": datetime (ISO 8601),
  "updated_at": datetime (ISO 8601)
}
```

#### ClubRegulationCreate

**status**: `string` → enum: [RegulationStatus](#regulationstatus)

**사용되는 엔드포인트:**

- [POST `/api/v1/clubs/{club_id}/regulations/categories/{category_id}/articles`](#4-클럽-clubs) - 규정 조항 생성

```json
{
  "category_id": int,
  "title": string,
  "content": string,
  "status": "ACTIVE"
}
```

#### ClubRegulationUpdate

**status**: `string` → enum: [RegulationStatus](#regulationstatus)

**사용되는 엔드포인트:**

- [PUT `/api/v1/clubs/{club_id}/regulations/categories/{category_id}/articles/{article_id}`](#4-클럽-clubs) - 규정 조항 수정

```json
{
  "category_id": int,
  "title": string,
  "content": string,
  "status": "ACTIVE"
}
```

#### ClubRegulationResponse

**status**: `string` → enum: [RegulationStatus](#regulationstatus)

**사용되는 엔드포인트:**

- [POST `/api/v1/clubs/{club_id}/regulations/categories/{category_id}/articles`](#4-클럽-clubs) - 규정 조항 생성
- [GET `/api/v1/clubs/{club_id}/regulations/categories/{category_id}/articles`](#4-클럽-clubs) - 규정 조항 목록 조회
- [PUT `/api/v1/clubs/{club_id}/regulations/categories/{category_id}/articles/{article_id}`](#4-클럽-clubs) - 규정 조항 수정

```json
{
  "id": int,
  "club_id": int,
  "category_id": int,
  "title": string,
  "content": string,
  "status": "ACTIVE",
  "created_by": int,
  "created_by_name": string,
  "published_at": datetime (ISO 8601),
  "created_at": datetime (ISO 8601),
  "updated_at": datetime (ISO 8601),
  "category_name": string
}
```

#### ClubRegulationsResponse

**사용되는 엔드포인트:**

- [GET `/api/v1/clubs/{club_id}/regulations`](#4-클럽-clubs) - 전체 규정 조회

```json
{
  "categories": array[object],
  "total_categories": int
}
```

---

### 모임 통계 및 알림 (Meeting Statistics & Notifications)

#### MeetingStatsResponse

**사용되는 엔드포인트:**

- [GET `/api/v1/meetings/stats`](#5-모임-meetings) - 모임 통계 조회

```json
{
  "total_meetings": int,
  "active_meetings": int,
  "canceled_meetings": int,
  "completed_meetings": int,
  "meetings_by_type": object,
  "meetings_by_month": array[object],
  "total_participants": int,
  "average_participants_per_meeting": float,
  "meetings_by_club": array[object],
  "upcoming_meetings_count": int,
  "past_meetings_count": int
}
```

#### MeetingNotificationResponse

**notification_type**: `string` → enum: [NotificationType](#notificationtype)

**사용되는 엔드포인트:**

- [POST `/api/v1/meetings/{meeting_id}/notify`](#5-모임-meetings) - 모임 알림 전송

```json
{
  "notification_id": int,
  "title": string,
  "content": string,
  "notification_type": "GENERAL",
  "sent_to_count": int,
  "created_at": datetime (ISO 8601)
}
```

#### ParticipantResponse

**사용되는 엔드포인트:**

- [GET `/api/v1/meetings/{meeting_id}/settlement/available-participants`](#5-모임-meetings) - 정산 가능 참가자 조회

```json
{
  "id": int,
  "name": string,
  "email": string,
  "joined_at": datetime (ISO 8601),
  "is_guest": boolean
}
```

---

### 규정 버전 (Regulation Versions)

#### RegulationVersionResponse

**status**: `string` → enum: [RegulationStatus](#regulationstatus)

**사용되는 엔드포인트:**

- [GET `/api/v1/clubs/{club_id}/regulations/versions`](#4-클럽-clubs) - 규정 버전 목록 조회

```json
{
  "id": int,
  "uuid": string,
  "club_id": int,
  "title": string,
  "version": string,
  "content": string,
  "status": "ACTIVE",
  "created_by": int,
  "creator_name": string,
  "published_at": datetime (ISO 8601),
  "created_at": datetime (ISO 8601),
  "updated_at": datetime (ISO 8601)
}
```

---

### 관리자 대시보드 (Admin Dashboard)

#### ActivityResponse

**사용되는 엔드포인트:**

- [GET `/api/v1/admin/dashboard/activities`](#3-관리자-admin) - 대시보드 활동 조회

```json
{
  "id": string,
  "type": string,
  "title": string,
  "timestamp": datetime (ISO 8601)
}
```

#### RefundResponse

**payment_method**: `string` → enum: [PaymentMethod](#paymentmethod)

**사용되는 엔드포인트:**

- [GET `/api/v1/admin/refunds`](#3-관리자-admin) - 환불 목록 조회

```json
{
  "id": int,
  "user_id": int,
  "user_name": string,
  "user_email": string,
  "amount": float,
  "currency": string,
  "payment_method": "CARD",
  "order_name": string,
  "cancel_reason": string,
  "canceled_at": datetime (ISO 8601),
  "created_at": datetime (ISO 8601),
  "payment_key": string
}
```

---

### 스코어 (Scores)

#### ScoreCreate

**사용되는 엔드포인트:**

- [POST `/api/v1/scores/`](#5-모임-meetings) - 스코어 등록

```json
{
  "participant_id": int,
  "hole_number": int,
  "strokes": int,
  "par": int,
  "score_to_par": int
}
```

#### ScoreUpdate

**사용되는 엔드포인트:**

- [PUT `/api/v1/scores/{score_id}`](#5-모임-meetings) - 스코어 수정

```json
{
  "hole_number": int,
  "strokes": int,
  "par": int,
  "score_to_par": int
}
```

#### ScoreResponse

**사용되는 엔드포인트:**

- [POST `/api/v1/scores/`](#5-모임-meetings) - 스코어 등록
- [GET `/api/v1/scores/{score_id}`](#5-모임-meetings) - 스코어 상세 조회
- [PUT `/api/v1/scores/{score_id}`](#5-모임-meetings) - 스코어 수정

```json
{
  "id": int,
  "participant_id": int,
  "user_id": int,
  "user_name": string,
  "user_nickname": string,
  "meeting_id": int,
  "meeting_name": string,
  "hole_number": int,
  "strokes": int,
  "par": int,
  "score_to_par": int,
  "created_at": datetime (ISO 8601),
  "updated_at": datetime (ISO 8601)
}
```

#### ScoreListResponse

**사용되는 엔드포인트:**

- [GET `/api/v1/admin/scores`](#3-관리자-admin) - 스코어 목록 조회
- [GET `/api/v1/scores/`](#5-모임-meetings) - 스코어 목록 조회
- [GET `/api/v1/meetings/{meeting_id}/participants/{participant_id}/scores`](#5-모임-meetings) - 참가자 스코어 조회

```json
{
  "scores": array[object],
  "total": int,
  "page": int,
  "limit": int,
  "total_pages": int
}
```

#### SimpleScoreCreate

**사용되는 엔드포인트:**

- [POST `/api/v1/meetings/{meeting_id}/participants/{participant_id}/simple-score`](#5-모임-meetings) - 간단 스코어 등록
- [PUT `/api/v1/meetings/{meeting_id}/participants/{participant_id}/simple-score`](#5-모임-meetings) - 간단 스코어 수정

```json
{
  "total_score": int,
  "putts": int
}
```

또는

```json
{
  "gross_score": int
}
```

#### SimpleScoreResponse

**사용되는 엔드포인트:**

- [POST `/api/v1/meetings/{meeting_id}/participants/{participant_id}/simple-score`](#5-모임-meetings) - 간단 스코어 등록
- [PUT `/api/v1/meetings/{meeting_id}/participants/{participant_id}/simple-score`](#5-모임-meetings) - 간단 스코어 수정

```json
{
  "message": string,
  "score_history_id": int,
  "updated_handicap": float
}
```

#### ScoreStats

**사용되는 엔드포인트:**

- [GET `/api/v1/scores/stats/{participant_id}`](#5-모임-meetings) - 참가자 스코어 통계 조회
- [GET `/api/v1/meetings/{meeting_id}/participants/{participant_id}/scores/stats`](#5-모임-meetings) - 참가자 스코어 통계 조회

```json
{
  "total_strokes": int,
  "total_par": int,
  "total_score_to_par": int,
  "average_strokes": float,
  "average_par": float,
  "average_score_to_par": float,
  "best_hole": int,
  "worst_hole": int,
  "birdies": int,
  "pars": int,
  "bogeys": int,
  "double_bogeys": int,
  "triple_bogeys": int,
  "worse": int
}
```

---

### 정산 (Settlement)

#### SettlementResponse

**사용되는 엔드포인트:**

- [POST `/api/v1/meetings/{meeting_id}/settlement/rounding`](#5-모임-meetings) - 라운딩 정산
- [POST `/api/v1/meetings/{meeting_id}/settlement/social`](#5-모임-meetings) - 소셜 모임 정산
- [GET `/api/v1/meetings/{meeting_id}/settlement`](#5-모임-meetings) - 정산 정보 조회

```json
{
  "settlement": object
}
```

#### MySettlementResponse

**사용되는 엔드포인트:**

- [GET `/api/v1/meetings/{meeting_id}/settlement/my`](#5-모임-meetings) - 내 정산 정보 조회

```json
{
  "total_amount_due": int,
  "amount_paid": int,
  "remaining_amount": int,
  "is_paid": boolean,
  "items": array[object]
}
```

---

### 비용 (Expenses)

#### ExpenseCreate

**사용되는 엔드포인트:**

- [POST `/api/v1/meetings/{meeting_id}/expenses`](#5-모임-meetings) - 비용 생성

```json
{
  "name": string,
  "amount": int,
  "category": string,
  "notes": string
}
```

#### ExpenseUpdate

**사용되는 엔드포인트:**

- [PUT `/api/v1/meetings/{meeting_id}/expenses/{expense_id}`](#5-모임-meetings) - 비용 수정

```json
{
  "name": string,
  "amount": int,
  "category": string,
  "notes": string
}
```

#### ExpenseResponse

**사용되는 엔드포인트:**

- [POST `/api/v1/meetings/{meeting_id}/expenses`](#5-모임-meetings) - 비용 생성
- [GET `/api/v1/meetings/{meeting_id}/expenses/{expense_id}`](#5-모임-meetings) - 비용 상세 조회
- [PUT `/api/v1/meetings/{meeting_id}/expenses/{expense_id}`](#5-모임-meetings) - 비용 수정

```json
{
  "id": int,
  "meeting_id": int,
  "name": string,
  "amount": int,
  "category": string,
  "notes": string,
  "created_at": datetime (ISO 8601),
  "updated_at": datetime (ISO 8601)
}
```

#### ExpenseListResponse

**사용되는 엔드포인트:**

- [GET `/api/v1/meetings/{meeting_id}/expenses`](#5-모임-meetings) - 비용 목록 조회

```json
{
  "expenses": array[object],
  "total": int,
  "page": int,
  "limit": int,
  "total_pages": int
}
```

#### ExpenseParticipantResponse

**사용되는 엔드포인트:**

- [GET `/api/v1/meetings/{meeting_id}/expenses/{expense_id}/participants`](#5-모임-meetings) - 비용 참가자 목록 조회
- [PUT `/api/v1/meetings/{meeting_id}/expenses/{expense_id}/participants/{participant_id}`](#5-모임-meetings) - 비용 참가자 수정

```json
{
  "id": int,
  "expense_id": int,
  "participant_id": int,
  "amount_paid": int,
  "user_name": string,
  "user_nickname": string,
  "created_at": datetime (ISO 8601),
  "updated_at": datetime (ISO 8601)
}
```

#### ExpenseParticipantUpdate

```json
{
  "amount_paid": int
}
```

---

### 요금제 (Plans)

#### PlanCreate

**type**: `string` → enum: [PlanType](#plantype)

**사용되는 엔드포인트:**

- [POST `/api/v1/admin/plans`](#3-관리자-admin) - 요금제 생성

```json
{
  "name": string,
  "description": string,
  "type": "BASIC",
  "price": int,
  "billing_cycle": string,
  "features": object,
  "max_clubs": int,
  "max_members_per_club": int,
  "max_meetings_per_month": int
}
```

#### PlanUpdate

**type**: `string` → enum: [PlanType](#plantype)

**사용되는 엔드포인트:**

- [PUT `/api/v1/admin/plans/{plan_id}`](#3-관리자-admin) - 요금제 수정

```json
{
  "name": string,
  "description": string,
  "type": "BASIC",
  "price": int,
  "billing_cycle": string,
  "max_meetings_per_month": int
}
```

#### PlanResponse

**type**: `string` → enum: [PlanType](#plantype)

**사용되는 엔드포인트:**

- [GET `/api/v1/admin/plans`](#3-관리자-admin) - 요금제 목록 조회
- [POST `/api/v1/admin/plans`](#3-관리자-admin) - 요금제 생성
- [PUT `/api/v1/admin/plans/{plan_id}`](#3-관리자-admin) - 요금제 수정
- [GET `/api/v1/plans/`](#12-요금제-plans) - 요금제 목록 조회
- [GET `/api/v1/plans/{plan_id}`](#12-요금제-plans) - 요금제 상세 조회

```json
{
  "id": int,
  "name": string,
  "description": string,
  "type": "BASIC",
  "price": int,
  "billing_cycle": string,
  "features": object,
  "max_clubs": int,
  "max_members_per_club": int,
  "max_meetings_per_month": int,
  "is_active": boolean,
  "created_at": datetime (ISO 8601),
  "updated_at": datetime (ISO 8601)
}
```

---

### 결제 수단 (Payment Methods)

#### PaymentMethodCreate

```json
{
  "method_type": string,
  "method_name": string,
  "masked_info": string,
  "is_default": boolean
}
```

#### PaymentMethodUpdate

**사용되는 엔드포인트:**

- [PUT `/api/v1/payment-methods/{method_id}`](#14-결제-수단-payment-methods) - 결제 수단 수정

```json
{
  "method_type": string,
  "method_name": string,
  "masked_info": string,
  "is_default": boolean
}
```

#### PaymentMethodResponse

**status**: `string` → enum: [PaymentMethodStatus](#paymentmethodstatus)

**사용되는 엔드포인트:**

- [GET `/api/v1/users/payment-methods`](#2-사용자-users) - 결제 수단 목록 조회
- [GET `/api/v1/payment-methods/`](#14-결제-수단-payment-methods) - 결제 수단 목록 조회
- [POST `/api/v1/payment-methods/`](#14-결제-수단-payment-methods) - 결제 수단 등록
- [PUT `/api/v1/payment-methods/{method_id}`](#14-결제-수단-payment-methods) - 결제 수단 수정

```json
{
  "id": int,
  "user_id": int,
  "method_type": string,
  "method_name": string,
  "masked_info": string,
  "is_default": boolean,
  "status": "ACTIVE",
  "created_at": datetime (ISO 8601),
  "updated_at": datetime (ISO 8601)
}
```

---

### 구독 (Subscriptions)

#### SubscriptionCreate

```json
{
  "plan_id": int,
  "start_date": datetime (ISO 8601)
}
```

#### SubscriptionUpdate

**status**: `string` → enum: [SubscriptionStatus](#subscriptionstatus)

**사용되는 엔드포인트:**

- [PUT `/api/v1/subscriptions/{subscription_id}`](#15-구독-subscriptions) - 구독 수정

```json
{
  "plan_id": int,
  "status": "ACTIVE",
  "end_date": datetime (ISO 8601)
}
```

#### SubscriptionResponse

**status**: `string` → enum: [SubscriptionStatus](#subscriptionstatus)

**사용되는 엔드포인트:**

- [GET `/api/v1/users/subscriptions`](#2-사용자-users) - 구독 내역 조회
- [GET `/api/v1/admin/subscriptions`](#3-관리자-admin) - 구독 목록 조회
- [GET `/api/v1/subscriptions/`](#15-구독-subscriptions) - 구독 목록 조회
- [POST `/api/v1/subscriptions/`](#15-구독-subscriptions) - 구독 생성
- [GET `/api/v1/subscriptions/{subscription_id}`](#15-구독-subscriptions) - 구독 상세 조회
- [PUT `/api/v1/subscriptions/{subscription_id}`](#15-구독-subscriptions) - 구독 수정
- [POST `/api/v1/subscriptions/{subscription_id}/renew`](#15-구독-subscriptions) - 구독 갱신

```json
{
  "id": int,
  "user_id": int,
  "plan_id": int,
  "plan_name": string,
  "status": "ACTIVE",
  "start_date": datetime (ISO 8601),
  "next_billing_date": datetime (ISO 8601),
  "end_date": null (optional),
  "created_at": datetime (ISO 8601),
  "updated_at": datetime (ISO 8601)
}
```

---

### 결제 (Payments)

#### PaymentResponse

```json
{
  "payment_key": string,
  "order_id": string,
  "order_name": string,
  "status": string,
  "requested_at": datetime (ISO 8601),
  "approved_at": datetime (ISO 8601),
  "total_amount": int,
  "method": string,
  "card": object,
  "virtual_account": null (optional)
}
```

#### PaymentConfirmRequest

```json
{
  "payment_key": string,
  "order_id": string
}
```

#### PaymentCancelRequest

```json
{
  "payment_key": string,
  "cancel_reason": string
}
```

---

## 📋 Enum 타입 정의

---

### ClubType

- `REGULAR`: 정기 클럽
- `IRREGULAR`: 비정기 클럽

**사용되는 스키마:** [ClubCreate](#clubcreate), [ClubResponse](#clubresponse)

### ClubStatus

- `ACTIVE`: 활성
- `INACTIVE`: 비활성

**사용되는 스키마:** [ClubResponse](#clubresponse)

### ClubRole

- `MEMBER`: 일반 멤버
- `MANAGER`: 매니저
- `LEADER`: 리더

**사용되는 스키마:** [ClubMemberAddRequest](#clubmemberaddrequest), [ClubMemberRoleUpdateRequest](#clubmemberroleupdaterequest), [ClubResponse](#clubresponse)

### BillingCycle

- `MONTHLY`: 월간
- `QUARTERLY`: 분기
- `YEARLY`: 연간

**사용되는 스키마:** [RegularFeeUpdate](#regularfeeupdate), [RegularFeeResponse](#regularfeeresponse)

### MembershipStatus

- `ACTIVE`: 활성
- `PENDING`: 대기 중
- `INACTIVE`: 비활성
- `SUSPENDED`: 정지
- `CANCELED`: 취소됨

**사용되는 스키마:** [ClubResponse](#clubresponse)

### RegulationStatus

- `ACTIVE`: 활성
- `INACTIVE`: 비활성
- `DRAFT`: 초안

**사용되는 스키마:** [ClubRegulationCreate](#clubregulationcreate), [ClubRegulationUpdate](#clubregulationupdate), [ClubRegulationResponse](#clubregulationresponse), [RegulationVersionResponse](#regulationversionresponse)

---

### MeetingType

- `ROUND`: 라운딩 모임
- `SOCIAL`: 소셜 모임

**사용되는 스키마:** [RoundingMeetingCreate](#roundingmeetingcreate), [MeetingResponse](#meetingresponse)

### MeetingSubtype

- `REGULAR`: 정기 모임
- `IRREGULAR`: 비정기 모임
- `ONE_TIME`: 일회성 모임

**사용되는 스키마:** [RoundingMeetingCreate](#roundingmeetingcreate), [MeetingResponse](#meetingresponse)

### MeetingStatus

- `SCHEDULED`: 예정됨
- `IN_PROGRESS`: 진행 중
- `COMPLETED`: 완료됨
- `CANCELED`: 취소됨

**사용되는 스키마:** [MeetingResponse](#meetingresponse)

### ParticipantType

- `USER`: 사용자
- `GUEST`: 게스트

**사용되는 스키마:** [MeetingParticipantResponse](#meetingparticipantresponse)

---

### SettlementMethod

- `EQUAL_SPLIT`: 균등 분할
- `INDIVIDUAL`: 개별 결제

**사용되는 스키마:** [RoundingMeetingCreate](#roundingmeetingcreate), [MeetingResponse](#meetingresponse)

### SocialSettlementMethod

- `EQUAL_SPLIT`: 균등 분할
- `TREASURER_PREPAID`: 회계 선불
- `CLUB_FUND`: 클럽 자금

**사용되는 스키마:** [SocialMeetingCreate](#socialmeetingcreate)

### TeamFormationMode

- `GENDER_SEPARATED_HANDICAP`: 성별 분리 + 핸디캡 기준
- `GENDER_SEPARATED_PREVIOUS_RECORD`: 성별 분리 + 직전대회 성적 기준
- `GENDER_SEPARATED_RANDOM`: 성별 분리 + 랜덤
- `GENDER_MIXED_HANDICAP`: 성별 혼합 + 핸디캡 기준
- `GENDER_MIXED_PREVIOUS_RECORD`: 성별 혼합 + 직전대회 성적 기준
- `GENDER_MIXED_RANDOM`: 성별 혼합 + 랜덤

**사용되는 스키마:** [RoundingMeetingCreate](#roundingmeetingcreate), [MeetingResponse](#meetingresponse), [TeamCreate](#teamcreate), [TeamResponse](#teamresponse), [TeamFormationRequest](#teamformationrequest)

### TeamStatus

- `DRAFT`: 초안
- `CONFIRMED`: 확정됨
- `CANCELED`: 취소됨

**사용되는 스키마:** [TeamUpdate](#teamupdate), [TeamResponse](#teamresponse)

---

### UserStatus

- `ACTIVE`: 활성
- `DEACTIVATED`: 비활성화됨
- `DELETED`: 삭제됨

**사용되는 스키마:** [UserCreate](#usercreate), [UserResponse](#userresponse)

### UserRole

- `USER`: 일반 사용자
- `ADMIN`: 관리자

**사용되는 스키마:** (현재 사용되지 않음)

### Provider

- `LOCAL`: 로컬 (이메일 가입)
- `GOOGLE`: Google
- `KAKAO`: 카카오
- `NAVER`: 네이버

**사용되는 스키마:** [UserResponse](#userresponse)

---

### PlanType

- `BASIC`: 기본
- `PREMIUM`: 프리미엄
- `ENTERPRISE`: 엔터프라이즈

**사용되는 스키마:** [PlanCreate](#plancreate), [PlanUpdate](#planupdate), [PlanResponse](#planresponse)

### PaymentStatus

- `SUCCEEDED`: 성공
- `PENDING`: 대기 중
- `FAILED`: 실패

**사용되는 스키마:** (현재 사용되지 않음)

### PaymentMethod

- `CARD`: 카드
- `VIRTUAL_ACCOUNT`: 가상계좌
- `TRANSFER`: 계좌이체

**사용되는 스키마:** [RefundResponse](#refundresponse)

### PaymentMethodStatus

- `ACTIVE`: 활성
- `INACTIVE`: 비활성
- `DELETED`: 삭제됨

**사용되는 스키마:** [PaymentMethodResponse](#paymentmethodresponse)

### SubscriptionStatus

- `ACTIVE`: 활성
- `CANCELED`: 취소됨
- `PAST_DUE`: 연체

**사용되는 스키마:** [SubscriptionUpdate](#subscriptionupdate), [SubscriptionResponse](#subscriptionresponse)

---

### NoticeType

- `GENERAL`: 일반
- `SYSTEM`: 시스템
- `EVENT`: 이벤트
- `MAINTENANCE`: 점검

**사용되는 스키마:** [NoticeCreate](#noticecreate), [NoticeResponse](#noticeresponse)

### InquiryType

- `GENERAL`: 일반
- `TECHNICAL`: 기술
- `BILLING`: 결제
- `FEATURE_REQUEST`: 기능 요청
- `BUG_REPORT`: 버그 신고

**사용되는 스키마:** [InquiryCreate](#inquirycreate), [InquiryResponse](#inquiryresponse)

### InquiryStatus

- `SUBMITTED`: 제출됨
- `IN_PROGRESS`: 진행 중
- `RESOLVED`: 해결됨

**사용되는 스키마:** [InquiryUpdate](#inquiryupdate), [InquiryResponse](#inquiryresponse)

### TermsType

- `SERVICE`: 서비스 이용약관
- `PRIVACY`: 개인정보 처리방침
- `MARKETING`: 마케팅 수신 동의

**사용되는 스키마:** [TermsCreate](#termscreate), [TermsUpdate](#termsupdate), [TermsResponse](#termsresponse)

---

### NotificationType

- `MEETING_CANCELLATION`: 모임 취소
- `MEETING_SETTLEMENT_COMPLETED`: 모임 정산 완료
- `MEETING_COMPLETED`: 모임 완료
- `MEETING_REMINDER`: 모임 리마인더
- `PAYMENT_RECEIVED`: 결제 완료
- `CLUB_INVITATION`: 클럽 초대
- `GENERAL`: 일반
- `SYSTEM`: 시스템
- `OTHER`: 기타
- `NEW_NOTICE`: 새 공지사항
- `CLUB_MEMBERSHIP_APPROVED`: 클럽 멤버십 승인
- `CLUB_MEMBERSHIP_REJECTED`: 클럽 멤버십 거부
- `CLUB_MEMBERSHIP_REQUEST`: 클럽 멤버십 요청
- `TEAM_FORMATION_COMPLETED`: 팀 편성 완료
- `SOCIAL_SETTLEMENT_COMPLETED`: 소셜 모임 정산 완료

**사용되는 스키마:** [NotificationResponse](#notificationresponse), [MeetingNotificationResponse](#meetingnotificationresponse)

### NotificationStatus

- `UNREAD`: 읽지 않음
- `READ`: 읽음
- `ARCHIVED`: 보관됨

**사용되는 스키마:** [NotificationResponse](#notificationresponse)
