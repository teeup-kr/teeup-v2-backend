#!/usr/bin/env python3
"""
데이터베이스 내용 비우기
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import engine, Base
from sqlalchemy import text

def clear_database():
    """데이터베이스의 모든 테이블 내용 삭제"""
    print("🗑️ 데이터베이스 내용 비우기 시작...")
    
    try:
        with engine.connect() as connection:
            # 모든 테이블의 데이터 삭제 (외래키 제약조건 고려하여 순서대로)
            tables_to_clear = [
                'refresh_token_blacklist',
                'terms_agreements', 
                'inquiry_responses',
                'inquiries',
                'notices',
                'expense_participants',
                'expenses',
                'scores',
                'team_members',
                'teams',
                'meeting_participants',
                'meetings',
                'personal_records',
                'user_schedules',
                'subscriptions',
                'user_payment_methods',
                'payments',
                'plans',
                'club_notices',
                'regulation_versions',
                'club_memberships',
                'club_applications',
                'clubs',
                'terms',
                'users'
            ]
            
            for table in tables_to_clear:
                try:
                    connection.execute(text(f"DELETE FROM {table}"))
                    print(f"✅ {table} 테이블 비우기 완료")
                except Exception as e:
                    print(f"⚠️ {table} 테이블 비우기 실패: {e}")
            
            connection.commit()
            print("✅ 데이터베이스 비우기 완료!")
            
    except Exception as e:
        print(f"❌ 데이터베이스 비우기 실패: {e}")

if __name__ == "__main__":
    clear_database()

