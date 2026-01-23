from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, asc
from typing import List, Optional
from datetime import datetime
import logging

from database import get_db
from models import Inquiry, InquiryResponse, User
from schemas import InquiryType, InquiryStatus
from schemas import (
    InquiryCreate, InquiryUpdate, InquiryResponse as InquiryResponseSchema,
    InquiryListResponse, InquiryResponseCreate, InquiryResponseUpdate,
    InquiryResponseResponse, InquiryDetailResponse
)
from routers.auth import get_current_user
from utils import generate_id

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/inquiries", tags=["inquiries"])


@router.get("/", response_model=InquiryListResponse)
async def get_inquiries(
    page: int = Query(1, ge=1, description="페이지 번호"),
    size: int = Query(20, ge=1, le=100, description="페이지 크기"),
    type: Optional[str] = Query(None, description="문의 타입"),
    status: Optional[str] = Query(None, description="문의 상태"),
    priority: Optional[int] = Query(None, description="우선순위"),
    search: Optional[str] = Query(None, description="제목 검색"),
    user_id: Optional[int] = Query(None, description="사용자 ID (관리자만)"),
    current_user = Depends(lambda: get_current_user(required_type="admin", check_status=False)),
    db: Session = Depends(get_db)
):
    """문의 목록 조회 (관리자)"""
    try:
        query = db.query(Inquiry)
        
        # 필터 적용
        if type:
            query = query.filter(Inquiry.type == type)
        if status:
            query = query.filter(Inquiry.status == status)
        if priority:
            query = query.filter(Inquiry.priority == priority)
        if search:
            query = query.filter(Inquiry.title.contains(search))
        if user_id:
            query = query.filter(Inquiry.user_id == user_id)
        
        # 총 개수 조회
        total = query.count()
        
        # 정렬 및 페이징 (우선순위 높은 순, 최신 순)
        inquiries = query.order_by(desc(Inquiry.priority), desc(Inquiry.created_at))\
                        .offset((page - 1) * size)\
                        .limit(size)\
                        .all()
        
        # JOIN을 사용한 최적화된 쿼리로 사용자 정보를 한 번에 조회
        inquiries_with_users = db.query(
            Inquiry,
            User.nickname
        ).outerjoin(
            User, Inquiry.user_id == User.id
        ).filter(
            Inquiry.id.in_([inquiry.id for inquiry in inquiries])
        ).all()
        
        # 응답 데이터 변환
        inquiry_responses = []
        for inquiry, user_nickname in inquiries_with_users:
            inquiry_responses.append(InquiryResponseSchema(
                id=inquiry.id,                user_id=inquiry.user_id,
                user_nickname=user_nickname if user_nickname else "알 수 없음",
                title=inquiry.title,
                content=inquiry.content,
                type=inquiry.type.value,
                status=inquiry.status.value,
                priority=inquiry.priority,
                created_at=inquiry.created_at,
                updated_at=inquiry.updated_at
            ))
        
        return InquiryListResponse(
            inquiries=inquiry_responses,
            total=total,
            page=page,
            size=size
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"문의 목록 조회 실패: {str(e)}")


@router.post("/", response_model=InquiryResponseSchema)
async def create_inquiry(
    inquiry_data: InquiryCreate,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """문의 등록"""
    try:
        # 문의 생성
        inquiry = Inquiry(
            user_id=current_user.id,
            title=inquiry_data.title,
            content=inquiry_data.content,
            type=InquiryType(inquiry_data.type),
            priority=inquiry_data.priority
        )
        
        db.add(inquiry)
        db.commit()
        db.refresh(inquiry)
        
        # 관리자에게 새 문의 등록 알림 전송
        try:
            from utils.notification_service import create_inquiry_admin_notification
            create_inquiry_admin_notification(
                db=db,
                inquiry_title=inquiry_data.title,
                inquiry_type=inquiry_data.type,
                user_name=current_user.nickname,
                inquiry_id=inquiry.id
            )
        except Exception as e:
            logger.error(f"관리자 문의 등록 알림 전송 실패: {str(e)}")
        
        return InquiryResponseSchema(
            id=inquiry.id,            user_id=inquiry.user_id,
            user_nickname=inquiry.user.nickname,
            title=inquiry.title,
            content=inquiry.content,
            type=inquiry.type.value,
            status=inquiry.status.value,
            priority=inquiry.priority,
            created_at=inquiry.created_at,
            updated_at=inquiry.updated_at
        )
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"문의 등록 실패: {str(e)}")


