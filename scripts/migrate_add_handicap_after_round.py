#!/usr/bin/env python3
"""
user_score_history.handicap_after_round 컬럼 추가

이 경기 반영 후 자동 재계산된 핸디캡 (기록 내역 표시용)

  python scripts/migrate_add_handicap_after_round.py
"""
import sys
from pathlib import Path

_root = Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from sqlalchemy import text

from database import engine


def column_exists(connection, table: str, column: str) -> bool:
    r = connection.execute(
        text(
            """
            SELECT COUNT(*) AS c
            FROM information_schema.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE()
              AND TABLE_NAME = :t
              AND COLUMN_NAME = :c
            """
        ),
        {"t": table, "c": column},
    )
    row = r.fetchone()
    return (row[0] if row else 0) > 0


def main() -> None:
    with engine.begin() as conn:
        if column_exists(conn, "user_score_history", "handicap_after_round"):
            print("user_score_history.handicap_after_round already exists — nothing to do.")
            return
        print("Adding user_score_history.handicap_after_round ...")
        conn.execute(
            text(
                """
                ALTER TABLE user_score_history
                ADD COLUMN handicap_after_round DECIMAL(4,1) NULL
                COMMENT '이 경기 반영 후 핸디캡 (자동 재계산 결과, 기록 표시용)'
                AFTER handicap_used
                """
            )
        )
        print("Done.")


if __name__ == "__main__":
    main()
