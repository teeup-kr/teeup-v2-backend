"""
백오피스 약관 관리 API
"""
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import logging

from database import get_db
from models import Terms
from schemas import TermsType
from utils.datetime_utils import get_kst_now
from .deps import get_admin_user

logger = logging.getLogger(__name__)

router = APIRouter(tags=["admin-terms"])


def _get_default_terms_title(terms_type: str) -> str:
    titles = {
        "service": "서비스 이용약관",
        "privacy": "개인정보처리방침",
        "collection": "개인정보 수집 및 이용동의",
        "privacy_collection": "개인정보 수집 및 이용동의",
        "marketing": "마케팅정보 수신동의",
    }
    return titles.get(terms_type, "약관")


def _get_default_terms_content(terms_type: str) -> str:
    contents = {
        "service": "<h2>제1조 (목적)</h2><p>본 약관은 TeeUp 서비스의 이용과 관련하여 회사와 이용자 간의 권리, 의무 및 책임사항을 규정함을 목적으로 합니다.</p>",
        "privacy": "<h2>제1조 (개인정보의 처리목적)</h2><p>회사는 다음의 목적을 위하여 개인정보를 처리합니다.</p>",
        "collection": "<h2>제1조 (개인정보의 수집 및 이용목적)</h2><p>회사는 다음의 목적을 위하여 개인정보를 수집 및 이용합니다.</p>",
        "privacy_collection": "<h2>제1조 (개인정보의 수집 및 이용목적)</h2><p>회사는 다음의 목적을 위하여 개인정보를 수집 및 이용합니다.</p>",
        "marketing": "<h2>제1조 (마케팅정보 수신동의)</h2><p>회사는 이용자에게 다양한 정보를 제공하기 위해 마케팅 정보를 수신하는 것에 동의를 받습니다.</p>",
    }
    return contents.get(terms_type, "<p>약관 내용을 입력해주세요.</p>")


TYPE_MAPPING = {
    "service": TermsType.SERVICE,
    "privacy": TermsType.PRIVACY,
    "privacy_collection": TermsType.PRIVACY_COLLECTION,
    "marketing": TermsType.MARKETING,
}


@router.get("/terms")
async def get_admin_terms(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_admin_user),
):
    """관리자용 약관 목록 조회"""
    try:
        from sqlalchemy import desc

        terms = db.query(Terms).order_by(desc(Terms.created_at)).limit(20).all()
        term_list = []
        for t in terms:
            term_list.append({
                "id": t.id, "title": t.title, "type": t.type.value, "content": t.content,
                "is_active": t.is_active, "is_required": t.is_required,
                "published_at": t.published_at.isoformat() if t.published_at else None,
                "created_at": t.created_at.isoformat() if t.created_at else None,
            })
        return {"data": term_list, "total": len(term_list)}
    except Exception as e:
        logger.error(f"관리자 약관 목록 조회 중 오류: {str(e)}")
        return {"data": [], "total": 0}


@router.post("/terms")
async def create_admin_terms(
    terms_data: dict,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_admin_user),
):
    """관리자용 약관 생성"""
    try:
        if terms_data.get("is_active", True):
            db.query(Terms).filter(Terms.type == TermsType(terms_data.get("type", "SERVICE"))).update({"is_active": False})
        new_term = Terms(
            type=TermsType(terms_data.get("type", "SERVICE")),
            title=terms_data.get("title", ""),
            content=terms_data.get("content", ""),
            is_active=terms_data.get("is_active", True),
            is_required=terms_data.get("is_required", False),
            published_at=datetime.now(),
        )
        db.add(new_term)
        db.commit()
        db.refresh(new_term)
        return {
            "id": new_term.id, "title": new_term.title, "type": new_term.type.value,
            "content": new_term.content, "is_active": new_term.is_active,
            "is_required": new_term.is_required,
            "published_at": new_term.published_at.isoformat() if new_term.published_at else None,
            "created_at": new_term.created_at.isoformat() if new_term.created_at else None,
        }
    except Exception as e:
        logger.error(f"관리자 약관 생성 중 오류: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="약관 생성 중 오류가 발생했습니다")


@router.put("/terms/{terms_type}")
async def update_terms(
    terms_type: str,
    terms_data: dict,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_admin_user),
):
    """약관 수정 (타입 기반)"""
    try:
        if terms_type not in TYPE_MAPPING:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="유효하지 않은 약관 타입입니다")
        db_terms_type = TYPE_MAPPING[terms_type]
        if "title" not in terms_data or "content" not in terms_data:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="제목과 내용은 필수입니다")
        terms = db.query(Terms).filter(Terms.type == db_terms_type, Terms.is_active == True).first()
        if terms:
            terms.title = terms_data["title"]
            terms.content = terms_data["content"]
            terms.updated_at = get_kst_now()
        else:
            terms = Terms(type=db_terms_type, title=terms_data["title"], content=terms_data["content"], is_active=True)
            db.add(terms)
        db.commit()
        return {"message": "약관이 성공적으로 저장되었습니다", "success": True}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"약관 저장 중 오류: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="서버 내부 오류가 발생했습니다")


