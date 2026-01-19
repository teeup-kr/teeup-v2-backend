#!/usr/bin/env python3
"""
테스트 계정 생성 스크립트
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.orm import Session
from database import get_db
from models import User
from schemas import UserRole, UserStatus, Provider
import hashlib
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_test_accounts():
    """테스트 계정들 생성"""
    
    # 데이터베이스 세션 생성
    db = next(get_db())
    
    try:
        # 테스트 계정들 정의
        test_accounts = [
            {
                "id": "admin_001",
                "email": "admin@teeup.run",
                "nickname": "관리자",
                "realname": "관리자",
                "password": "test1234",
                "role": UserRole.ADMIN,
                "status": UserStatus.ACTIVE,
                "birthdate": datetime(1980, 1, 1)
            },
            {
                "id": "leader_001",
                "email": "leader1@teeup.run",
                "nickname": "리더1",
                "realname": "리더1",
                "password": "test1234",
                "role": UserRole.USER,
                "status": UserStatus.ACTIVE,
                "birthdate": datetime(1985, 5, 15)
            },
            {
                "id": "manager_001",
                "email": "manager1@teeup.run",
                "nickname": "매니저1",
                "realname": "매니저1",
                "password": "test1234",
                "role": UserRole.USER,
                "status": UserStatus.ACTIVE,
                "birthdate": datetime(1988, 8, 20)
            },
            {
                "id": "user_001",
                "email": "user1@teeup.run",
                "nickname": "사용자1",
                "realname": "사용자1",
                "password": "test1234",
                "role": UserRole.USER,
                "status": UserStatus.ACTIVE,
                "birthdate": datetime(1990, 3, 10)
            },
            {
                "id": "user_002",
                "email": "user2@teeup.run",
                "nickname": "사용자2",
                "realname": "사용자2",
                "password": "test1234",
                "role": UserRole.USER,
                "status": UserStatus.ACTIVE,
                "birthdate": datetime(1992, 7, 25)
            },
            {
                "id": "user_003",
                "email": "user3@teeup.run",
                "nickname": "사용자3",
                "realname": "사용자3",
                "password": "test1234",
                "role": UserRole.USER,
                "status": UserStatus.ACTIVE,
                "birthdate": datetime(1995, 11, 12)
            }
        ]
        
        for account_data in test_accounts:
            # 기존 계정 확인
            existing_user = db.query(User).filter(User.email == account_data["email"]).first()
            
            if not existing_user:
                # 비밀번호 해시화
                password_hash = hashlib.sha256(account_data["password"].encode()).hexdigest()
                
                # 사용자 생성
                user = User(
                    id=account_data["id"],
                    email=account_data["email"],
                    nickname=account_data["nickname"],
                    realname=account_data["realname"],
                    password=password_hash,
                    role=account_data["role"],
                    status=account_data["status"],
                    provider=Provider.LOCAL,
                    needs_terms_agreement=False,
                    birthdate=account_data["birthdate"]
                )
                
                db.add(user)
                logger.info(f"✅ 테스트 계정 생성: {account_data['email']} ({account_data['role']})")
            else:
                logger.info(f"⚠️ 계정 이미 존재: {account_data['email']}")
        
        db.commit()
        logger.info("🎉 모든 테스트 계정 생성 완료!")
        
        # 생성된 계정 목록 출력
        logger.info("\n📋 생성된 테스트 계정들:")
        for account in test_accounts:
            logger.info(f"- {account['email']} / {account['password']} ({account['role']})")
            
    except Exception as e:
        db.rollback()
        logger.error(f"❌ 테스트 계정 생성 실패: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    create_test_accounts()
