"""
백오피스 관리자 프로필 API
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import logging

from database import get_db
from models import Admin
from utils.datetime_utils import get_kst_now
from .deps import get_admin_user

logger = logging.getLogger(__name__)

router = APIRouter(tags=["admin-profile"])


@router.get("/profile")
async def get_admin_profile(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_admin_user),
):
    """관리자 프로필 조회"""
    try:
        admin_id = current_user.get("id")
        if not admin_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="인증이 필요합니다")
        admin = db.query(Admin).filter(Admin.id == admin_id, Admin.deleted_at.is_(None)).first()
        if not admin:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="관리자를 찾을 수 없습니다")
        return {
            "id": admin.id,
            "email": admin.email,
            "name": admin.name,
            "role": "ADMIN",
            "created_at": admin.created_at.isoformat() if admin.created_at else None,
            "updated_at": admin.updated_at.isoformat() if admin.updated_at else None,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"관리자 프로필 조회 중 오류: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="서버 내부 오류가 발생했습니다",
        )


@router.put("/profile")
async def update_admin_profile(
    profile_data: dict,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_admin_user),
):
    """관리자 프로필 수정"""
    try:
        admin_id = current_user.get("id")
        if not admin_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="인증이 필요합니다")
        admin = db.query(Admin).filter(Admin.id == admin_id, Admin.deleted_at.is_(None)).first()
        if not admin:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="관리자를 찾을 수 없습니다")
        if "name" in profile_data:
            admin.name = profile_data["name"]
        admin.updated_at = get_kst_now()
        db.commit()
        db.refresh(admin)
        return {
            "id": admin.id,
            "email": admin.email,
            "name": admin.name,
            "role": "ADMIN",
            "created_at": admin.created_at.isoformat() if admin.created_at else None,
            "updated_at": admin.updated_at.isoformat() if admin.updated_at else None,
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"관리자 프로필 수정 중 오류: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="서버 내부 오류가 발생했습니다",
        )


@router.put("/password")
async def change_admin_password(
    password_data: dict,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_admin_user),
):
    """관리자 비밀번호 변경"""
    try:
        user_id = current_user.get("id")
        if not user_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="인증이 필요합니다")
        current_password = password_data.get("current_password")
        new_password = password_data.get("new_password")
        confirm_password = password_data.get("confirm_password")
        if not current_password or not new_password or not confirm_password:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="모든 비밀번호 필드를 입력해주세요")
        if new_password != confirm_password:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="새 비밀번호와 확인 비밀번호가 일치하지 않습니다")
        from routers.auth import validate_password

        password_validation = validate_password(new_password)
        if not password_validation["is_valid"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="; ".join(password_validation["errors"]),
            )
        admin = db.query(Admin).filter(Admin.id == user_id, Admin.deleted_at.is_(None)).first()
        if not admin:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="관리자를 찾을 수 없습니다")
        import hashlib

        current_password_hash = hashlib.sha256(current_password.encode()).hexdigest()
        if admin.password != current_password_hash:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="현재 비밀번호가 올바르지 않습니다")
        admin.password = hashlib.sha256(new_password.encode()).hexdigest()
        admin.updated_at = get_kst_now()
        db.commit()
        return {"message": "비밀번호가 성공적으로 변경되었습니다", "success": True}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"관리자 비밀번호 변경 중 오류: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="서버 내부 오류가 발생했습니다",
        )
