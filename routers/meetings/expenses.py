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
    Expense, ExpenseParticipant, Guest, MeetingParticipant
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

def build_expense_participant_response(participant: ExpenseParticipant, db: Session) -> ExpenseParticipantResponse:
    """ExpenseParticipant를 ExpenseParticipantResponse로 변환 (게스트 지원)"""
    if participant.guest_id:
        # 게스트인 경우
        guest = db.query(Guest).filter(Guest.id == participant.guest_id).first()
        return ExpenseParticipantResponse(
            id=participant.id,
            expense_id=participant.expense_id,
            user_id=None,
            guest_id=participant.guest_id,
            user_name=guest.name if guest else "게스트",
            user_nickname=guest.name if guest else "게스트",
            is_guest=True,
            amount_paid=float(participant.amount_paid) if participant.amount_paid else None,
            is_paid=participant.is_paid,
            paid_at=participant.paid_at,
            created_at=participant.created_at
        )
    else:
        # 일반 사용자인 경우
        user = db.query(User).filter(User.id == participant.user_id).first()
        return ExpenseParticipantResponse(
            id=participant.id,
            expense_id=participant.expense_id,
            user_id=participant.user_id,
            guest_id=None,
            user_name=user.realname or user.nickname if user else "알 수 없음",
            user_nickname=user.nickname if user else "알 수 없음",
            is_guest=False,
            amount_paid=float(participant.amount_paid) if participant.amount_paid else None,
            is_paid=participant.is_paid,
            paid_at=participant.paid_at,
            created_at=participant.created_at
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
        
        # 비용 목록 조회
        skip = (page - 1) * limit
        expenses = db.query(Expense).filter(
            Expense.meeting_id == meeting_id
        ).order_by(Expense.created_at.desc()).offset(skip).limit(limit).all()
        
        total = db.query(Expense).filter(Expense.meeting_id == meeting_id).count()
        
        # 응답 데이터 구성
        expense_responses = []
        for expense in expenses:
            # 참가자 정보 조회
            participants = db.query(ExpenseParticipant).filter(
                ExpenseParticipant.expense_id == expense.id
            ).all()
            
            participant_responses = []
            for participant in participants:
                participant_responses.append(build_expense_participant_response(participant, db))
            
            # 클럽 정보 조회
            club = db.query(Club).filter(Club.id == expense.club_id).first()
            creator = db.query(User).filter(User.id == expense.created_by).first()
            
            expense_responses.append(ExpenseResponse(
                id=expense.id,                title=expense.title,
                description=expense.description,
                amount=float(expense.amount),
                total_participants=expense.total_participants,
                amount_per_person=float(expense.amount_per_person),
                meeting_id=expense.meeting_id,
                # event_id=expense.event_id,  # 레거시 필드 (Phase 3에서 Event 모델 제거됨)
                club_id=expense.club_id,
                club_name=club.name if club else "알 수 없음",
                created_by=expense.created_by,
                creator_nickname=creator.nickname if creator else "알 수 없음",
                status=expense.status,
                settled_at=expense.settled_at,
                notes=expense.notes,
                participants=participant_responses,
                created_at=expense.created_at,
                updated_at=expense.updated_at
            ))
        
        return ExpenseListResponse(
            expenses=expense_responses,
            total=total,
            page=page,
            size=limit
        )
        
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
        
        # 1인당 비용 계산
        amount_per_person = expense_data.amount / expense_data.total_participants
        
        # 비용 생성
        expense = Expense(
            title=expense_data.title,
            description=expense_data.description,
            amount=expense_data.amount,
            total_participants=expense_data.total_participants,
            amount_per_person=amount_per_person,
            meeting_id=meeting_id,
            club_id=meeting.club_id,
            created_by=current_user.get('id'),
            notes=expense_data.notes
        )
        
        db.add(expense)
        db.flush()  # ID 생성
        
        # 참가자 생성 (MeetingParticipant를 조회하여 user_id 또는 guest_id 설정)
        for participant_id in expense_data.participant_ids:
            # MeetingParticipant 조회
            meeting_participant = db.query(MeetingParticipant).filter(
                MeetingParticipant.id == participant_id,
                MeetingParticipant.meeting_id == meeting_id
            ).first()
            
            if not meeting_participant:
                continue
            
            # 게스트인 경우와 일반 사용자인 경우 구분
            if meeting_participant.guest_id:
                participant = ExpenseParticipant(
                    expense_id=expense.id,
                    user_id=None,
                    guest_id=meeting_participant.guest_id,
                    amount_paid=amount_per_person
                )
            else:
                participant = ExpenseParticipant(
                    expense_id=expense.id,
                    user_id=meeting_participant.user_id,
                    guest_id=None,
                    amount_paid=amount_per_person
                )
            db.add(participant)
        
        db.commit()
        
        # 응답 데이터 구성
        participants = db.query(ExpenseParticipant).filter(
            ExpenseParticipant.expense_id == expense.id
        ).all()
        
        participant_responses = []
        for participant in participants:
            participant_responses.append(build_expense_participant_response(participant, db))
        
        club = db.query(Club).filter(Club.id == expense.club_id).first()
        creator = db.query(User).filter(User.id == expense.created_by).first()
        
        return ExpenseResponse(
            id=expense.id,            title=expense.title,
            description=expense.description,
            amount=float(expense.amount),
            total_participants=expense.total_participants,
            amount_per_person=float(expense.amount_per_person),
            meeting_id=expense.meeting_id,
            # event_id=expense.event_id,  # 레거시 필드 (Phase 4에서 제거)
            club_id=expense.club_id,
            club_name=club.name if club else "알 수 없음",
            created_by=expense.created_by,
            creator_nickname=creator.nickname if creator else "알 수 없음",
            status=expense.status,
            settled_at=expense.settled_at,
            notes=expense.notes,
            participants=participant_responses,
            created_at=expense.created_at,
            updated_at=expense.updated_at
        )
        
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
        
        # 참가자 정보 조회
        participants = db.query(ExpenseParticipant).filter(
            ExpenseParticipant.expense_id == expense.id
        ).all()
        
        participant_responses = []
        for participant in participants:
            participant_responses.append(build_expense_participant_response(participant, db))
        
        club = db.query(Club).filter(Club.id == expense.club_id).first()
        creator = db.query(User).filter(User.id == expense.created_by).first()
        
        return ExpenseResponse(
            id=expense.id,            title=expense.title,
            description=expense.description,
            amount=float(expense.amount),
            total_participants=expense.total_participants,
            amount_per_person=float(expense.amount_per_person),
            meeting_id=expense.meeting_id,
            # event_id=expense.event_id,  # 레거시 필드 (Phase 4에서 제거)
            club_id=expense.club_id,
            club_name=club.name if club else "알 수 없음",
            created_by=expense.created_by,
            creator_nickname=creator.nickname if creator else "알 수 없음",
            status=expense.status,
            settled_at=expense.settled_at,
            notes=expense.notes,
            participants=participant_responses,
            created_at=expense.created_at,
            updated_at=expense.updated_at
        )
        
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
        
        # 비용 수정
        if expense_data.title is not None:
            expense.title = expense_data.title
        if expense_data.description is not None:
            expense.description = expense_data.description
        if expense_data.amount is not None:
            expense.amount = expense_data.amount
            # 1인당 비용 재계산
            expense.amount_per_person = expense_data.amount / expense.total_participants
        if expense_data.total_participants is not None:
            expense.total_participants = expense_data.total_participants
            # 1인당 비용 재계산
            expense.amount_per_person = expense.amount / expense_data.total_participants
        if expense_data.status is not None:
            expense.status = expense_data.status
            if expense_data.status == "SETTLED":
                expense.settled_at = datetime.now()
        if expense_data.notes is not None:
            expense.notes = expense_data.notes
        
        expense.updated_at = datetime.now()
        
        db.commit()
        
        # 응답 데이터 구성 (상세 조회와 동일)
        participants = db.query(ExpenseParticipant).filter(
            ExpenseParticipant.expense_id == expense.id
        ).all()
        
        participant_responses = []
        for participant in participants:
            participant_responses.append(build_expense_participant_response(participant, db))
        
        club = db.query(Club).filter(Club.id == expense.club_id).first()
        creator = db.query(User).filter(User.id == expense.created_by).first()
        
        return ExpenseResponse(
            id=expense.id,            title=expense.title,
            description=expense.description,
            amount=float(expense.amount),
            total_participants=expense.total_participants,
            amount_per_person=float(expense.amount_per_person),
            meeting_id=expense.meeting_id,
            # event_id=expense.event_id,  # 레거시 필드 (Phase 4에서 제거)
            club_id=expense.club_id,
            club_name=club.name if club else "알 수 없음",
            created_by=expense.created_by,
            creator_nickname=creator.nickname if creator else "알 수 없음",
            status=expense.status,
            settled_at=expense.settled_at,
            notes=expense.notes,
            participants=participant_responses,
            created_at=expense.created_at,
            updated_at=expense.updated_at
        )
        
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
        
        # 참가자 목록 조회
        participants = db.query(ExpenseParticipant).filter(
            ExpenseParticipant.expense_id == expense_id
        ).all()
        
        participant_responses = []
        for participant in participants:
            participant_responses.append(build_expense_participant_response(participant, db))
        
        return participant_responses
        
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
        
        # 참가자 조회
        participant = db.query(ExpenseParticipant).filter(
            ExpenseParticipant.id == participant_id,
            ExpenseParticipant.expense_id == expense_id
        ).first()
        
        if not participant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="참가자를 찾을 수 없습니다."
            )
        
        # 수정 권한 확인 (본인 또는 리더/매니저)
        if participant.user_id != current_user.get('id') and membership.role not in [ClubRole.LEADER, ClubRole.MANAGER]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="참가자 상태를 변경할 권한이 없습니다."
            )
        
        # 참가자 상태 수정
        if participant_data.amount_paid is not None:
            participant.amount_paid = participant_data.amount_paid
        if participant_data.status is not None:
            participant.status = participant_data.status
            if participant_data.status == "PAID":
                participant.paid_at = datetime.now()
        if participant_data.notes is not None:
            participant.notes = participant_data.notes
        
        participant.updated_at = datetime.now()
        
        db.commit()
        
        # 응답 데이터 구성
        return build_expense_participant_response(participant, db)
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="서버 내부 오류가 발생했습니다."
        )

