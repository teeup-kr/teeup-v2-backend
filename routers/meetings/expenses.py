# 비용 정산 API들 (모임 전용)
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

from database import get_db
from models import (
    User, Club, ClubMembership, Meeting,
    Expense, ExpenseItem, ExpenseItemParticipant, Guest, MeetingParticipant
)
from schemas import ClubRole
# Event 모델은 Phase 3에서 제거됨
from schemas import (
    ExpenseCreate, ExpenseUpdate, ExpenseResponse, ExpenseListResponse,
    ExpenseParticipantResponse, ExpenseParticipantUpdate, MessageResponse
)
from routers.auth import get_current_user, get_current_active_user

router = APIRouter(prefix="/meetings", tags=["비용 정산"])

# ===== 헬퍼 함수 =====

def _eip_to_response(eip: ExpenseItemParticipant, expense_id: int, db: Session) -> ExpenseParticipantResponse:
    """ExpenseItemParticipant를 ExpenseParticipantResponse로 변환"""
    if eip.guest_id:
        g = db.query(Guest).filter(Guest.id == eip.guest_id).first()
        return ExpenseParticipantResponse(
            id=eip.id, expense_id=expense_id, user_id=None, guest_id=eip.guest_id,
            user_name=g.name if g else "게스트", user_nickname=g.name if g else "게스트",
            is_guest=True, amount_paid=float(eip.amount_paid or 0) if eip.amount_paid else None,
            is_paid=eip.is_paid or False, paid_at=eip.paid_at, created_at=eip.created_at
        )
    else:
        u = db.query(User).filter(User.id == eip.user_id).first()
        return ExpenseParticipantResponse(
            id=eip.id, expense_id=expense_id, user_id=eip.user_id, guest_id=None,
            user_name=u.realname or u.nickname if u else "알 수 없음",
            user_nickname=u.nickname if u else "알 수 없음",
            is_guest=False, amount_paid=float(eip.amount_paid or 0) if eip.amount_paid else None,
            is_paid=eip.is_paid or False, paid_at=eip.paid_at, created_at=eip.created_at
        )


def _build_expense_response(expense: Expense, db: Session) -> ExpenseResponse:
    """Expense + ExpenseItem + ExpenseItemParticipant로 ExpenseResponse 구성"""
    items = db.query(ExpenseItem).filter(ExpenseItem.expense_id == expense.id).all()
    total_amount = sum(float(i.amount or 0) for i in items)
    seen = set()
    participant_responses = []
    for item in items:
        for eip in db.query(ExpenseItemParticipant).filter(ExpenseItemParticipant.expense_item_id == item.id).all():
            key = (eip.user_id, eip.guest_id)
            if key not in seen:
                seen.add(key)
                participant_responses.append(_eip_to_response(eip, expense.id, db))
    total_participants = len(participant_responses) or 1
    amount_per_person = total_amount / total_participants if total_participants else 0
    club = db.query(Club).filter(Club.id == expense.club_id).first()
    creator = db.query(User).filter(User.id == expense.created_by).first()
    return ExpenseResponse(
        id=expense.id, title=expense.title, description=expense.description,
        amount=total_amount, total_participants=total_participants, amount_per_person=amount_per_person,
        meeting_id=expense.meeting_id, club_id=expense.club_id, created_by=expense.created_by,
        creator_name=creator.nickname if creator else "알 수 없음",
        notes=expense.notes, created_at=expense.created_at, updated_at=expense.updated_at,
        participants=participant_responses,
    )

# ===== 모임 비용 정산 API =====

