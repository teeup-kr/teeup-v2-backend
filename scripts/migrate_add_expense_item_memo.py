#!/usr/bin/env python3
"""
expense_items.memo 컬럼 추가 (모델 meeting.ExpenseItem과 동기화)

500 오류 예:
  Unknown column 'expense_items_1.memo' in 'field list'

사용 (백엔드 프로젝트 루트 teeup-v2-backend 에서):
  python scripts/migrate_add_expense_item_memo.py

또는 SQL 직접:
  mysql ... < scripts/add_expense_item_memo.sql
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
        if column_exists(conn, "expense_items", "memo"):
            print("expense_items.memo already exists — nothing to do.")
            return
        print("Adding expense_items.memo ...")
        conn.execute(
            text(
                """
                ALTER TABLE expense_items
                ADD COLUMN memo VARCHAR(2000) NULL
                COMMENT '항목별 메모'
                AFTER title
                """
            )
        )
        print("Done.")


if __name__ == "__main__":
    main()
