"""
FAQ 관리 API 라우터
- 관리자용 FAQ 관리 API
- 클라이언트용 FAQ 조회 API
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from typing import List, Optional
from datetime import datetime
import logging

from database import get_db
from models import FAQ, FAQCategory, User
from schemas import (
    FAQResponse, FAQPageResponse, FAQCategoryResponse,
    FAQCreate, FAQUpdate, FAQCategoryCreate, FAQCategoryUpdate,
    PaginatedResponse, MessageResponse
)
from routers.admin import get_admin_user
from routers.auth import get_current_active_user

logger = logging.getLogger(__name__)

# 관리자용 라우터
admin_router = APIRouter(prefix="/admin", tags=["admin"])

# 클라이언트용 라우터
client_router = APIRouter(prefix="", tags=["faq"])


# -------------------------
# 내부 공통 유틸
# -------------------------

def _ensure_admin(admin_data: dict):
    """관리자 권한 확인"""
def _to_faq_response(faq: FAQ) -> FAQResponse:
    """FAQ 모델을 응답 스키마로 변환"""
    return FAQResponse(
        id=faq.id,
        question=faq.question,
        answer=faq.answer,
        category_id=faq.category_id,
        category_title=getattr(getattr(faq, "category", None), "title", None) if faq.category else None,
        order=faq.order,
        is_active=faq.is_active,
        is_deleted=faq.is_deleted,
        view_count=faq.view_count or 0,
        created_at=faq.created_at,
        updated_at=faq.updated_at,
        deleted_at=faq.deleted_at,
    )


# -------------------------
# 관리자: 카테고리 API
# -------------------------

@admin_router.get("/faq-categories", response_model=List[FAQCategoryResponse])
async def admin_faq_categories_api(
    db: Session = Depends(get_db),
    admin_data: dict = Depends(get_admin_user)
):
    """FAQ 카테고리 목록 조회 (관리자)"""
    if not admin_data or admin_data.get("role") != "ADMIN":
        raise HTTPException(status_code=403, detail="관리자 권한이 필요합니다.")
    cats = db.query(FAQCategory).order_by(FAQCategory.order.asc()).all()
    return [
        FAQCategoryResponse(
            id=c.id, title=c.title, order=c.order, is_active=c.is_active,
            created_at=c.created_at, updated_at=c.updated_at
        )
        for c in cats
    ]

@admin_router.post("/faq-categories", response_model=MessageResponse)
async def admin_faq_category_create_api(
    data: FAQCategoryCreate,
    db: Session = Depends(get_db),
    admin_data: dict = Depends(get_admin_user)
):
    """FAQ 카테고리 생성 (관리자)"""
    if not admin_data or admin_data.get("role") != "ADMIN":
        raise HTTPException(status_code=403, detail="관리자 권한이 필요합니다.")
    
    title = data.title.strip()
    order = data.order
    is_active = data.is_active

    if not title:
        raise HTTPException(status_code=400, detail="카테고리명은 필수입니다.")
    if len(title) > 50:
        raise HTTPException(status_code=400, detail="카테고리명은 50자 이하로 입력해주세요.")

    exists = db.query(FAQCategory).filter(FAQCategory.title == title).first()
    if exists:
        raise HTTPException(status_code=400, detail="이미 존재하는 카테고리명입니다.")

    current_count = db.query(FAQCategory).count()
    if current_count == 0 or order <= 0:
        adjusted_order = 1
    elif order > current_count + 1:
        adjusted_order = current_count + 1
    else:
        adjusted_order = order

    # 순서 조정
    conflicts = db.query(FAQCategory).filter(FAQCategory.order >= adjusted_order).all()
    for c in conflicts:
        c.order += 1

    cat = FAQCategory(title=title, order=adjusted_order, is_active=is_active)
    db.add(cat)
    db.commit()
    db.refresh(cat)
    return MessageResponse(message="FAQ 카테고리가 생성되었습니다.", success=True)

@admin_router.put("/faq-categories/{category_id}", response_model=MessageResponse)
async def admin_faq_category_update_api(
    category_id: int,
    data: FAQCategoryUpdate,
    db: Session = Depends(get_db),
    admin_data: dict = Depends(get_admin_user)
):
    """FAQ 카테고리 수정 (관리자)"""
    _ensure_admin(admin_data)
    
    cat = db.query(FAQCategory).filter(FAQCategory.id == category_id).first()
    if not cat:
        raise HTTPException(status_code=404, detail="FAQ 카테고리를 찾을 수 없습니다.")

    # title 수정
    if data.title is not None:
        title = data.title.strip()
        if not title:
            raise HTTPException(status_code=400, detail="카테고리명은 필수입니다.")
        if len(title) > 50:
            raise HTTPException(status_code=400, detail="카테고리명은 50자 이하로 입력해주세요.")
        dup = db.query(FAQCategory).filter(
            FAQCategory.title == title, FAQCategory.id != category_id
        ).first()
        if dup:
            raise HTTPException(status_code=400, detail="이미 존재하는 카테고리명입니다.")
        cat.title = title

    # order 수정
    if data.order is not None:
        new_order = int(data.order)
        old_order = cat.order
        if new_order != old_order:
            if new_order > old_order:
                db.query(FAQCategory).filter(
                    FAQCategory.order > old_order,
                    FAQCategory.order <= new_order,
                    FAQCategory.id != category_id
                ).update({FAQCategory.order: FAQCategory.order - 1}, synchronize_session=False)
            else:
                db.query(FAQCategory).filter(
                    FAQCategory.order >= new_order,
                    FAQCategory.order < old_order,
                    FAQCategory.id != category_id
                ).update({FAQCategory.order: FAQCategory.order + 1}, synchronize_session=False)
            cat.order = new_order

    # is_active 수정
    if data.is_active is not None:
        cat.is_active = bool(data.is_active)

    db.commit()
    return MessageResponse(message="FAQ 카테고리가 수정되었습니다.", success=True)

@admin_router.delete("/faq-categories/{category_id}", response_model=MessageResponse)
async def admin_faq_category_delete_api(
    category_id: int,
    db: Session = Depends(get_db),
    admin_data: dict = Depends(get_admin_user)
):
    """FAQ 카테고리 삭제 (관리자)"""
    _ensure_admin(admin_data)
    
    cat = db.query(FAQCategory).filter(FAQCategory.id == category_id).first()
    if not cat:
        raise HTTPException(status_code=404, detail="FAQ 카테고리를 찾을 수 없습니다.")

    faq_count = db.query(FAQ).filter(
        FAQ.category_id == category_id, FAQ.is_deleted == False
    ).count()
    if faq_count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"이 카테고리를 사용하는 FAQ가 {faq_count}개 있습니다. 먼저 FAQ를 삭제하거나 다른 카테고리로 이동해주세요."
        )

    deleted_order = cat.order
    db.delete(cat)
    db.query(FAQCategory).filter(FAQCategory.order > deleted_order).update(
        {FAQCategory.order: FAQCategory.order - 1}
    )
    db.commit()
    return MessageResponse(message="FAQ 카테고리가 삭제되었습니다.", success=True)


# -------------------------
# 관리자: FAQ API
# -------------------------

@admin_router.get("/faq", response_model=FAQPageResponse)
async def admin_faq_list_api(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    search: Optional[str] = None,
    category_id: Optional[str] = None,
    db: Session = Depends(get_db),
    admin_data: dict = Depends(get_admin_user)
):
    """FAQ 목록 조회 (관리자)"""
    _ensure_admin(admin_data)

    q = db.query(FAQ).outerjoin(FAQCategory, FAQ.category_id == FAQCategory.id)
    q = q.filter(FAQ.is_deleted == False)

    if search:
        q = q.filter(or_(FAQ.question.contains(search), FAQ.answer.contains(search)))

    if category_id and str(category_id).strip():
        try:
            cid = int(category_id)
            q = q.filter(FAQ.category_id == cid)
        except ValueError:
            pass

    q = q.order_by(FAQ.order.asc(), FAQ.created_at.desc())
    total = q.count()

    # 페이지 보정
    if page < 1:
        page = 1
    total_pages = (total + limit - 1) // limit if total > 0 else 1
    if total_pages > 0 and page > total_pages:
        page = total_pages

    items = q.offset((page - 1) * limit).limit(limit).all()
    dto_items = [_to_faq_response(f) for f in items]

    return FAQPageResponse(
        items=dto_items,
        total=total,
        page=page,
        limit=limit,
        total_pages=total_pages
    )

@admin_router.get("/faq/{faq_id}", response_model=FAQResponse)
async def admin_faq_detail_api(
    faq_id: int,
    db: Session = Depends(get_db),
    admin_data: dict = Depends(get_admin_user)
):
    """FAQ 상세 조회 (관리자)"""
    _ensure_admin(admin_data)
    
    faq = db.query(FAQ).filter(FAQ.id == faq_id, FAQ.is_deleted == False).first()
    if not faq:
        raise HTTPException(status_code=404, detail="FAQ를 찾을 수 없습니다.")
    return _to_faq_response(faq)

@admin_router.post("/faq", response_model=MessageResponse)
async def admin_faq_create_api(
    data: FAQCreate,
    db: Session = Depends(get_db),
    admin_data: dict = Depends(get_admin_user)
):
    """FAQ 생성 (관리자)"""
    _ensure_admin(admin_data)
    
    question = data.question.strip()
    answer = data.answer.strip()
    category_id = data.category_id
    is_active = data.is_active

    if not question:
        raise HTTPException(status_code=400, detail="질문은 필수입니다.")
    if len(question) > 300:
        raise HTTPException(status_code=400, detail="질문은 300자 이하로 입력해주세요.")
    if not answer:
        raise HTTPException(status_code=400, detail="답변은 필수입니다.")

    # 자동 order 설정 (카테고리별 max+1)
    if category_id is not None and category_id != "":
        last = db.query(FAQ).filter(
            FAQ.category_id == category_id, FAQ.is_deleted == False
        ).order_by(FAQ.order.desc()).first()
        auto_order = (last.order + 1) if last else 1
        cat_id = category_id
    else:
        last = db.query(FAQ).filter(
            FAQ.category_id.is_(None), FAQ.is_deleted == False
        ).order_by(FAQ.order.desc()).first()
        auto_order = (last.order + 1) if last else 1
        cat_id = None

    faq = FAQ(
        question=question,
        answer=answer,
        category_id=cat_id,
        order=auto_order,
        is_active=is_active,
        created_by=admin_data['id']
    )
    db.add(faq)
    db.commit()
    db.refresh(faq)
    return MessageResponse(message="FAQ가 생성되었습니다", success=True)

@admin_router.put("/faq/{faq_id}", response_model=MessageResponse)
async def admin_faq_update_api(
    faq_id: int,
    data: FAQUpdate,
    db: Session = Depends(get_db),
    admin_data: dict = Depends(get_admin_user)
):
    """FAQ 수정 (관리자)"""
    _ensure_admin(admin_data)
    
    faq = db.query(FAQ).filter(FAQ.id == faq_id, FAQ.is_deleted == False).first()
    if not faq:
        raise HTTPException(status_code=404, detail="FAQ를 찾을 수 없습니다.")

    if data.question is not None:
        q = data.question.strip()
        if not q:
            raise HTTPException(status_code=400, detail="질문은 필수입니다.")
        if len(q) > 300:
            raise HTTPException(status_code=400, detail="질문은 300자 이하로 입력해주세요.")
        faq.question = q

    if data.answer is not None:
        a = data.answer.strip()
        if not a:
            raise HTTPException(status_code=400, detail="답변은 필수입니다.")
        faq.answer = a

    if data.category_id is not None:
        faq.category_id = data.category_id if data.category_id else None

    if data.order is not None:
        faq.order = int(data.order)

    if data.is_active is not None:
        faq.is_active = bool(data.is_active)

    db.commit()
    return MessageResponse(message="FAQ가 수정되었습니다.", success=True)

@admin_router.delete("/faq/{faq_id}", response_model=MessageResponse)
async def admin_faq_delete_api(
    faq_id: int,
    db: Session = Depends(get_db),
    admin_data: dict = Depends(get_admin_user)
):
    """FAQ 삭제 (관리자)"""
    _ensure_admin(admin_data)
    
    faq = db.query(FAQ).filter(FAQ.id == faq_id, FAQ.is_deleted == False).first()
    if not faq:
        raise HTTPException(status_code=404, detail="FAQ를 찾을 수 없습니다.")

    faq.is_deleted = True
    faq.deleted_at = datetime.now()
    db.commit()
    return MessageResponse(message="FAQ가 삭제되었습니다.", success=True)

@admin_router.patch("/faq/{faq_id}/toggle-active", response_model=MessageResponse)
async def admin_faq_toggle_active_api(
    faq_id: int,
    db: Session = Depends(get_db),
    admin_data: dict = Depends(get_admin_user)
):
    """FAQ 공개/비공개 토글 (관리자)"""
    _ensure_admin(admin_data)
    
    faq = db.query(FAQ).filter(FAQ.id == faq_id, FAQ.is_deleted == False).first()
    if not faq:
        raise HTTPException(status_code=404, detail="FAQ를 찾을 수 없습니다.")

    faq.is_active = not faq.is_active
    db.commit()
    status_text = "공개" if faq.is_active else "비공개"
    return MessageResponse(message=f"FAQ가 {status_text}로 변경되었습니다.", success=True)


# -------------------------
# 클라이언트: FAQ 조회 API
# -------------------------

@client_router.get("/faq", response_model=FAQPageResponse)
async def client_faq_list_api(
    page: int = Query(1, ge=1),
    limit: int = Query(5, ge=1, le=100),
    search: Optional[str] = None,
    category_id: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """FAQ 목록 조회 (클라이언트 - 공개만)"""
    q = db.query(FAQ).outerjoin(FAQCategory, FAQ.category_id == FAQCategory.id)
    q = q.filter(FAQ.is_deleted == False, FAQ.is_active == True)

    if search:
        q = q.filter(or_(FAQ.question.contains(search), FAQ.answer.contains(search)))

    if category_id and str(category_id).strip():
        try:
            cid = int(category_id)
            q = q.filter(FAQ.category_id == cid)
        except ValueError:
            pass

    q = q.order_by(FAQ.order.asc(), FAQ.created_at.desc())
    total = q.count()

    # 페이지 보정
    if page < 1:
        page = 1
    total_pages = (total + limit - 1) // limit if total > 0 else 1
    if total_pages > 0 and page > total_pages:
        page = total_pages

    items = q.offset((page - 1) * limit).limit(limit).all()
    dto_items = [_to_faq_response(f) for f in items]

    return FAQPageResponse(
        items=dto_items,
        total=total,
        page=page,
        limit=limit,
        total_pages=total_pages
    )

@client_router.get("/faq/{faq_id}", response_model=FAQResponse)
async def client_faq_detail_api(
    faq_id: int, db: Session = Depends(get_db)
):
    """FAQ 상세 조회 (클라이언트 - 공개만)"""
    faq = db.query(FAQ).filter(
        FAQ.id == faq_id, FAQ.is_deleted == False, FAQ.is_active == True
    ).first()
    if not faq:
        raise HTTPException(status_code=404, detail="FAQ를 찾을 수 없습니다.")
    
    # 조회수 증가
    faq.view_count = (faq.view_count or 0) + 1
    db.commit()
    
    return _to_faq_response(faq)

@client_router.get("/faq-categories", response_model=List[FAQCategoryResponse])
async def client_faq_categories_api(
    db: Session = Depends(get_db)
):
    """FAQ 카테고리 목록 조회 (클라이언트 - 활성만)"""
    cats = (
        db.query(FAQCategory)
        .filter(FAQCategory.is_active == True)
        .order_by(FAQCategory.order.asc())
        .all()
    )
    return [
        FAQCategoryResponse(
            id=c.id, title=c.title, order=c.order, is_active=c.is_active,
            created_at=c.created_at, updated_at=c.updated_at
        )
        for c in cats
    ]

