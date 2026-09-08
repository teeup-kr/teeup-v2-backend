-- expense_items: 항목별 메모 (소셜 정산 비용 항목, 라운딩 기타 비용)
--
-- 모델: models/meeting.py ExpenseItem.memo
-- 미적용 시 /admin/meetings/{id}/settlement 등에서 500 (Unknown column 'expense_items.memo')
--
-- 실행 예: mysql -u USER -p DB_NAME < scripts/add_expense_item_memo.sql
-- 또는:   python scripts/migrate_add_expense_item_memo.py
--
-- MySQL / MariaDB
ALTER TABLE expense_items
  ADD COLUMN memo VARCHAR(2000) NULL COMMENT '항목별 메모' AFTER title;

-- PostgreSQL (COMMENT/위치는 DB에 맞게 조정)
-- ALTER TABLE expense_items ADD COLUMN memo VARCHAR(2000) NULL;
