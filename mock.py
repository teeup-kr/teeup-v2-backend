#!/usr/bin/env python3
"""Seed mock data for users, clubs, meetings, and participants.

Constraints from product request:
- No admin creation
- No explicit marker prefix (e.g. MOCK_)
- Total users are seeded up to 100 from name.txt
- Club memberships are around 20 users per club (duplicate users across clubs allowed)
- Meeting participants are always between 12 and 20
- User names are sourced from name.txt
"""

from __future__ import annotations

import argparse
import random
from datetime import datetime, timedelta
from pathlib import Path

from sqlalchemy.orm import Session

from database import SessionLocal
from create_default_terms import create_default_terms
from utils.handicap_calculator import calculate_handicap_from_average_score
from models import (
    Club,
    ClubMembership,
    ClubRole,
    ClubStatus,
    ClubType,
    Gender,
    Meeting,
    MeetingSubtype,
    MeetingType,
    MeetingParticipant,
    MembershipStatus,
    ParticipantType,
    Provider,
    SettlementMethod,
    Sido,
    SocialType,
    User,
    UserStatus,
)
from utils.region import fetch_all_regions, sync_regions

CLUB_NAME_POOL = [
    "Sunrise Golf Club",
    "River Green Club",
    "Pine Valley Club",
    "Blue Lake Club",
    "Hill Crest Club",
    "City Fairway Club",
    "Ocean Breeze Club",
    "Royal Tee Club",
]

# Change these constants directly when you want a different fixed leader/club.
DEFAULT_USER_COUNT = 100
DEFAULT_MEMBERS_PER_CLUB = 20
MEETING_MIN_PARTICIPANTS = 12
MEETING_MAX_PARTICIPANTS = 20
FIXED_LEADER_USER_ID = 1
FIXED_LEADER_CLUB_INDEX = 0


def refresh_regions_once(db: Session) -> bool:
    active_sido = db.query(Sido).filter(Sido.is_active.is_(True)).first()
    if active_sido:
        return False

    regions = fetch_all_regions()
    result = sync_regions(db, regions)
    print(f"Region list synchronized: fetched={len(regions)}, synced={result}")
    return True


def seed_default_terms(db: Session) -> tuple[int, int]:
    created, updated = create_default_terms(db)
    print(f"Default terms: created={created}, existing={updated}")
    return created, updated