@router.get("/{inquiry_id}", response_model=InquiryDetailResponse)
async def get_inquiry(
    inquiry_id: int,
    current_user = Depends(lambda: get_current_user(required_type="admin", check_status=False)),
    db: Session = Depends(get_db)
):
    """문의 상세 조회 (관리자)"""
    try:
        inquiry = db.query(Inquiry).filter(Inquiry.id == inquiry_id).first()
        if not inquiry:
            raise HTTPException(status_code=404, detail="문의를 찾을 수 없습니다")
        
        # 답변 목록 조회
        responses = db.query(InquiryResponse).filter(
            InquiryResponse.inquiry_id == inquiry_id
        ).order_by(asc(InquiryResponse.created_at)).all()
        
        # 응답 데이터 변환
        inquiry_response = InquiryResponseSchema(
            id=inquiry.id,            user_id=inquiry.user_id,
            user_nickname=inquiry.user.nickname if inquiry.user else "알 수 없음",
            title=inquiry.title,
            content=inquiry.content,
            type=inquiry.type.value,
            status=inquiry.status.value,
            priority=inquiry.priority,
            created_at=inquiry.created_at,
            updated_at=inquiry.updated_at
        )
        
        response_responses = []
        for response in responses:
            response_responses.append(InquiryResponseResponse(
                id=response.id,                inquiry_id=response.inquiry_id,
                admin_id=response.admin_id,
                admin_nickname=response.admin.nickname if response.admin else "알 수 없음",
                content=response.content,
                is_internal=response.is_internal,
                created_at=response.created_at,
                updated_at=response.updated_at
            ))
        
        return InquiryDetailResponse(
            inquiry=inquiry_response,
            responses=response_responses
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"문의 조회 실패: {str(e)}")


@router.put("/{inquiry_id}", response_model=InquiryResponseSchema)
async def update_inquiry(
    inquiry_id: int,
    inquiry_data: InquiryUpdate,
    current_user = Depends(lambda: get_current_user(required_type="admin", check_status=False)),
    db: Session = Depends(get_db)
):
    """문의 수정 (관리자)"""
    try:
        inquiry = db.query(Inquiry).filter(Inquiry.id == inquiry_id).first()
        if not inquiry:
            raise HTTPException(status_code=404, detail="문의를 찾을 수 없습니다")
        
        # 업데이트할 필드만 수정
        update_data = inquiry_data.dict(exclude_unset=True)
        for field, value in update_data.items():
            if field == "type":
                setattr(inquiry, field, InquiryType(value))
            elif field == "status":
                setattr(inquiry, field, InquiryStatus(value))
            else:
                setattr(inquiry, field, value)
        
        inquiry.updated_at = datetime.now()
        
        db.commit()
        db.refresh(inquiry)
        
        return InquiryResponseSchema(
            id=inquiry.id,            user_id=inquiry.user_id,
            user_nickname=inquiry.user.nickname,
            title=inquiry.title,
            content=inquiry.content,
            type=inquiry.type.value,
            status=inquiry.status.value,
            priority=inquiry.priority,
            created_at=inquiry.created_at,
            updated_at=inquiry.updated_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"문의 수정 실패: {str(e)}")