@router.put("/terms/id/{term_id}")
async def update_admin_terms(
    term_id: int,
    terms_data: dict,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_admin_user),
):
    """관리자용 약관 수정"""
    try:
        term = db.query(Terms).filter(Terms.id == term_id).first()
        if not term:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="약관을 찾을 수 없습니다")
        if "type" in terms_data:
            term.type = TermsType(terms_data["type"])
        if "title" in terms_data:
            term.title = terms_data["title"]
        if "content" in terms_data:
            term.content = terms_data["content"]
        if "is_active" in terms_data:
            term.is_active = terms_data["is_active"]
        if "is_required" in terms_data:
            term.is_required = terms_data["is_required"]
        term.updated_at = datetime.now()
        db.commit()
        db.refresh(term)
        return {
            "id": term.id, "title": term.title, "type": term.type.value,
            "content": term.content, "is_active": term.is_active, "is_required": term.is_required,
            "published_at": term.published_at.isoformat() if term.published_at else None,
            "created_at": term.created_at.isoformat() if term.created_at else None,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"관리자 약관 수정 중 오류: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="약관 수정 중 오류가 발생했습니다")


@router.put("/terms/{term_id}/activate")
async def activate_admin_terms(
    term_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_admin_user),
):
    """관리자용 약관 활성화"""
    try:
        term = db.query(Terms).filter(Terms.id == term_id).first()
        if not term:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="약관을 찾을 수 없습니다")
        db.query(Terms).filter(Terms.type == term.type, Terms.id != term_id).update({"is_active": False})
        term.is_active = True
        db.commit()
        db.refresh(term)
        return {"message": "약관이 활성화되었습니다", "term": {"id": term.id, "title": term.title, "type": term.type.value, "is_active": term.is_active}}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"관리자 약관 활성화 중 오류: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="약관 활성화 중 오류가 발생했습니다")


@router.put("/terms/{term_id}/deactivate")
async def deactivate_admin_terms(
    term_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_admin_user),
):
    """관리자용 약관 비활성화"""
    try:
        term = db.query(Terms).filter(Terms.id == term_id).first()
        if not term:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="약관을 찾을 수 없습니다")
        term.is_active = False
        db.commit()
        db.refresh(term)
        return {"message": "약관이 비활성화되었습니다", "term": {"id": term.id, "title": term.title, "type": term.type.value, "is_active": term.is_active}}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"관리자 약관 비활성화 중 오류: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="약관 비활성화 중 오류가 발생했습니다")


@router.get("/terms/{terms_type}")
async def get_terms(
    terms_type: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_admin_user),
):
    """약관 조회 (타입별)"""
    try:
        if terms_type not in TYPE_MAPPING:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="유효하지 않은 약관 타입입니다")
        db_terms_type = TYPE_MAPPING[terms_type]
        terms = db.query(Terms).filter(Terms.type == db_terms_type, Terms.is_active == True).first()
        if not terms:
            terms = Terms(
                type=db_terms_type,
                title=_get_default_terms_title(terms_type),
                content=_get_default_terms_content(terms_type),
                is_active=True,
            )
            db.add(terms)
            db.commit()
            db.refresh(terms)
        return {"title": terms.title, "content": terms.content, "updated_at": terms.updated_at.isoformat() if terms.updated_at else None}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"약관 조회 중 오류: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="서버 내부 오류가 발생했습니다")
