# 팀 편성 검증용 Mock 사용자 생성 가이드

## 1. 목적 및 전제

이 문서는 **팀 편성 48케이스 검증**을 위해 필요한 mock 사용자를 DB 구조에 맞게 어떻게 만들고, 몇 명을 만들며, 성별·평균타수·핸디캡 등 **어떤 회원 정보를 어떻게 넣어야 하는지**를 정리한 가이드입니다.

- **전제**: Google 계정 없이 `Provider.LOCAL` 사용자만으로 검증합니다.
- **관련 문서**: [team-formation-final.md](team-formation-final.md) — 48케이스 실행 절차 및 모임/참가자 배정 흐름.

---

## 2. 인원 수: 30명

| 항목 | 내용 |
|------|------|
| **필요 인원** | **30명** |
| **이유** | 단일 모임 최대 인원이 20명(케이스 47·48)이며, 성별 분리 모드에서 최대 **남 10명 / 여 10명**이 필요합니다. 따라서 남성 ≥10명, 여성 ≥10명이 있어야 합니다. |
| **재사용** | 48개 모임은 동일 클럽·동일 사용자 풀에서 **참가자만 다르게 배정**하면 되므로, 한 번 만든 30명을 여러 모임에 재사용합니다. (한 사람이 여러 모임에 참가 가능) |

---

## 3. DB 구조 반영 — User 테이블 필드

`models/user.py`의 **users** 테이블 기준으로, mock 생성 시 **반드시 채워야 할 필드**와 **팀 편성/클럽 가입에 쓰이는 필드**를 정리했습니다.

### 3.1 필드 일람표

| 분류 | 필드 | 타입/제약 | 권장값 또는 설명 |
|------|------|-----------|------------------|
| **식별/로그인** | email | unique | `user1@teeup.run` ~ `user30@teeup.run` |
| | nickname | unique | 예: `테스트유저1` ~ `테스트유저30` 또는 이름 풀 재사용 |
| | password | String(255) | `hashlib.sha256("test1234".encode()).hexdigest()` (6자 이상) |
| | provider | Enum | `Provider.LOCAL` |
| | provider_id | String(255) | NULL |
| **프로필(클럽/편성)** | realname | String(255) | 이름 풀 또는 `유저1` 등 |
| | phone_number | unique | 30명 각각 상이 (예: `010-1000-0001` ~ `010-1000-0030`) |
| | gender | Enum(Gender) | 팀 편성 성별 분리·클럽 가입에 **필수**. 아래 §4 성별 배분 참고 |
| | birthdate | DateTime | 임의 유효 날짜 (예: 1980년대~2000년대) |
| **핸디캡/타수** | average_score | Integer, 55~144 | 다양하게 분포 (예: 68~140). 팀 편성 HANDICAP/PREVIOUS_RECORD에 사용 |
| | average_score_init | Integer | average_score와 동일 권장 |
| | handicap_init | DECIMAL(4,1), 0~72 | `calculate_handicap_from_average_score(average_score)` 결과 사용 (`utils/handicap_calculator.py`) |
| | handicap | DECIMAL(4,1) | 경기 기록 없으면 편성 시 `handicap_init` 사용. mock은 handicap_init과 동일하게 설정 가능 |
| | handicap_update_method | Enum | `HandicapUpdateMethod.MANUAL` |
| | handicap_calculation_count | Integer | 0 |
| **기타** | status | Enum | `UserStatus.ACTIVE` |
| | terms_agreement | Boolean | True (필수 약관 동의) |
| | privacy_policy | Boolean | True (필수 약관 동의) |
| | privacy_collection | Boolean | True (필수 약관 동의) |
| | marketing_consent | Boolean | 선택 (True/False 혼합 가능) |

### 3.2 팀 편성 로직과의 관계

- **핸디캡**: 팀 편성 시 참가자별 핸디캡은 `utils/handicap_calculator.py`의 `get_user_handicap_for_formation(db, user_id)`로 조회됩니다. 경기 기록이 없으면 `handicap_init`(또는 `handicap`)을 사용합니다.
- **성별**: 성별 분리 모드(`GENDER_SEPARATED_*`)에서는 `utils/team_formation.py`가 User의 `gender`를 사용해 남/여를 분리합니다. 클럽 가입 시에도 성별이 필수로 요구될 수 있습니다.

---

## 4. 성별 배분

| 구분 | 인원 | 비고 |
|------|------|------|
| **최소** | 남성 10명, 여성 10명 | 성별 분리 20명 모임(남10/여10) 대비 |
| **권장** | 남 약 18명, 여 약 12명 | 다양한 “성별 분리 시 남/여” 케이스 커버 |

### 4.1 배분 예시

- **user1~10**: 남성 (MALE)
- **user11~20**: 여성 (FEMALE)
- **user21~30**: 남성 (MALE)

→ 남 20명, 여 10명. 필요 시 user21~24를 여성으로 바꿔 남 16명/여 14명 등으로 조정 가능합니다.

---

## 5. 평균타수·핸디캡

