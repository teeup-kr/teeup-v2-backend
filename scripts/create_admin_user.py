#!/usr/bin/env python3
"""
관리자 계정 생성 스크립트
- Admin 엔티티(admins 테이블)에 관리자 계정을 생성합니다.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from database import get_db
from models import Admin, Provider, UserStatus
import hashlib
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_admin_user():
    """Admin 엔티티에 관리자 계정 생성"""

    db = next(get_db())

    try:
        # 기존 관리자 계정 확인 및 삭제 (soft delete 대신 물리 삭제)
        existing_admin = db.query(Admin).filter(
            Admin.email == "admin@teeup.kr",
            Admin.deleted_at.is_(None)
        ).first()

        if existing_admin:
            logger.info("기존 관리자 계정을 삭제하고 새로 생성합니다.")
            print("[경고] 기존 관리자 계정을 삭제하고 새로 생성합니다.")
            db.delete(existing_admin)
            db.commit()

        # 비밀번호 해시 (SHA256 - Admin 인증 방식과 동일)
        password_hash = hashlib.sha256("admin123".encode()).hexdigest()

        # Admin 엔티티 생성
        admin = Admin(
            email="admin@teeup.kr",
            password=password_hash,
            name="관리자",
            provider=Provider.LOCAL,
            status=UserStatus.ACTIVE,
        )

        db.add(admin)
        db.commit()
        db.refresh(admin)

        logger.info("관리자 계정이 성공적으로 생성되었습니다!")
        logger.info("이메일: admin@teeup.kr")
        logger.info("비밀번호: admin123")
        logger.info(f"Admin ID: {admin.id}")
        print("[성공] 관리자 계정이 성공적으로 생성되었습니다!")
        print("이메일: admin@teeup.kr")
        print("비밀번호: admin123")
        print(f"Admin ID: {admin.id}")

    except Exception as e:
        logger.error(f"관리자 계정 생성 실패: {e}")
        import traceback
        logger.error(traceback.format_exc())
        print(f"[실패] 관리자 계정 생성 실패: {e}")
        print(traceback.format_exc())
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    create_admin_user()
