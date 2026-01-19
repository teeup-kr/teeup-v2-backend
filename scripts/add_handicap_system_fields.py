#!/usr/bin/env python3
"""
핸디캡 시스템 개선 필드 추가 마이그레이션 스크립트

Phase 1-4에서 추가된 핸디캡 관련 필드 및 테이블을 데이터베이스에 추가합니다.

추가되는 필드:
- users 테이블:
  - initial_handicap: DECIMAL(4,1) - 가입 시 수동 입력한 핸디캡
  - calculated_handicap: DECIMAL(4,1) - 자동 계산된 핸디캡
  - handicap_update_method: ENUM('MANUAL', 'AUTO') - 핸디캡 업데이트 방식
  - handicap_calculation_count: INT - 핸디캡 계산에 사용된 경기 수

추가되는 테이블:
- user_score_history: 사용자의 최근 경기 스코어 히스토리
- meeting_results: 직전 대회 성적 저장

사용법:
  python apps/backend/scripts/add_handicap_system_fields.py
"""
import os
import sys
from sqlalchemy import text

# 백엔드 모듈 경로 추가
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))

from database import SessionLocal


def check_column_exists(db, table_name, column_name):
    """컬럼이 존재하는지 확인"""
    check_query = """
    SELECT COUNT(*) as count
    FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE()
    AND TABLE_NAME = :table_name
    AND COLUMN_NAME = :column_name
    """
    result = db.execute(text(check_query), {"table_name": table_name, "column_name": column_name})
    return result.scalar() > 0


def check_table_exists(db, table_name):
    """테이블이 존재하는지 확인"""
    check_query = """
    SELECT COUNT(*) as count
    FROM INFORMATION_SCHEMA.TABLES
    WHERE TABLE_SCHEMA = DATABASE()
    AND TABLE_NAME = :table_name
    """
    result = db.execute(text(check_query), {"table_name": table_name})
    return result.scalar() > 0


