-- 클럽별 모임 정산 기능 ON/OFF (기존 행은 모두 사용 중으로 간주)
ALTER TABLE clubs ADD COLUMN settlement_enabled TINYINT(1) NOT NULL DEFAULT 1 COMMENT '모임 정산 기능 사용 여부';