@router.get("/{meeting_id}/expenses", response_model=ExpenseListResponse)
async def get_meeting_expenses(
    meeting_id: int,
    page: int = 1,
    limit: int = 10,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_active_user)
):
    """모임 비용 목록 조회"""
    try:
        # 모임 조회 및 권한 확인
        meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
        if not meeting:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="모임을 찾을 수 없습니다."
            )
        
        # 관리자 권한 확인 (관리자는 모든 데이터 조회 가능)
        user_type = current_user.get('type', 'user')
        if user_type != 'admin':
            # 클럽 멤버 권한 확인
            membership = db.query(ClubMembership).filter(
                ClubMembership.club_id == meeting.club_id,
                ClubMembership.user_id == current_user.get('id')
            ).first()
            
            if not membership:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="클럽 멤버만 비용을 조회할 수 있습니다."
                )
        
        skip = (page - 1) * limit
        expenses = db.query(Expense).filter(Expense.meeting_id == meeting_id).order_by(Expense.created_at.desc()).offset(skip).limit(limit).all()
        total = db.query(Expense).filter(Expense.meeting_id == meeting_id).count()
        expense_responses = [_build_expense_response(e, db) for e in expenses]
        return ExpenseListResponse(expenses=expense_responses, total=total, page=page, limit=limit)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="서버 내부 오류가 발생했습니다."
        )

@router.post("/{meeting_id}/expenses", response_model=ExpenseResponse)
async def create_meeting_expense(
    meeting_id: int,
    expense_data: ExpenseCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_active_user)
):
    """모임 비용 등록"""
    try:
        # 모임 조회 및 권한 확인
        meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
        if not meeting:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="모임을 찾을 수 없습니다."
            )
        
        # 클럽 멤버 권한 확인
        membership = db.query(ClubMembership).filter(
            ClubMembership.club_id == meeting.club_id,
            ClubMembership.user_id == current_user.get('id')
        ).first()
        
        if not membership:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="클럽 멤버만 비용을 등록할 수 있습니다."
            )
        
        # 모임 비용 정산은 리더/매니저만 등록 가능
        if membership.role not in [ClubRole.LEADER, ClubRole.MANAGER]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="모임 비용 정산은 클럽 리더/매니저만 등록할 수 있습니다."
            )
        
        from models.enums import ExpenseItemType
        amount_per_person = expense_data.amount / expense_data.total_participants

        expense = Expense(
            title=expense_data.title,
            description=expense_data.description,
            meeting_id=meeting_id,
            club_id=meeting.club_id,
            created_by=current_user.get('id'),
            notes=expense_data.notes,
        )
        db.add(expense)
        db.flush()

        ei = ExpenseItem(
            expense_id=expense.id,
            type=ExpenseItemType.OTHER,
            title=expense_data.title,
            amount=expense_data.amount,
            covered_by_fee=False,
            order_index=0,
        )
        db.add(ei)
        db.flush()

        for participant_id in (expense_data.participant_ids or []):
            mp = db.query(MeetingParticipant).filter(
                MeetingParticipant.id == participant_id,
                MeetingParticipant.meeting_id == meeting_id
            ).first()
            if mp:
                db.add(ExpenseItemParticipant(
                    expense_item_id=ei.id,
                    user_id=mp.user_id,
                    guest_id=mp.guest_id,
                    is_exempted=False,
                    amount=amount_per_person,
                ))
        db.commit()
        db.refresh(expense)
        return _build_expense_response(expense, db)
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="서버 내부 오류가 발생했습니다."
        )

@router.get("/{meeting_id}/expenses/{expense_id}", response_model=ExpenseResponse)
async def get_meeting_expense(
    meeting_id: int,
    expense_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_active_user)
):
    """모임 비용 상세 조회"""
    try:
        # 모임 조회 및 권한 확인
        meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
        if not meeting:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="모임을 찾을 수 없습니다."
            )
        
        # 관리자 권한 확인 (관리자는 모든 데이터 조회 가능)
        user_type = current_user.get('type', 'user')
        if user_type != 'admin':
            # 클럽 멤버 권한 확인
            membership = db.query(ClubMembership).filter(
                ClubMembership.club_id == meeting.club_id,
                ClubMembership.user_id == current_user.get('id')
            ).first()
            
            if not membership:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="클럽 멤버만 비용을 조회할 수 있습니다."
                )
        
        # 비용 조회
        expense = db.query(Expense).filter(
            Expense.id == expense_id,
            Expense.meeting_id == meeting_id
        ).first()
        
        if not expense:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="비용을 찾을 수 없습니다."
            )
        
        return _build_expense_response(expense, db)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="서버 내부 오류가 발생했습니다."
        )

