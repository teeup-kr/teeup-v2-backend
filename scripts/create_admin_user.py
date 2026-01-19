#!/usr/bin/env python3
"""
관리자 계정 생성 스크립트
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from database import get_db
from models import User, UserRole, UserStatus, Provider
from utils.cuid import generate_cuid
import hashlib
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_admin_user():
    """관리자 계정 생성"""
    
    # 데이터베이스 세션 생성
    db = next(get_db())
    
    try:
        # 기존 관리자 계정 확인 및 삭제
        existing_admin = db.query(User).filter(
            User.email == "admin@teeup.run",
            User.deleted_at.is_(None)
        ).first()
        
        if existing_admin:
            logger.info("기존 관리자 계정을 삭제하고 새로 생성합니다.")
            print("[경고] 기존 관리자 계정을 삭제하고 새로 생성합니다.")
            db.delete(existing_admin)
            db.commit()
        
        # 비밀번호 해시화
        password_hash = hashlib.sha256("admin123".encode()).hexdigest()
        
        # CUID 생성
        user_uuid = generate_cuid()
        
        # 관리자 계정 생성
        admin_user = User(
            uuid=user_uuid,
            email="admin@teeup.run",
            nickname="관리자",
            realname="관리자",
            password=password_hash,
            role=UserRole.ADMIN,
            status=UserStatus.ACTIVE,
            provider=Provider.LOCAL,
            needs_terms_agreement=False,
            terms_agreement=True,
            privacy_policy=True,
            privacy_collection=True,
            marketing_consent=False
        )
        
        db.add(admin_user)
        db.commit()
        db.refresh(admin_user)
        
        logger.info("관리자 계정이 성공적으로 생성되었습니다!")
        logger.info("이메일: admin@teeup.run")
        logger.info("비밀번호: admin123")
        logger.info(f"UUID: {user_uuid}")
        print("[성공] 관리자 계정이 성공적으로 생성되었습니다!")
        print("이메일: admin@teeup.run")
        print("비밀번호: admin123")
        print(f"UUID: {user_uuid}")
        
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