# ===== 모임 비용 조회 엔드포인트 (base.py에서 이동) =====

@router.get("/{meeting_id}/expenses", response_model=ExpenseListResponse)
async def get_meeting_expenses(
    meeting_id: int,
    page: int = 1,
    limit: int = 10,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """모임 비용 정산 목록 조회"""
    try:
        # 모임 존재 확인
        meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
        if not meeting:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="모임을 찾을 수 없습니다."
            )
        
        # 페이지네이션 계산
        offset = (page - 1) * limit
        
        # 비용 정산 조회
        expenses_query = db.query(Expense).filter(Expense.meeting_id == meeting_id)
        total = expenses_query.count()
        expenses = expenses_query.order_by(Expense.created_at.desc()).offset(offset).limit(limit).all()
        
        expense_responses = []
        for expense in expenses:
            # 클럽 정보 조회
            club = db.query(Club).filter(Club.id == expense.club_id).first()
            
            # 생성자 정보 조회
            creator = db.query(User).filter(User.id == expense.created_by).first()
            
            # 참가자 정보 조회
            participants = db.query(ExpenseParticipant, User).join(
                User, ExpenseParticipant.user_id == User.id
            ).filter(ExpenseParticipant.expense_id == expense.id).all()
            
            participant_responses = []
            for expense_participant, user in participants:
                participant_responses.append(ExpenseParticipantResponse(
                    id=expense_participant.id,
                    user_id=user.id,
                    user_nickname=user.nickname,
                    user_email=user.email,
                    amount_due=expense_participant.amount_due,
                    amount_paid=expense_participant.amount_paid,
                    status=expense_participant.status,
                    paid_at=expense_participant.paid_at,
                    notes=expense_participant.notes,
                    created_at=expense_participant.created_at,
                    updated_at=expense_participant.updated_at
                ))
            
            expense_responses.append(ExpenseResponse(
                id=expense.id,
                title=expense.title,
                description=expense.description,
                amount=expense.amount,
                total_participants=expense.total_participants,
                amount_per_person=expense.amount_per_person,
                meeting_id=expense.meeting_id,
                club_id=expense.club_id,
                club_name=club.name if club else "알 수 없는 클럽",
                created_by=expense.created_by,
                creator_nickname=creator.nickname if creator else "알 수 없음",
                status=expense.status,
                settled_at=expense.settled_at,
                notes=expense.notes,
                participants=participant_responses,
                created_at=expense.created_at,
                updated_at=expense.updated_at
            ))
        
        return ExpenseListResponse(
            expenses=expense_responses,
            total=total,
            page=page,
            size=limit
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"모임 비용 조회 중 오류: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"서버 내부 오류가 발생했습니다: {str(e)}"
        )

# ===== 레거시 이벤트 비용 정산 API (Phase 3에서 Event 모델 제거됨) =====
# /events/ 엔드포인트들은 더 이상 작동하지 않음
# 소셜 모임 비용은 /expenses/meetings/{meeting_id}를 사용하세요
