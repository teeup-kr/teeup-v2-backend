#!/usr/bin/env python3
"""
라운딩(meeting_id)에 팀 편성 검증용 mock 게스트 30명을 일괄 추가하는 스크립트.
docs/mock-users-guide.md §9 명단(테스트유저1~30, 성별·핸디캡)을 게스트로 등록합니다.
"""

import argparse
import sys
import os
from decimal import Decimal

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.orm import Session
from database import SessionLocal
from models import Meeting
from models.enums import Gender, MeetingType
from utils.team_formation import add_guest_to_meeting

# docs/mock-users-guide.md §4·§9: 인원 1~10 남, 11~20 여, 21~30 남 / 핸디캡 0,2,...,18, 20,...,38, 40,...,58
GUEST_LIST = [
    ("테스트유저1", Gender.MALE, 0),
    ("테스트유저2", Gender.MALE, 2),
    ("테스트유저3", Gender.MALE, 4),
    ("테스트유저4", Gender.MALE, 6),
    ("테스트유저5", Gender.MALE, 8),
    ("테스트유저6", Gender.MALE, 10),
    ("테스트유저7", Gender.MALE, 12),
    ("테스트유저8", Gender.MALE, 14),
    ("테스트유저9", Gender.MALE, 16),
    ("테스트유저10", Gender.MALE, 18),
    ("테스트유저11", Gender.FEMALE, 20),
    ("테스트유저12", Gender.FEMALE, 22),
    ("테스트유저13", Gender.FEMALE, 24),
    ("테스트유저14", Gender.FEMALE, 26),
    ("테스트유저15", Gender.FEMALE, 28),
    ("테스트유저16", Gender.FEMALE, 30),
    ("테스트유저17", Gender.FEMALE, 32),
    ("테스트유저18", Gender.FEMALE, 34),
    ("테스트유저19", Gender.FEMALE, 36),
    ("테스트유저20", Gender.FEMALE, 38),
    ("테스트유저21", Gender.MALE, 40),
    ("테스트유저22", Gender.MALE, 42),
    ("테스트유저23", Gender.MALE, 44),
    ("테스트유저24", Gender.MALE, 46),
    ("테스트유저25", Gender.MALE, 48),
    ("테스트유저26", Gender.MALE, 50),
    ("테스트유저27", Gender.MALE, 52),
    ("테스트유저28", Gender.MALE, 54),
    ("테스트유저29", Gender.MALE, 56),
    ("테스트유저30", Gender.MALE, 58),
]


def add_guests_to_rounding(meeting_id: int, db: Session) -> int:
    """라운딩 meeting_id에 GUEST_LIST 30명을 게스트로 추가. 추가된 인원 수 반환."""
    meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
    if not meeting:
        print(f"[오류] meeting_id={meeting_id} 인 모임이 없습니다.")
        return 0
    if meeting.meeting_type != MeetingType.ROUND:
        print(f"[오류] meeting_id={meeting_id} 는 라운딩이 아닙니다. (meeting_type={meeting.meeting_type})")
        return 0

    from models import MeetingParticipant
    current_count = db.query(MeetingParticipant).filter(
        MeetingParticipant.meeting_id == meeting_id
    ).count()
    if meeting.max_participants is not None and current_count + len(GUEST_LIST) > meeting.max_participants:
        print(f"[오류] 정원 초과: 현재 {current_count}명 + {len(GUEST_LIST)}명 > max_participants={meeting.max_participants}")
        return 0

    added = 0
    for name, gender, handicap in GUEST_LIST:
        add_guest_to_meeting(
            meeting_id=meeting_id,
            guest_name=name,
            guest_handicap=Decimal(handicap),
            guest_gender=gender,
            guest_birthdate=None,
            db=db,
        )
        added += 1
    return added


def main() -> int:
    parser = argparse.ArgumentParser(description="라운딩에 mock 게스트 30명 일괄 추가 (팀 편성 검증용)")
    parser.add_argument("--meeting-id", type=int, default=1, help="라운딩 모임 ID (기본: 1)")
    args = parser.parse_args()
    meeting_id = args.meeting_id

    db: Session = SessionLocal()
    try:
        print("=" * 50)
        print(f"라운딩 meeting_id={meeting_id} 에 게스트 30명 일괄 추가")
        print("=" * 50)
        added = add_guests_to_rounding(meeting_id, db)
        if added:
            print(f"라운딩 meeting_id={meeting_id} 에 {added}명 게스트 추가 완료.")
        print("=" * 50)
        return 0 if added else 1
    except Exception as e:
        db.rollback()
        print(f"오류: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