@router.put("/{meeting_id}/expenses/{expense_id}", response_model=ExpenseResponse)
async def update_meeting_expense(
    meeting_id: int,
    expense_id: int,
    expense_data: ExpenseUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_active_user)
):
    """모임 비용 수정"""
    try:
        # 모임 조회 및 권한 확인
        meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
        if not meeting:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="모임을 찾을 수 없습니다."
            )
        
        # 클럽 멤버 권한 확인
        membership = db.query(ClubMembership).filter(
            ClubMembership.club_id == meeting.club_id,
            ClubMembership.user_id == current_user.get('id')
        ).first()
        
        if not membership:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="클럽 멤버만 비용을 수정할 수 있습니다."
            )
        
        # 비용 조회
        expense = db.query(Expense).filter(
            Expense.id == expense_id,
            Expense.meeting_id == meeting_id
        ).first()
        
        if not expense:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="비용을 찾을 수 없습니다."
            )
        
        # 수정 권한 확인 (생성자 또는 리더/매니저)
        if expense.created_by != current_user.get('id') and membership.role not in [ClubRole.LEADER, ClubRole.MANAGER]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="비용을 수정할 권한이 없습니다."
            )
        
        if expense_data.title is not None:
            expense.title = expense_data.title
        if expense_data.description is not None:
            expense.description = expense_data.description
        if expense_data.notes is not None:
            expense.notes = expense_data.notes
        expense.updated_at = datetime.now()

        items = db.query(ExpenseItem).filter(ExpenseItem.expense_id == expense.id).all()
        if expense_data.amount is not None or expense_data.total_participants is not None:
            from models.enums import ExpenseItemType
            first_item = next((i for i in items if (i.type.value if hasattr(i.type, "value") else str(i.type)) == "OTHER"), items[0] if items else None)
            if first_item:
                if expense_data.amount is not None:
                    first_item.amount = expense_data.amount
                participants = db.query(ExpenseItemParticipant).filter(ExpenseItemParticipant.expense_item_id == first_item.id).all()
                n = expense_data.total_participants if expense_data.total_participants is not None else len(participants) or 1
                amt = float(expense_data.amount if expense_data.amount is not None else first_item.amount or 0)
                per_person = amt / n if n else 0
                for p in participants:
                    p.amount = per_person
        db.commit()
        db.refresh(expense)
        return _build_expense_response(expense, db)
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="서버 내부 오류가 발생했습니다."
        )

@router.delete("/{meeting_id}/expenses/{expense_id}", response_model=MessageResponse)
async def delete_meeting_expense(
    meeting_id: int,
    expense_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_active_user)
):
    """모임 비용 삭제"""
    try:
        # 모임 조회 및 권한 확인
        meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
        if not meeting:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="모임을 찾을 수 없습니다."
            )
        
        # 클럽 멤버 권한 확인
        membership = db.query(ClubMembership).filter(
            ClubMembership.club_id == meeting.club_id,
            ClubMembership.user_id == current_user.get('id')
        ).first()
        
        if not membership:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="클럽 멤버만 비용을 삭제할 수 있습니다."
            )
        
        # 비용 조회
        expense = db.query(Expense).filter(
            Expense.id == expense_id,
            Expense.meeting_id == meeting_id
        ).first()
        
        if not expense:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="비용을 찾을 수 없습니다."
            )
        
        # 삭제 권한 확인 (생성자 또는 리더/매니저)
        if expense.created_by != current_user.get('id') and membership.role not in [ClubRole.LEADER, ClubRole.MANAGER]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="비용을 삭제할 권한이 없습니다."
            )
        
        # 비용 삭제 (참가자도 함께 삭제됨 - cascade)
        db.delete(expense)
        db.commit()
        
        return {
            "message": "비용이 삭제되었습니다.",
            "success": True
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="서버 내부 오류가 발생했습니다."
        )

