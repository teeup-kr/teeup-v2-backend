"""
백오피스 공지사항 API (시스템 공지)
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import logging

from database import get_db
from utils.datetime_utils import get_kst_now
from .deps import get_admin_user

logger = logging.getLogger(__name__)

router = APIRouter(tags=["admin-notices"])


@router.get("/notices")
async def get_admin_notices(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_admin_user),
):
    """관리자용 공지사항 목록 조회"""
    try:
        from models import Notice
        from sqlalchemy import desc

        notices = db.query(Notice).order_by(desc(Notice.created_at)).limit(20).all()
        notice_list = []
        for n in notices:
            notice_list.append({
                "id": n.id, "title": n.title, "type": n.type.value,
                "is_published": n.is_published,
                "created_at": n.created_at.isoformat() if n.created_at else None,
            })
        return {"data": notice_list, "total": len(notice_list)}
    except Exception as e:
        logger.error(f"관리자 공지사항 목록 조회 중 오류: {str(e)}")
        return {"data": [], "total": 0}


@router.post("/notices")
async def create_admin_notice(
    notice_data: dict,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_admin_user),
):
    """관리자용 공지사항 생성"""
    try:
        from models import Notice
        from models.enums import NoticeType

        for field in ["title", "content"]:
            if field not in notice_data or not notice_data[field]:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"{field} 필드는 필수입니다")
        new_notice = Notice(
            title=notice_data["title"],
            content=notice_data["content"],
            type=NoticeType.SYSTEM,
            author_id=current_user["id"],
            is_important=notice_data.get("is_important", False),
        )
        db.add(new_notice)
        db.commit()
        db.refresh(new_notice)
        try:
            from utils.notification_service import create_notice_notification
            from models import User, UserStatus
            for user in db.query(User).filter(User.status == UserStatus.ACTIVE).all():
                create_notice_notification(db=db, user_id=user.id, notice_title=notice_data["title"])
        except Exception as e:
            logger.error(f"시스템 공지사항 알림 전송 실패: {str(e)}")
        return {
            "id": new_notice.id, "title": new_notice.title, "content": new_notice.content,
            "is_important": new_notice.is_important,
            "created_at": new_notice.created_at.isoformat() if new_notice.created_at else None,
            "updated_at": new_notice.updated_at.isoformat() if new_notice.updated_at else None,
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"관리자 공지사항 생성 중 오류: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"공지사항 생성 중 오류가 발생했습니다: {str(e)}")


@router.put("/notices/{notice_id}")
async def update_admin_notice(
    notice_id: int,
    notice_data: dict,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_admin_user),
):
    """관리자용 공지사항 수정"""
    try:
        from models import Notice

        notice = db.query(Notice).filter(Notice.id == notice_id).first()
        if not notice:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="공지사항을 찾을 수 없습니다")
        if "title" in notice_data:
            notice.title = notice_data["title"]
        if "content" in notice_data:
            notice.content = notice_data["content"]
        if "is_important" in notice_data:
            notice.is_important = notice_data["is_important"]
        notice.updated_at = get_kst_now()
        db.commit()
        db.refresh(notice)
        return {
            "id": notice.id, "title": notice.title, "content": notice.content,
            "is_important": notice.is_important,
            "created_at": notice.created_at.isoformat() if notice.created_at else None,
            "updated_at": notice.updated_at.isoformat() if notice.updated_at else None,
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"관리자 공지사항 수정 중 오류: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="공지사항 수정 중 오류가 발생했습니다")


@router.delete("/notices/{notice_id}")
async def delete_admin_notice(
    notice_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_admin_user),
):
    """관리자용 공지사항 삭제"""
    try:
        from models import Notice

        notice = db.query(Notice).filter(Notice.id == notice_id).first()
        if not notice:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="공지사항을 찾을 수 없습니다")
        if hasattr(notice, "deleted_at"):
            notice.deleted_at = get_kst_now()
        else:
            db.delete(notice)
        db.commit()
        return {"message": "공지사항이 성공적으로 삭제되었습니다", "success": True}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"관리자 공지사항 삭제 중 오류: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="공지사항 삭제 중 오류가 발생했습니다")