@router.post("/{inquiry_id}/responses", response_model=InquiryResponseResponse)
async def create_inquiry_response(
    inquiry_id: int,
    response_data: InquiryResponseCreate,
    current_user = Depends(lambda: get_current_user(required_type="admin", check_status=False)),
    db: Session = Depends(get_db)
):
    """문의 답변 등록 (관리자)"""
    try:
        # 문의 존재 확인
        inquiry = db.query(Inquiry).filter(Inquiry.id == inquiry_id).first()
        if not inquiry:
            raise HTTPException(status_code=404, detail="문의를 찾을 수 없습니다")
        
        # 답변 생성
        response = InquiryResponse(
            inquiry_id=inquiry_id,
            admin_id=current_user.id,
            content=response_data.content,
            is_internal=response_data.is_internal
        )
        
        db.add(response)
        
        # 문의 상태를 처리중으로 변경 (내부 메모가 아닌 경우)
        if not response_data.is_internal and inquiry.status == InquiryStatus.PENDING:
            inquiry.status = InquiryStatus.IN_PROGRESS
            inquiry.updated_at = datetime.now()
        
        db.commit()
        db.refresh(response)
        
        return InquiryResponseResponse(
            id=response.id,            inquiry_id=response.inquiry_id,
            admin_id=response.admin_id,
            admin_nickname=response.admin.nickname,
            content=response.content,
            is_internal=response.is_internal,
            created_at=response.created_at,
            updated_at=response.updated_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"문의 답변 등록 실패: {str(e)}")


@router.put("/{inquiry_id}/responses/{response_id}", response_model=InquiryResponseResponse)
async def update_inquiry_response(
    inquiry_id: int,
    response_id: int,
    response_data: InquiryResponseUpdate,
    current_user = Depends(lambda: get_current_user(required_type="admin", check_status=False)),
    db: Session = Depends(get_db)
):
    """문의 답변 수정 (관리자)"""
    try:
        response = db.query(InquiryResponse).filter(
            InquiryResponse.id == response_id,
            InquiryResponse.inquiry_id == inquiry_id
        ).first()
        if not response:
            raise HTTPException(status_code=404, detail="답변을 찾을 수 없습니다")
        
        # 업데이트할 필드만 수정
        update_data = response_data.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(response, field, value)
        
        response.updated_at = datetime.now()
        
        db.commit()
        db.refresh(response)
        
        return InquiryResponseResponse(
            id=response.id,            inquiry_id=response.inquiry_id,
            admin_id=response.admin_id,
            admin_nickname=response.admin.nickname,
            content=response.content,
            is_internal=response.is_internal,
            created_at=response.created_at,
            updated_at=response.updated_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"문의 답변 수정 실패: {str(e)}")


@router.delete("/{inquiry_id}/responses/{response_id}")
async def delete_inquiry_response(
    inquiry_id: int,
    response_id: int,
    current_user = Depends(lambda: get_current_user(required_type="admin", check_status=False)),
    db: Session = Depends(get_db)
):
    """문의 답변 삭제 (관리자)"""
    try:
        response = db.query(InquiryResponse).filter(
            InquiryResponse.id == response_id,
            InquiryResponse.inquiry_id == inquiry_id
        ).first()
        if not response:
            raise HTTPException(status_code=404, detail="답변을 찾을 수 없습니다")
        
        db.delete(response)
        db.commit()
        
        return {"message": "답변이 삭제되었습니다"}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"문의 답변 삭제 실패: {str(e)}")


@router.get("/types/", response_model=List[dict])
async def get_inquiry_types():
    """문의 타입 목록 조회"""
    return [
        {"id": "GENERAL", "name": "일반 문의"},
        {"id": "TECHNICAL", "name": "기술 문의"},
        {"id": "BUG_REPORT", "name": "버그 신고"},
        {"id": "FEATURE_REQUEST", "name": "기능 요청"},
        {"id": "ACCOUNT", "name": "계정 문의"},
        {"id": "PAYMENT", "name": "결제 문의"}
    ]


@router.get("/statuses/", response_model=List[dict])
async def get_inquiry_statuses():
    """문의 상태 목록 조회"""
    return [
        {"id": "PENDING", "name": "대기중"},
        {"id": "IN_PROGRESS", "name": "처리중"},
        {"id": "COMPLETED", "name": "완료"},
        {"id": "CLOSED", "name": "종료"}
    ]
