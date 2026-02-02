"""
백오피스 공통 의존성 (인증, get_admin_user 등)
"""
import logging
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from pydantic import BaseModel

from database import get_db
from models import Admin, UserStatus
from utils.jwt_auth import jwt_auth

logger = logging.getLogger(__name__)

security = HTTPBearer()


class AdminLoginRequest(BaseModel):
    email: str
    password: str


class AdminLoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: dict


def verify_admin_credentials(email: str, password: str, db: Session) -> Admin:
    """관리자 인증 확인"""
    try:
        admin = db.query(Admin).filter(Admin.email == email, Admin.deleted_at.is_(None)).first()
        if not admin:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="인증 정보가 올바르지 않습니다")
        import hashlib
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        if admin.password != password_hash:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="인증 정보가 올바르지 않습니다")
        if admin.status == UserStatus.DELETED:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="삭제된 관리자 계정입니다")
        if admin.status == UserStatus.DEACTIVATED:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="비활성화된 관리자 계정입니다")
        return admin
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"관리자 인증 중 오류: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"인증 처리 중 오류가 발생했습니다: {str(e)}"
        )


def get_admin_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> dict:
    """JWT 토큰으로 어드민 사용자 조회"""
    try:
        token = credentials.credentials
        logger.info(f"Admin auth - Token received: {token[:20]}...")
        payload = jwt_auth.verify_token(token, "access")
        user_id = payload.get("id")
        if not user_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="토큰에 사용자 정보가 없습니다")
        admin = db.query(Admin).filter(Admin.id == user_id, Admin.deleted_at.is_(None)).first()
        if not admin:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="관리자를 찾을 수 없습니다")
        if admin.status == UserStatus.DELETED:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="삭제된 관리자 계정입니다")
        if admin.status == UserStatus.DEACTIVATED:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="비활성화된 관리자 계정입니다")
        return {
            "id": admin.id,
            "email": admin.email,
            "name": admin.name,
            "status": admin.status.value if admin.status else None,
            "type": "admin",
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"어드민 사용자 인증 중 오류: {str(e)}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="토큰 검증 중 오류가 발생했습니다")
