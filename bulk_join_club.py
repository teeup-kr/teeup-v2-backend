#!/usr/bin/env python3
"""
user id 4~103 사용자를 club_id=1 클럽에 일괄 가입시키는 스크립트
- 이미 가입된 사용자는 스킵
- 신규 가입만 ACTIVE 상태로 추가 후 club.member_count 갱신
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.orm import Session
from database import SessionLocal
from models import User, Club, ClubMembership
from models.enums import ClubRole, MembershipStatus

CLUB_ID = 1
USER_ID_MIN = 4
USER_ID_MAX = 103


def bulk_join_club(db: Session) -> tuple[int, int]:
    """user_id 4~103 사용자를 club_id=1에 가입시킴. (추가된 수, 스킵된 수) 반환."""
    club = db.query(Club).filter(Club.id == CLUB_ID).first()
    if not club:
        print(f"[오류] club_id={CLUB_ID} 인 클럽이 없습니다.")
        return 0, 0

    users = (
        db.query(User)
        .filter(User.id >= USER_ID_MIN, User.id <= USER_ID_MAX)
        .all()
    )
    if not users:
        print(f"[안내] user_id {USER_ID_MIN}~{USER_ID_MAX} 에 해당하는 사용자가 없습니다.")
        return 0, 0

    existing = (
        db.query(ClubMembership.user_id)
        .filter(
            ClubMembership.club_id == CLUB_ID,
            ClubMembership.user_id >= USER_ID_MIN,
            ClubMembership.user_id <= USER_ID_MAX,
        )
        .all()
    )
    existing_ids = {r.user_id for r in existing}
    user_ids = [u.id for u in users]
    to_add = [uid for uid in user_ids if uid not in existing_ids]
    skip_count = len(user_ids) - len(to_add)

    for user_id in to_add:
        db.add(
            ClubMembership(
                club_id=CLUB_ID,
                user_id=user_id,
                role=ClubRole.MEMBER,
                status=MembershipStatus.ACTIVE,
            )
        )

    if to_add:
        current_count = (
            db.query(ClubMembership)
            .filter(
                ClubMembership.club_id == CLUB_ID,
                ClubMembership.status == MembershipStatus.ACTIVE,
            )
            .count()
        )
        club.member_count = current_count

    db.commit()
    return len(to_add), skip_count


def main() -> int:
    db: Session = SessionLocal()
    try:
        print("=" * 50)
        print(f"클럽 ID={CLUB_ID} 에 user_id {USER_ID_MIN}~{USER_ID_MAX} 일괄 가입")
        print("=" * 50)
        added, skipped = bulk_join_club(db)
        print(f"추가: {added}명, 이미 가입으로 스킵: {skipped}명")
        print("=" * 50)
        return 0
    except Exception as e:
        db.rollback()
        print(f"오류: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    exit(main())
