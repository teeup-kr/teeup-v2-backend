from __future__ import annotations

import argparse
from typing import Sequence

from database import SessionLocal
from models import Meeting, MeetingParticipant, MeetingType
from schemas import TeamFormationMode
from utils.team_formation import (
    _form_teams_by_criteria,
    form_random_teams,
    form_teams_by_mode,
    separate_by_gender,
    sort_by_handicap,
    sort_by_previous_record,
    zigzag_distribute,
)

try:
    from line_profiler import LineProfiler
except ImportError as exc:  # pragma: no cover - runtime guard
    raise SystemExit(
        "line-profiler is not installed. Run `pip install -r scripts/loadtest/requirements.txt` first."
    ) from exc


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Line profile for team formation")
    parser.add_argument("--meeting-id", type=int, required=True, help="target ROUND meeting_id")
    parser.add_argument(
        "--mode",
        type=str,
        default=TeamFormationMode.GENDER_MIXED_RANDOM.value,
        choices=[mode.value for mode in TeamFormationMode],
        help="team formation mode",
    )
    parser.add_argument("--team-size", type=int, default=4, help="team size")
    return parser.parse_args()


def _validate_inputs(meeting: Meeting | None, participants: Sequence[MeetingParticipant]) -> None:
    if meeting is None:
        raise SystemExit("Meeting not found for given meeting_id.")
    if meeting.meeting_type != MeetingType.ROUND:
        raise SystemExit("Only ROUND meetings can be profiled.")
    if len(participants) < 2:
        raise SystemExit("At least 2 participants are required for team formation.")


def main() -> int:
    args = parse_args()
    db = SessionLocal()
    try:
        meeting = db.query(Meeting).filter(Meeting.id == args.meeting_id).first()
        participants = db.query(MeetingParticipant).filter(MeetingParticipant.meeting_id == args.meeting_id).all()
        _validate_inputs(meeting, participants)

        mode = TeamFormationMode(args.mode)
        profiler = LineProfiler()
        profiler.add_function(form_teams_by_mode)
        profiler.add_function(_form_teams_by_criteria)
        profiler.add_function(separate_by_gender)
        profiler.add_function(sort_by_handicap)
        profiler.add_function(sort_by_previous_record)
        profiler.add_function(zigzag_distribute)
        profiler.add_function(form_random_teams)

        teams = profiler.runcall(form_teams_by_mode, participants, mode, db, args.team_size)
        print(f"meeting_id={args.meeting_id}, participants={len(participants)}, teams={len(teams)}")
        profiler.print_stats(stripzeros=True)
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