def load_names(path: Path) -> list[str]:
    if not path.exists():
        raise FileNotFoundError(f"Name file not found: {path}")

    names = [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not names:
        raise ValueError(f"No names found in {path}")
    return names


def chunked_rotation(values: list[int], offset: int, size: int) -> list[int]:
    if not values:
        return []
    rotated = values[offset % len(values):] + values[:offset % len(values)]
    return rotated[:size]


def upsert_users(db: Session, names: list[str], target_count: int,
                 rng: random.Random) -> tuple[list[User], dict[str, int]]:
    counters = {"created": 0, "skipped": 0}
    users: list[User] = []

    for i in range(target_count):
        name = names[i % len(names)]
        cycle = i // len(names)

        email = f"user{i + 1:03d}@teeuplink.com"
        nickname = name if cycle == 0 else f"{name}{cycle + 1}"

        existing = db.query(User).filter(User.email == email).first()
        if existing:
            users.append(existing)
            counters["skipped"] += 1
            continue

        average_score = 82 + (i % 12)
        handicap = calculate_handicap_from_average_score(average_score)

        user = User(
            email=email,
            nickname=nickname,
            realname=name,
            provider=Provider.LOCAL,
            status=UserStatus.ACTIVE,
            gender=rng.choice([Gender.MALE, Gender.FEMALE]),
            birthdate=datetime(1980 + (i % 20), (i % 12) + 1, ((i % 28) + 1)),
            average_score_init=average_score,
            average_score=average_score,
            handicap_init=handicap,
            handicap=handicap,
            terms_agreement=True,
            privacy_policy=True,
            privacy_collection=True,
            marketing_consent=bool(i % 2),
        )
        db.add(user)
        db.flush()

        users.append(user)
        counters["created"] += 1

    db.commit()
    return users, counters


def upsert_clubs(db: Session, users: list[User], target_count: int) -> tuple[list[Club], dict[str, int]]:
    counters = {"created": 0, "skipped": 0}

    sido_codes = [s.code for s in db.query(Sido).filter(Sido.is_active.is_(True)).order_by(Sido.code).all()]
    if not sido_codes:
        raise RuntimeError("No active sido found. Seed region data first.")

    clubs: list[Club] = []
    for i in range(target_count):
        club_name = CLUB_NAME_POOL[i % len(CLUB_NAME_POOL)]
        sido_code = sido_codes[i % len(sido_codes)]

        existing = (db.query(Club).filter(Club.name == club_name, Club.sido_code == sido_code,
                                          Club.deleted_at.is_(None)).first())
        if existing:
            clubs.append(existing)
            counters["skipped"] += 1
            continue

        representative = users[i % len(users)]
        club = Club(
            name=club_name,
            display_id=f"club{i + 1:03d}",
            sido_code=sido_code,
            type=ClubType.REGULAR if i % 2 == 0 else ClubType.IRREGULAR,
            description=f"{club_name} members community",
            representative_name=representative.realname,
            location=f"Area {i + 1}",
            contact_info=f"010-1000-{1000 + i}",
            status=ClubStatus.ACTIVE,
        )
        db.add(club)
        db.flush()

        clubs.append(club)
        counters["created"] += 1

    db.commit()
    return clubs, counters


def upsert_memberships(
    db: Session,
    users: list[User],
    clubs: list[Club],
    members_per_club: int,
    fixed_leader_user_id: int,
    fixed_leader_club_index: int,
) -> dict[str, int]:
    counters = {"created": 0, "updated": 0, "skipped": 0}

    user_ids = [u.id for u in users]
    if len(user_ids) < 4:
        raise RuntimeError("At least 4 users are required to seed memberships.")

    for idx, club in enumerate(clubs):
        size = min(max(MEETING_MAX_PARTICIPANTS, members_per_club), len(user_ids))
        selected = chunked_rotation(user_ids, offset=idx * 3, size=size)

        if idx == fixed_leader_club_index and fixed_leader_user_id in user_ids:
            if fixed_leader_user_id in selected:
                selected.remove(fixed_leader_user_id)
            elif len(selected) >= size:
                selected = selected[:-1]
            selected.insert(0, fixed_leader_user_id)

        leader_id = fixed_leader_user_id if idx == fixed_leader_club_index and fixed_leader_user_id in selected else selected[
            0]
        manager_id = next((uid for uid in selected if uid != leader_id), None)

        for user_id in selected:
            role = ClubRole.MEMBER
            if user_id == leader_id:
                role = ClubRole.LEADER
            elif manager_id is not None and user_id == manager_id:
                role = ClubRole.MANAGER

            desired_status = MembershipStatus.ACTIVE

            membership = (db.query(ClubMembership).filter(ClubMembership.club_id == club.id,
                                                          ClubMembership.user_id == user_id).first())
            if membership:
                changed = False
                if membership.role != role:
                    membership.role = role
                    changed = True
                if membership.status != desired_status:
                    membership.status = desired_status
                    changed = True
                if changed:
                    counters["updated"] += 1
                else:
                    counters["skipped"] += 1
                continue

            db.add(ClubMembership(
                club_id=club.id,
                user_id=user_id,
                role=role,
                status=desired_status,
            ))
            counters["created"] += 1

        # Keep exactly one leader role in each seeded club.
        other_leaders = (db.query(ClubMembership).filter(
            ClubMembership.club_id == club.id,
            ClubMembership.role == ClubRole.LEADER,
            ClubMembership.user_id != leader_id,
        ).all())
        for other in other_leaders:
            other.role = ClubRole.MEMBER
            if other.status != MembershipStatus.ACTIVE:
                other.status = MembershipStatus.ACTIVE
            counters["updated"] += 1

        # Keep active member count around members_per_club by pushing extra members to PENDING.
        non_selected_memberships = (db.query(ClubMembership).filter(
            ClubMembership.club_id == club.id,
            ClubMembership.user_id.notin_(selected),
            ClubMembership.status == MembershipStatus.ACTIVE,
        ).all())
        for membership in non_selected_memberships:
            membership.status = MembershipStatus.PENDING
            if membership.role in (ClubRole.LEADER, ClubRole.MANAGER):
                membership.role = ClubRole.MEMBER
            counters["updated"] += 1

        club.member_count = (db.query(ClubMembership).filter(ClubMembership.club_id == club.id,
                                                             ClubMembership.status == MembershipStatus.ACTIVE).count())

    db.commit()
    return counters


def ensure_user_one_memberships(db: Session, clubs: list[Club], user_id: int) -> dict[str, int]:
    counters = {"created": 0, "updated": 0, "skipped": 0}
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return counters

    role_cycle = [ClubRole.LEADER, ClubRole.MANAGER, ClubRole.MEMBER]

    for idx, club in enumerate(clubs):
        desired_role = role_cycle[idx % len(role_cycle)]
        membership = (db.query(ClubMembership).filter(
            ClubMembership.club_id == club.id,
            ClubMembership.user_id == user_id,
        ).first())

        if membership:
            changed = False
            if membership.role != desired_role:
                membership.role = desired_role
                changed = True
            if membership.status != MembershipStatus.ACTIVE:
                membership.status = MembershipStatus.ACTIVE
                changed = True
            if changed:
                counters["updated"] += 1
            else:
                counters["skipped"] += 1
        else:
            db.add(ClubMembership(
                club_id=club.id,
                user_id=user_id,
                role=desired_role,
                status=MembershipStatus.ACTIVE,
            ))
            counters["created"] += 1

        if desired_role == ClubRole.LEADER:
            other_leaders = (db.query(ClubMembership).filter(
                ClubMembership.club_id == club.id,
                ClubMembership.role == ClubRole.LEADER,
                ClubMembership.user_id != user_id,
            ).all())
            for other in other_leaders:
                other.role = ClubRole.MEMBER
                if other.status != MembershipStatus.ACTIVE:
                    other.status = MembershipStatus.ACTIVE
                counters["updated"] += 1

        club.member_count = (db.query(ClubMembership).filter(
            ClubMembership.club_id == club.id,
            ClubMembership.status == MembershipStatus.ACTIVE,
        ).count())

    db.commit()
    return counters


def choose_participant_count(available: int, rng: random.Random) -> int:
    if available < MEETING_MIN_PARTICIPANTS:
        return 0

    upper = min(MEETING_MAX_PARTICIPANTS, available)
    return rng.randint(MEETING_MIN_PARTICIPANTS, upper)


def upsert_meetings_and_participants(
    db: Session,
    clubs: list[Club],
    meetings_per_club: int,
    rng: random.Random,
    fixed_leader_user_id: int,
    fixed_leader_club_index: int,
    force_user_id: int | None = None,
) -> dict[str, int]:
    counters = {
        "meeting_created": 0,
        "meeting_skipped": 0,
        "participant_created": 0,
        "participant_skipped": 0,
    }

    base_time = datetime.now().replace(minute=0, second=0, microsecond=0)
    status_cycle = ["SCHEDULED", "IN_PROGRESS", "COMPLETED", "CANCELED"]

    for c_idx, club in enumerate(clubs):
        active_memberships = (db.query(ClubMembership).filter(
            ClubMembership.club_id == club.id,
            ClubMembership.status == MembershipStatus.ACTIVE).order_by(ClubMembership.id).all())
        active_user_ids = [m.user_id for m in active_memberships]

        if len(active_user_ids) < MEETING_MIN_PARTICIPANTS:
            continue

        leader_id = fixed_leader_user_id if c_idx == fixed_leader_club_index and fixed_leader_user_id in active_user_ids else None
        for m in active_memberships:
            if m.role == ClubRole.LEADER:
                leader_id = m.user_id
                break

        for m_idx in range(meetings_per_club):
            meeting_type = MeetingType.ROUND if m_idx % 4 != 3 else MeetingType.SOCIAL
            meeting_time = base_time + timedelta(days=(c_idx * meetings_per_club + m_idx))
            status_value = status_cycle[m_idx % len(status_cycle)]

            if meeting_type == MeetingType.ROUND:
                meeting_name = f"{club.name} Round {m_idx + 1}"
            else:
                meeting_name = f"{club.name} Social {m_idx + 1}"

            existing = (db.query(Meeting).filter(
                Meeting.club_id == club.id,
                Meeting.name == meeting_name,
                Meeting.meeting_time == meeting_time,
            ).first())

            participant_count = choose_participant_count(len(active_user_ids), rng)
            if participant_count < MEETING_MIN_PARTICIPANTS:
                continue

            if existing:
                meeting = existing
                if meeting.created_by != leader_id:
                    meeting.created_by = leader_id
                counters["meeting_skipped"] += 1
            else:
                tee_count = max(1, (participant_count + 3) // 4)
                tee_times = [f"{7 + i:02d}:00" for i in range(tee_count)]
                is_round = meeting_type == MeetingType.ROUND

                meeting = Meeting(
                    name=meeting_name,
                    description=f"Auto generated {meeting_type.value.lower()} meeting",
                    location=f"{club.name} course" if is_round else f"{club.name} lounge",
                    meeting_time=meeting_time,
                    tee_times=tee_times,
                    max_participants=participant_count,
                    meeting_type=meeting_type,
                    meeting_subtype=MeetingSubtype.REGULAR if is_round else None,
                    total_cost=120000 if is_round else None,
                    green_fee=80000 if is_round else None,
                    caddy_fee=30000 if is_round else None,
                    cart_fee=10000 if is_round else None,
                    settlement_method=SettlementMethod.EQUAL_SPLIT,
                    course_name=f"{club.name} Course" if is_round else None,
                    venue_name=f"{club.name} Lounge" if not is_round else None,
                    hole_count=18 if is_round else None,
                    social_cost=60000 if not is_round else None,
                    social_type=rng.choice([SocialType.CASUAL, SocialType.DINNER, SocialType.EVENT]) if not is_round else None,
                    reservation_name=club.representative_name,
                    club_id=club.id,
                    status=status_value,
                    application_deadline=meeting_time - timedelta(days=2),
                    created_by=leader_id,
                )
                db.add(meeting)
                db.flush()
                counters["meeting_created"] += 1

            selected_ids = chunked_rotation(active_user_ids, offset=m_idx * 2, size=participant_count)
            if leader_id and leader_id in active_user_ids and leader_id not in selected_ids:
                selected_ids[-1] = leader_id

            if force_user_id and force_user_id in active_user_ids and force_user_id not in selected_ids:
                for i in range(len(selected_ids) - 1, -1, -1):
                    if selected_ids[i] != leader_id:
                        selected_ids[i] = force_user_id
                        break

            for idx, user_id in enumerate(selected_ids):
                participant = (db.query(MeetingParticipant).filter(
                    MeetingParticipant.meeting_id == meeting.id,
                    MeetingParticipant.user_id == user_id,
                ).first())
                if participant:
                    counters["participant_skipped"] += 1
                    continue

                db.add(
                    MeetingParticipant(
                        meeting_id=meeting.id,
                        user_id=user_id,
                        participant_type=ParticipantType.USER,
                        handicap=10 + (idx % 15),
                        average_score=80 + (idx % 10),
                        is_newbie=bool(idx % 5 == 0),
                    ))
                counters["participant_created"] += 1

    db.commit()
    return counters


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Seed users, clubs, meetings, and participants.")
    parser.add_argument("--name-file", default="name.txt", help="Path to source names file")
    parser.add_argument("--users", type=int, default=DEFAULT_USER_COUNT, help="Number of users to seed")
    parser.add_argument("--clubs", type=int, default=6, help="Number of clubs to seed")
    parser.add_argument("--meetings-per-club", type=int, default=6, help="Meetings per club")
    parser.add_argument("--members-per-club", type=int, default=DEFAULT_MEMBERS_PER_CLUB, help="Members per club")
    parser.add_argument("--seed", type=int, default=20260203, help="Random seed")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rng = random.Random(args.seed)

    name_path = Path(args.name_file)
    names = load_names(name_path)

    with SessionLocal() as db:
        refresh_regions_once(db)
        seed_default_terms(db)
        users, user_counts = upsert_users(db, names, args.users, rng)
        clubs, club_counts = upsert_clubs(db, users, args.clubs)
        membership_counts = upsert_memberships(
            db,
            users,
            clubs,
            args.members_per_club,
            FIXED_LEADER_USER_ID,
            FIXED_LEADER_CLUB_INDEX,
        )
        user_one = db.query(User).filter(User.id == FIXED_LEADER_USER_ID).first()
        user_one_membership_counts = {"created": 0, "updated": 0, "skipped": 0}
        if user_one:
            user_one_membership_counts = ensure_user_one_memberships(db, clubs, user_one.id)
        meeting_counts = upsert_meetings_and_participants(
            db,
            clubs,
            args.meetings_per_club,
            rng,
            FIXED_LEADER_USER_ID,
            FIXED_LEADER_CLUB_INDEX,
            force_user_id=user_one.id if user_one else None,
        )

    print("Seed completed")
    print(f"users: created={user_counts['created']}, skipped={user_counts['skipped']}")
    print(f"clubs: created={club_counts['created']}, skipped={club_counts['skipped']}")
    print("memberships: "
          f"created={membership_counts['created']}, "
          f"updated={membership_counts['updated']}, "
          f"skipped={membership_counts['skipped']}")
    if user_one:
        print("user_id=1 memberships: "
              f"created={user_one_membership_counts['created']}, "
              f"updated={user_one_membership_counts['updated']}, "
              f"skipped={user_one_membership_counts['skipped']}")
    print("meetings: "
          f"created={meeting_counts['meeting_created']}, "
          f"skipped={meeting_counts['meeting_skipped']}")
    print("participants: "
          f"created={meeting_counts['participant_created']}, "
          f"skipped={meeting_counts['participant_skipped']}")


if __name__ == "__main__":
    main()