def add_handicap_system_fields():
    """핸디캡 시스템 개선 필드 및 테이블 추가"""
    db = SessionLocal()
    
    try:
        print("🚀 핸디캡 시스템 개선 마이그레이션 시작...")
        
        # 1. users 테이블에 필드 추가
        print("\n1️⃣ users 테이블 필드 추가 중...")
        
        columns_to_add = [
            {
                "name": "initial_handicap",
                "definition": "DECIMAL(4,1) COMMENT '가입 시 수동 입력한 핸디캡'",
                "after": "average_score"
            },
            {
                "name": "calculated_handicap",
                "definition": "DECIMAL(4,1) COMMENT '자동 계산된 핸디캡 (최근 N경기 평균 기반)'",
                "after": "initial_handicap"
            },
            {
                "name": "handicap_update_method",
                "definition": "ENUM('MANUAL', 'AUTO') DEFAULT 'MANUAL' COMMENT '핸디캡 업데이트 방식'",
                "after": "calculated_handicap"
            },
            {
                "name": "handicap_calculation_count",
                "definition": "INT DEFAULT 0 COMMENT '핸디캡 계산에 사용된 경기 수'",
                "after": "handicap_update_method"
            }
        ]
        
        for col in columns_to_add:
            if check_column_exists(db, "users", col["name"]):
                print(f"  ⚠️  컬럼이 이미 존재함: {col['name']}")
            else:
                sql = f"ALTER TABLE users ADD COLUMN {col['name']} {col['definition']}"
                if col.get("after"):
                    sql += f" AFTER {col['after']}"
                try:
                    db.execute(text(sql))
                    db.commit()
                    print(f"  ✅ 추가 완료: {col['name']}")
                except Exception as e:
                    db.rollback()
                    print(f"  ❌ 오류 발생: {col['name']} - {e}")
        
        # 2. user_score_history 테이블 생성
        print("\n2️⃣ user_score_history 테이블 생성 중...")
        
        if check_table_exists(db, "user_score_history"):
            print("  ⚠️  테이블이 이미 존재함: user_score_history")
        else:
            create_user_score_history = """
            CREATE TABLE user_score_history (
                id VARCHAR(25) PRIMARY KEY,
                user_id VARCHAR(25) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
                meeting_id VARCHAR(25) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
                gross_score INT NOT NULL COMMENT '실제 타수 (Gross Score)',
                net_score DECIMAL(5,1) COMMENT '넷 스코어 (Gross Score - Handicap)',
                handicap_used DECIMAL(4,1) NOT NULL COMMENT '해당 경기에서 사용된 핸디캡',
                played_at DATETIME NOT NULL COMMENT '경기 날짜',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_user_id (user_id),
                INDEX idx_meeting_id (meeting_id),
                INDEX idx_played_at (played_at)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
            """
            try:
                db.execute(text(create_user_score_history))
                db.commit()
                print("  ✅ 테이블 생성 완료: user_score_history")
                
                # Foreign Key는 나중에 추가 (타입 호환성 문제 방지)
                try:
                    db.execute(text("ALTER TABLE user_score_history ADD CONSTRAINT fk_user_score_history_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE"))
                    db.commit()
                    print("  ✅ Foreign Key 추가 완료: user_id")
                except Exception as fk_error:
                    if "Duplicate foreign key constraint name" in str(fk_error) or "already exists" in str(fk_error):
                        print("  ⚠️  Foreign Key가 이미 존재함: user_id")
                    else:
                        print(f"  ⚠️  Foreign Key 추가 실패 (무시): user_id - {fk_error}")
                
                try:
                    db.execute(text("ALTER TABLE user_score_history ADD CONSTRAINT fk_user_score_history_meeting FOREIGN KEY (meeting_id) REFERENCES meetings(id) ON DELETE CASCADE"))
                    db.commit()
                    print("  ✅ Foreign Key 추가 완료: meeting_id")
                except Exception as fk_error:
                    if "Duplicate foreign key constraint name" in str(fk_error) or "already exists" in str(fk_error):
                        print("  ⚠️  Foreign Key가 이미 존재함: meeting_id")
                    else:
                        print(f"  ⚠️  Foreign Key 추가 실패 (무시): meeting_id - {fk_error}")
                        
            except Exception as e:
                db.rollback()
                print(f"  ❌ 오류 발생: user_score_history - {e}")
        
        # 3. meeting_results 테이블 생성
        print("\n3️⃣ meeting_results 테이블 생성 중...")
        
        if check_table_exists(db, "meeting_results"):
            print("  ⚠️  테이블이 이미 존재함: meeting_results")
        else:
            create_meeting_results = """
            CREATE TABLE meeting_results (
                id VARCHAR(25) PRIMARY KEY,
                meeting_id VARCHAR(25) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
                user_id VARCHAR(25) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
                gross_score INT NOT NULL COMMENT '실제 타수',
                net_score DECIMAL(5,1) NOT NULL COMMENT '넷 스코어 (Gross Score - Handicap)',
                `rank` INT COMMENT '순위',
                handicap_used DECIMAL(4,1) NOT NULL COMMENT '사용된 핸디캡',
                completed_at DATETIME NOT NULL COMMENT '경기 완료 시간',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_meeting_id (meeting_id),
                INDEX idx_user_id (user_id),
                INDEX idx_rank (`rank`),
                UNIQUE KEY unique_meeting_user (meeting_id, user_id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
            """
            try:
                db.execute(text(create_meeting_results))
                db.commit()
                print("  ✅ 테이블 생성 완료: meeting_results")
                
                # Foreign Key는 나중에 추가 (타입 호환성 문제 방지)
                try:
                    db.execute(text("ALTER TABLE meeting_results ADD CONSTRAINT fk_meeting_results_meeting FOREIGN KEY (meeting_id) REFERENCES meetings(id) ON DELETE CASCADE"))
                    db.commit()
                    print("  ✅ Foreign Key 추가 완료: meeting_id")
                except Exception as fk_error:
                    if "Duplicate foreign key constraint name" in str(fk_error) or "already exists" in str(fk_error):
                        print("  ⚠️  Foreign Key가 이미 존재함: meeting_id")
                    else:
                        print(f"  ⚠️  Foreign Key 추가 실패 (무시): meeting_id - {fk_error}")
                
                try:
                    db.execute(text("ALTER TABLE meeting_results ADD CONSTRAINT fk_meeting_results_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE"))
                    db.commit()
                    print("  ✅ Foreign Key 추가 완료: user_id")
                except Exception as fk_error:
                    if "Duplicate foreign key constraint name" in str(fk_error) or "already exists" in str(fk_error):
                        print("  ⚠️  Foreign Key가 이미 존재함: user_id")
                    else:
                        print(f"  ⚠️  Foreign Key 추가 실패 (무시): user_id - {fk_error}")
                        
            except Exception as e:
                db.rollback()
                print(f"  ❌ 오류 발생: meeting_results - {e}")
        
        print("\n🎉 핸디캡 시스템 개선 마이그레이션 완료!")
        
    except Exception as e:
        db.rollback()
        print(f"\n❌ 전체 작업 실패: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    add_handicap_system_fields()