| 항목 | 범위/규칙 | 비고 |
|------|-----------|------|
| **average_score** | 55~144 (Integer) | 팀 편성에서 편차가 나도록 다양한 값 분포 권장 (예: 68~140, 72~100 등) |
| **핸디캡 계산** | `handicap = average_score - 72`, 0~72로 클램프 | `utils/handicap_calculator.py`의 `calculate_handicap_from_average_score(average_score)` 사용 권장 |
| **mock 사용자** | 경기 기록 없음 | `get_user_handicap_for_formation()`는 `handicap_init`(또는 `handicap`)을 반환합니다. 두 필드를 동일하게 넣어 두면 됩니다. |

---

## 6. 스크립트 작성 시 유의사항

- **비밀번호**: 일반 회원(LOCAL)은 `services/user_admin_service.py`와 동일하게 `hashlib.sha256(plain_password.encode()).hexdigest()`로 저장합니다.
- **핸디캡**: `utils.handicap_calculator.calculate_handicap_from_average_score(average_score)`를 사용해 `handicap_init`·`handicap`을 설정합니다.
- **unique 제약**: `email`, `nickname`, `phone_number`는 30명 모두 서로 다르게 설정합니다.
- **스크립트 위치**: 현재 저장소에는 `create_test_users.py`가 없습니다. 스크립트는 프로젝트 루트 또는 `scripts/` 하위에 두고, DB 세션·import 경로는 기존 [scripts/mock_init/mock.py](scripts/mock_init/mock.py) 또는 [bulk_join_club.py](bulk_join_club.py)와 동일하게 맞추면 됩니다.

---

## 7. 클럽 가입 및 PREVIOUS_RECORD(선택)

- **클럽 가입**: mock 사용자 생성 후, 테스트용 클럽 1개에 30명 전원을 가입시켜야 합니다. [bulk_join_club.py](bulk_join_club.py) 또는 동일 목적 스크립트를 활용합니다. (자세한 순서는 [team-formation-final.md](team-formation-final.md) §4.2 참고)
- **PREVIOUS_RECORD 모드**: 직전 대회 성적 기준 편성 케이스를 검증하려면 [team-formation-final.md](team-formation-final.md) §5처럼 **MeetingResult** 시드를 user별로 넣는 단계가 선택 사항입니다. 시드가 없어도 편성 API는 동작하며, 기록 없는 참가자는 net_score 999.0으로 마지막에 배치되는 동작만 확인할 수 있습니다.

---

## 8. 참고

| 항목 | 경로 |
|------|------|
| 팀 편성 48케이스 실행 가이드 | [docs/team-formation-final.md](team-formation-final.md) |
| User 모델 | [models/user.py](../models/user.py) |
| 핸디캡 계산 | [utils/handicap_calculator.py](../utils/handicap_calculator.py) |
| 팀 편성 로직 | [utils/team_formation.py](../utils/team_formation.py) |
| 클럽 일괄 가입 예시 | [bulk_join_club.py](../bulk_join_club.py) |
| Mock 시드 예시 | [scripts/mock_init/mock.py](../scripts/mock_init/mock.py) |

---

## 9. 게스트/회원 한꺼번에 추가용 명단 (인원 번호 · 이름 · 성별 · 핸디캡)

아래 표를 복사해 게스트 추가·회원 배정 등에 그대로 사용할 수 있습니다. 성별·핸디캡은 §4·§5 배분에 맞춰 두었습니다.

| 인원 번호 | 이름 | 성별 | 핸디캡 |
|----------|------|------|--------|
| 1 | 테스트유저1 | 남 | 0 |
| 2 | 테스트유저2 | 남 | 2 |
| 3 | 테스트유저3 | 남 | 4 |
| 4 | 테스트유저4 | 남 | 6 |
| 5 | 테스트유저5 | 남 | 8 |
| 6 | 테스트유저6 | 남 | 10 |
| 7 | 테스트유저7 | 남 | 12 |
| 8 | 테스트유저8 | 남 | 14 |
| 9 | 테스트유저9 | 남 | 16 |
| 10 | 테스트유저10 | 남 | 18 |
| 11 | 테스트유저11 | 여 | 20 |
| 12 | 테스트유저12 | 여 | 22 |
| 13 | 테스트유저13 | 여 | 24 |
| 14 | 테스트유저14 | 여 | 26 |
| 15 | 테스트유저15 | 여 | 28 |
| 16 | 테스트유저16 | 여 | 30 |
| 17 | 테스트유저17 | 여 | 32 |
| 18 | 테스트유저18 | 여 | 34 |
| 19 | 테스트유저19 | 여 | 36 |
| 20 | 테스트유저20 | 여 | 38 |
| 21 | 테스트유저21 | 남 | 40 |
| 22 | 테스트유저22 | 남 | 42 |
| 23 | 테스트유저23 | 남 | 44 |
| 24 | 테스트유저24 | 남 | 46 |
| 25 | 테스트유저25 | 남 | 48 |
| 26 | 테스트유저26 | 남 | 50 |
| 27 | 테스트유저27 | 남 | 52 |
| 28 | 테스트유저28 | 남 | 54 |
| 29 | 테스트유저29 | 남 | 56 |
| 30 | 테스트유저30 | 남 | 58 |