@router.get("/{meeting_id}/expenses/{expense_id}/participants", response_model=List[ExpenseParticipantResponse])
async def get_expense_participants(
    meeting_id: int,
    expense_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_active_user)
):
    """비용 참가자 목록 조회"""
    try:
        # 모임 조회 및 권한 확인
        meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
        if not meeting:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="모임을 찾을 수 없습니다."
            )
        
        # 관리자 권한 확인 (관리자는 모든 데이터 조회 가능)
        user_type = current_user.get('type', 'user')
        if user_type != 'admin':
            # 클럽 멤버 권한 확인
            membership = db.query(ClubMembership).filter(
                ClubMembership.club_id == meeting.club_id,
                ClubMembership.user_id == current_user.get('id')
            ).first()
            
            if not membership:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="클럽 멤버만 참가자 목록을 조회할 수 있습니다."
                )
        
        # 비용 조회
        expense = db.query(Expense).filter(
            Expense.id == expense_id,
            Expense.meeting_id == meeting_id
        ).first()
        
        if not expense:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="비용을 찾을 수 없습니다."
            )
        
        resp = _build_expense_response(expense, db)
        return resp.participants or []
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="서버 내부 오류가 발생했습니다."
        )

@router.put("/{meeting_id}/expenses/{expense_id}/participants/{participant_id}", response_model=ExpenseParticipantResponse)
async def update_expense_participant(
    meeting_id: int,
    expense_id: int,
    participant_id: int,
    participant_data: ExpenseParticipantUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_active_user)
):
    """비용 참가자 상태 변경"""
    try:
        # 모임 조회 및 권한 확인
        meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
        if not meeting:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="모임을 찾을 수 없습니다."
            )
        
        # 클럽 멤버 권한 확인
        membership = db.query(ClubMembership).filter(
            ClubMembership.club_id == meeting.club_id,
            ClubMembership.user_id == current_user.get('id')
        ).first()
        
        if not membership:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="클럽 멤버만 참가자 상태를 변경할 수 있습니다."
            )
        
        # 비용 조회
        expense = db.query(Expense).filter(
            Expense.id == expense_id,
            Expense.meeting_id == meeting_id
        ).first()
        
        if not expense:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="비용을 찾을 수 없습니다."
            )
        
        participant = db.query(ExpenseItemParticipant).filter(
            ExpenseItemParticipant.id == participant_id
        ).first()
        if not participant:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="참가자를 찾을 수 없습니다.")
        item = db.query(ExpenseItem).filter(ExpenseItem.id == participant.expense_item_id, ExpenseItem.expense_id == expense_id).first()
        if not item:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="참가자를 찾을 수 없습니다.")
        if participant.user_id != current_user.get('id') and membership.role not in [ClubRole.LEADER, ClubRole.MANAGER]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="참가자 상태를 변경할 권한이 없습니다.")
        if participant_data.amount_paid is not None:
            participant.amount_paid = participant_data.amount_paid
        if participant_data.is_paid is not None:
            participant.is_paid = participant_data.is_paid
            if participant_data.is_paid:
                participant.paid_at = datetime.now()
        db.commit()
        db.refresh(participant)
        return _eip_to_response(participant, expense_id, db)
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="서버 내부 오류가 발생했습니다."
        )

# ===== 레거시 이벤트 비용 정산 API (Phase 3에서 Event 모델 제거됨) =====
# /events/ 엔드포인트들은 더 이상 작동하지 않음
# 소셜 모임 비용은 /expenses/meetings/{meeting_id}를 사용하세요
