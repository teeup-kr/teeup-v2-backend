import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import get_db
from models import User, UserRole

def check_admin_users():
    db = next(get_db())
    try:
        # 모든 사용자 조회
        users = db.query(User).filter(User.deleted_at.is_(None)).all()
        
        print("=== 모든 사용자 목록 ===")
        for user in users:
            print(f"ID: {user.id}")
            print(f"Email: {user.email}")
            print(f"Nickname: {user.nickname}")
            print(f"Role: {user.role}")
            print(f"Status: {user.status}")
            print("---")
        
        # 관리자 사용자만 조회
        admin_users = db.query(User).filter(
            User.role == UserRole.ADMIN,
            User.deleted_at.is_(None)
        ).all()
        
        print(f"\n=== 관리자 사용자 ({len(admin_users)}명) ===")
        for user in admin_users:
            print(f"ID: {user.id}")
            print(f"Email: {user.email}")
            print(f"Nickname: {user.nickname}")
            print(f"Role: {user.role}")
            print("---")
            
    except Exception as e:
        print(f"오류 발생: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    check_admin_users()
