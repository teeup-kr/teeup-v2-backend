"""
요금제 관리 API 라우터
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
import logging

from database import get_db
from models import Plan
from schemas import PlanType, BillingCycle
from schemas import PlanCreate, PlanUpdate, PlanResponse, MessageResponse
from routers.auth import get_current_user
from utils.permissions import PermissionChecker

# 로깅 설정
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/plans", tags=["plans"])

@router.get("/", response_model=List[PlanResponse])
async def get_plans(
    is_active: Optional[bool] = None,
    plan_type: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """요금제 목록 조회"""
    try:
        logger.info(f"요금제 목록 조회 시작 - user_id: {current_user.get('id')}")
        
        query = db.query(Plan)
        
        if is_active is not None:
            query = query.filter(Plan.is_active == is_active)
        
        if plan_type:
            query = query.filter(Plan.type == plan_type)
        
        plans = query.order_by(Plan.price.asc()).all()
        
        plan_responses = []
        for plan in plans:
            plan_response = PlanResponse(
                id=plan.id,                name=plan.name,
                description=plan.description,
                type=plan.type.value,
                price=float(plan.price),
                billing_cycle=plan.billing_cycle.value,
                features=plan.features,
                max_clubs=plan.max_clubs,
                max_members_per_club=plan.max_members_per_club,
                max_meetings_per_month=plan.max_meetings_per_month,
                is_active=plan.is_active,
                created_at=plan.created_at,
                updated_at=plan.updated_at
            )
            plan_responses.append(plan_response)
        
        logger.info(f"요금제 목록 조회 완료 - 총 {len(plan_responses)}개")
        return plan_responses
        
    except Exception as e:
        logger.error(f"요금제 목록 조회 중 오류: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"서버 오류: {str(e)}"
        )

@router.get("/{plan_id}", response_model=PlanResponse)
async def get_plan(
    plan_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """요금제 상세 조회"""
    try:
        logger.info(f"요금제 상세 조회 시작 - plan_id: {plan_id}")
        
        plan = db.query(Plan).filter(Plan.id == plan_id).first()
        if not plan:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="요금제를 찾을 수 없습니다"
            )
        
        plan_response = PlanResponse(
            id=plan.id,            name=plan.name,
            description=plan.description,
            type=plan.type.value,
            price=float(plan.price),
            billing_cycle=plan.billing_cycle.value,
            features=plan.features,
            max_clubs=plan.max_clubs,
            max_members_per_club=plan.max_members_per_club,
            max_meetings_per_month=plan.max_meetings_per_month,
            is_active=plan.is_active,
            created_at=plan.created_at,
            updated_at=plan.updated_at
        )
        
        logger.info(f"요금제 상세 조회 완료 - plan_id: {plan_id}")
        return plan_response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"요금제 상세 조회 중 오류: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"서버 오류: {str(e)}"
        )

@router.post("/", response_model=PlanResponse)
async def create_plan(
    plan_data: PlanCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """요금제 생성 (관리자만 가능)"""
    try:
        logger.info(f"요금제 생성 시작 - user_id: {current_user.get('id')}")
        
        # 관리자 권한 확인 (임시로 모든 사용자 허용)
        # 관리자 권한 확인
        if not PermissionChecker.check_admin_permission(current_user, db):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="관리자 권한이 필요합니다"
            )
        
        # 요금제 생성
        import secrets
        import string
        chars = string.ascii_lowercase + string.digits
        plan_id = ''.join(secrets.choice(chars) for _ in range(20))
        
        plan = Plan(
            id=plan_id,
            name=plan_data.name,
            description=plan_data.description,
            type=PlanType(plan_data.type),
            price=plan_data.price,
            billing_cycle=BillingCycle(plan_data.billing_cycle),
            features=plan_data.features,
            max_clubs=plan_data.max_clubs,
            max_members_per_club=plan_data.max_members_per_club,
            max_meetings_per_month=plan_data.max_meetings_per_month,
            is_active=True
        )
        
        db.add(plan)
        db.commit()
        db.refresh(plan)
        
        plan_response = PlanResponse(
            id=plan.id,            name=plan.name,
            description=plan.description,
            type=plan.type.value,
            price=float(plan.price),
            billing_cycle=plan.billing_cycle.value,
            features=plan.features,
            max_clubs=plan.max_clubs,
            max_members_per_club=plan.max_members_per_club,
            max_meetings_per_month=plan.max_meetings_per_month,
            is_active=plan.is_active,
            created_at=plan.created_at,
            updated_at=plan.updated_at
        )
        
        logger.info(f"요금제 생성 완료 - plan_id: {plan.id}")
        return plan_response
        
    except Exception as e:
        logger.error(f"요금제 생성 중 오류: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"서버 오류: {str(e)}"
        )

@router.put("/{plan_id}", response_model=PlanResponse)
async def update_plan(
    plan_id: int,
    plan_data: PlanUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """요금제 수정 (관리자만 가능)"""
    try:
        logger.info(f"요금제 수정 시작 - plan_id: {plan_id}")
        
        # 요금제 조회
        plan = db.query(Plan).filter(Plan.id == plan_id).first()
        if not plan:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="요금제를 찾을 수 없습니다"
            )
        
        # 관리자 권한 확인 (임시로 모든 사용자 허용)
        # 관리자 권한 확인
        if not PermissionChecker.check_admin_permission(current_user, db):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="관리자 권한이 필요합니다"
            )
        
        # 요금제 정보 업데이트
        update_data = plan_data.dict(exclude_unset=True)
        for field, value in update_data.items():
            if field == "type" and value:
                setattr(plan, field, PlanType(value))
            elif field == "billing_cycle" and value:
                setattr(plan, field, BillingCycle(value))
            else:
                setattr(plan, field, value)
        
        db.commit()
        db.refresh(plan)
        
        plan_response = PlanResponse(
            id=plan.id,            name=plan.name,
            description=plan.description,
            type=plan.type.value,
            price=float(plan.price),
            billing_cycle=plan.billing_cycle.value,
            features=plan.features,
            max_clubs=plan.max_clubs,
            max_members_per_club=plan.max_members_per_club,
            max_meetings_per_month=plan.max_meetings_per_month,
            is_active=plan.is_active,
            created_at=plan.created_at,
            updated_at=plan.updated_at
        )
        
        logger.info(f"요금제 수정 완료 - plan_id: {plan_id}")
        return plan_response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"요금제 수정 중 오류: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"서버 오류: {str(e)}"
        )

@router.delete("/{plan_id}", response_model=MessageResponse)
async def delete_plan(
    plan_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """요금제 삭제 (관리자만 가능)"""
    try:
        logger.info(f"요금제 삭제 시작 - plan_id: {plan_id}")
        
        # 요금제 조회
        plan = db.query(Plan).filter(Plan.id == plan_id).first()
        if not plan:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="요금제를 찾을 수 없습니다"
            )
        
        # 관리자 권한 확인 (임시로 모든 사용자 허용)
        # 관리자 권한 확인
        if not PermissionChecker.check_admin_permission(current_user, db):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="관리자 권한이 필요합니다"
            )
        
        # 활성 구독이 있는지 확인
        from models import Subscription
        active_subscriptions = db.query(Subscription).filter(
            Subscription.plan_id == plan_id,
            Subscription.status == "ACTIVE"
        ).count()
        
        if active_subscriptions > 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="활성 구독이 있는 요금제는 삭제할 수 없습니다"
            )
        
        # 요금제 삭제
        db.delete(plan)
        db.commit()
        
        logger.info(f"요금제 삭제 완료 - plan_id: {plan_id}")
        return MessageResponse(
            message="요금제가 성공적으로 삭제되었습니다",
            success=True
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"요금제 삭제 중 오류: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"서버 오류: {str(e)}"
        )


