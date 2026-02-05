"""
소셜 모임 관리 API - SOCIAL 타입 전용
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, case
from typing import List, Optional
from datetime import datetime
from utils.datetime_utils import get_kst_now
import logging

from database import get_db
from models import (
    User, Club, ClubMembership, Meeting, MeetingParticipant, ParticipantType, Guest
)
from schemas import (
    MeetingType, MeetingStatus, MeetingParticipantStatus, MeetingParticipantRole
)
from schemas import (
    SocialMeetingCreate, MeetingUpdate, MeetingResponse,
    MeetingParticipantResponse, PaginatedResponse, MessageResponse
)
from routers.auth import get_current_active_user, get_current_user, get_current_user_allow_both
from utils.permissions import MEMBERSHIP_ACTIVE_STATUSES

router = APIRouter(prefix="/socials", tags=["소셜 모임 관리"])
logger = logging.getLogger(__name__)


# =============================================================================
# 소셜 모임 목록 조회
# =============================================================================

@router.get("/", response_model=PaginatedResponse[MeetingResponse])
async def get_socials(
    page: int = Query(1, ge=1, description="페이지 번호"),
    limit: int = Query(10, ge=1, le=100, description="페이지당 항목 수"),
    status: Optional[MeetingStatus] = Query(None, description="모임 상태 필터"),
    search: Optional[str] = Query(None, description="검색어"),
    current_user: User = Depends(get_current_user_allow_both),
    db: Session = Depends(get_db)
):
    """소셜 모임 목록 조회"""
    
    # 사용자가 속한 클럽만 조회
    user_club_ids = db.query(ClubMembership.club_id).filter(
        and_(
            ClubMembership.user_id == current_user.id,
            ClubMembership.status.in_(MEMBERSHIP_ACTIVE_STATUSES)
        )
    ).subquery()
    
    query = db.query(Meeting).join(Club).filter(
        and_(
            Meeting.meeting_type == MeetingType.SOCIAL,
            Meeting.club_id.in_(user_club_ids)
        )
    )
    
    # 상태 필터
    if status:
        query = query.filter(Meeting.status == status)
    
    # 검색 필터
    if search:
        search_filter = or_(
            Meeting.name.contains(search),
            Meeting.venue_name.contains(search),
            Meeting.location.contains(search)
        )
        query = query.filter(search_filter)
    
    # 총 개수
    total = query.count()
    
    # 정렬: 상태별 우선순위 (SCHEDULED → IN_PROGRESS → COMPLETED)
    # CANCELED는 999로 설정하여 맨 뒤로
    # 동일 상태 내에서는 최신 모임부터 (created_at 내림차순)
    status_order = case(
        (Meeting.status == MeetingStatus.SCHEDULED, 1),
        (Meeting.status == MeetingStatus.IN_PROGRESS, 2),
        (Meeting.status == MeetingStatus.COMPLETED, 3),
        (Meeting.status == MeetingStatus.CANCELED, 999),
        else_=5
    )
    query = query.order_by(status_order.asc(), Meeting.created_at.desc())
    
    # 페이지네이션
    meetings = query.offset((page - 1) * limit).limit(limit).all()
    
    # 응답 데이터 구성
    meeting_responses = []
    for meeting in meetings:
        participant_count = db.query(MeetingParticipant).filter(
            and_(
                MeetingParticipant.meeting_id == meeting.id,
                MeetingParticipant.status == MeetingParticipantStatus.CONFIRMED
            )
        ).count()
        
        meeting_dict = {**meeting.__dict__}
        meeting_dict.pop("_sa_instance_state", None)
        meeting_dict["tee_times"] = meeting.tee_times or []

        meeting_responses.append(
            MeetingResponse(
                **meeting_dict,
                club_name=meeting.club.name,
                participant_count=participant_count,
            )
        )
    
    return PaginatedResponse(
        data=meeting_responses,
        total=total,
        page=page,
        limit=limit,
        total_pages=(total + limit - 1) // limit
    )

# =============================================================================
# 소셜 모임 생성
# =============================================================================

@router.post("/", response_model=MeetingResponse)
async def create_social(
    meeting_data: SocialMeetingCreate,
    current_user: User = Depends(get_current_user_allow_both),
    db: Session = Depends(get_db)
):
    """소셜 모임 생성 (모든 멤버 가능)"""
    
    # 클럽 멤버십 확인
    membership = db.query(ClubMembership).filter(
        and_(
            ClubMembership.user_id == current_user.id,
            ClubMembership.club_id == meeting_data.club_id,
            ClubMembership.status.in_(MEMBERSHIP_ACTIVE_STATUSES)
        )
    ).first()
    
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="해당 클럽의 멤버가 아닙니다."
        )
    
    # 모임 생성
    meeting = Meeting(        name=meeting_data.name,
        description=meeting_data.description,
        meeting_time=meeting_data.meeting_time,
        application_deadline=meeting_data.application_deadline,
        max_participants=meeting_data.max_participants,
        meeting_type=MeetingType.SOCIAL,
        venue_name=meeting_data.venue_name,
        location=meeting_data.venue_name,
        social_cost=meeting_data.social_cost,
        social_settlement_method=(
            meeting_data.social_settlement_method.value
            if hasattr(meeting_data.social_settlement_method, "value")
            else meeting_data.social_settlement_method
        ),
        social_notes=meeting_data.social_notes,
        club_id=meeting_data.club_id,
        status=MeetingStatus.SCHEDULED,
        tee_times=[],
    )
    
    db.add(meeting)
    db.commit()
    db.refresh(meeting)
    
    # 생성자를 매니저로 자동 참가
    participant = MeetingParticipant(
        meeting_id=meeting.id,
        user_id=current_user.id,
        participant_type=ParticipantType.USER,
        status=MeetingParticipantStatus.CONFIRMED,
        role=MeetingParticipantRole.ORGANIZER
    )
    db.add(participant)
    db.commit()
    
    # 클럽 정보 조회
    club = db.query(Club).filter(Club.id == meeting.club_id).first()
    
    # 클럽 멤버들에게 새 소셜모임 등록 알림 전송
    try:
        from utils.notification_service import create_social_notification
        
        # 클럽의 모든 멤버 조회 (생성자 제외)
        club_members = db.query(ClubMembership).filter(
            ClubMembership.club_id == meeting_data.club_id,
            ClubMembership.user_id != current_user.id,  # 생성자 제외
            ClubMembership.status.in_(MEMBERSHIP_ACTIVE_STATUSES)  # 승인된 멤버만
        ).all()
        
        for member in club_members:
            create_social_notification(
                db=db,
                user_id=member.user_id,
                social_name=meeting_data.name,
                club_name=club.name,
                notification_type="CREATED",
                meeting_id=meeting.id
            )
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"소셜모임 등록 알림 전송 실패: {str(e)}")
    
    meeting_dict = {**meeting.__dict__}
    meeting_dict.pop("_sa_instance_state", None)
    meeting_dict["tee_times"] = meeting.tee_times or []

    return MeetingResponse(
        **meeting_dict,
        club_name=club.name,
        participant_count=1,
    )

# =============================================================================
# 소셜 모임 상세 조회
# =============================================================================

@router.get("/{meeting_id}", response_model=MeetingResponse)
async def get_social(
    meeting_id: int,
    current_user: User = Depends(get_current_user_allow_both),
    db: Session = Depends(get_db)
):
    """소셜 모임 상세 조회"""
    
    # 모임 조회
    meeting = db.query(Meeting).join(Club).filter(
        and_(
            Meeting.id == meeting_id,
            Meeting.meeting_type == MeetingType.SOCIAL
        )
    ).first()
    
    if not meeting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="소셜 모임을 찾을 수 없습니다."
        )
    
    # 클럽 멤버십 확인 (관리자는 제외)
    from models import Admin
    admin = db.query(Admin).filter(
        Admin.id == current_user.id,
        Admin.deleted_at.is_(None)
    ).first()
    
    if not admin:
        membership = db.query(ClubMembership).filter(
            and_(
                ClubMembership.user_id == current_user.id,
                ClubMembership.club_id == meeting.club_id,
                ClubMembership.status.in_(MEMBERSHIP_ACTIVE_STATUSES)
            )
        ).first()
        
        if not membership:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="해당 클럽의 멤버가 아닙니다."
            )
    
    # 참가자 수 조회
    participant_count = db.query(MeetingParticipant).filter(
        and_(
            MeetingParticipant.meeting_id == meeting.id,
            MeetingParticipant.status == MeetingParticipantStatus.CONFIRMED
        )
    ).count()
    
    meeting_dict = {**meeting.__dict__}
    meeting_dict.pop("_sa_instance_state", None)
    meeting_dict["tee_times"] = meeting.tee_times or []

    return MeetingResponse(
        **meeting_dict,
        club_name=meeting.club.name,
        participant_count=participant_count,
    )
    meeting_dict = {**meeting.__dict__}
    meeting_dict.pop("_sa_instance_state", None)
    meeting_dict["tee_times"] = meeting.tee_times or []

    return MeetingResponse(
        **meeting_dict,
        club_name=meeting.club.name,
        participant_count=participant_count,
    )

# =============================================================================
# 소셜 모임 수정
# =============================================================================

@router.put("/{meeting_id}", response_model=MeetingResponse)
async def update_social(
    meeting_id: int,
    meeting_data: MeetingUpdate,
    current_user: User = Depends(get_current_user_allow_both),
    db: Session = Depends(get_db)
):
    """소셜 모임 수정 (매니저만 가능)"""
    
    # 모임 조회
    meeting = db.query(Meeting).filter(
        and_(
            Meeting.id == meeting_id,
            Meeting.meeting_type == MeetingType.SOCIAL
        )
    ).first()
    
    if not meeting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="소셜 모임을 찾을 수 없습니다."
        )
    
    # 매니저 권한 확인 (개설자, ORGANIZER, 또는 리더/매니저 참가자)
    from utils.permissions import is_meeting_organizer_or_manager
    if not is_meeting_organizer_or_manager(meeting_id, current_user.id, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="소셜 모임 매니저만 수정할 수 있습니다."
        )
    
    # 수정 가능한 필드들만 업데이트
    update_data = meeting_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(meeting, field, value)
    
    meeting.updated_at = get_kst_now()
    
    db.commit()
    db.refresh(meeting)
    
    # 클럽 정보 조회
    club = db.query(Club).filter(Club.id == meeting.club_id).first()
    
    # 참가자 수 조회
    participant_count = db.query(MeetingParticipant).filter(
        and_(
            MeetingParticipant.meeting_id == meeting.id,
            MeetingParticipant.status == MeetingParticipantStatus.CONFIRMED
        )
    ).count()
    
    return MeetingResponse(
        **meeting.__dict__,
        club_name=club.name,
        participant_count=participant_count
    )

# =============================================================================
# 소셜 모임 삭제
# =============================================================================

@router.delete("/{meeting_id}")
async def delete_social(
    meeting_id: int,
    current_user: User = Depends(get_current_user_allow_both),
    db: Session = Depends(get_db)
):
    """소셜 모임 삭제 (매니저만 가능)"""
    
    # 모임 조회
    meeting = db.query(Meeting).filter(
        and_(
            Meeting.id == meeting_id,
            Meeting.meeting_type == MeetingType.SOCIAL
        )
    ).first()
    
    if not meeting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="소셜 모임을 찾을 수 없습니다."
        )
    
    # 매니저 권한 확인 (개설자, ORGANIZER, 또는 리더/매니저 참가자)
    from utils.permissions import is_meeting_organizer_or_manager
    if not is_meeting_organizer_or_manager(meeting_id, current_user.id, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="소셜 모임 매니저만 삭제할 수 있습니다."
        )
    
    db.delete(meeting)
    db.commit()
    
    return {"message": "소셜 모임이 삭제되었습니다."}

# =============================================================================
# 소셜 모임 참가자 목록 조회
# =============================================================================

@router.get("/{meeting_id}/participants")
async def get_social_participants(
    meeting_id: int,
    current_user: User = Depends(get_current_user_allow_both),
    db: Session = Depends(get_db)
):
    """소셜 모임 참가자 목록 조회 (하단 참가탭용)"""
    meeting = db.query(Meeting).filter(
        and_(
            Meeting.id == meeting_id,
            Meeting.meeting_type == MeetingType.SOCIAL
        )
    ).first()

    if not meeting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="소셜 모임을 찾을 수 없습니다."
        )

    # 클럽 멤버십 확인
    membership = db.query(ClubMembership).filter(
        and_(
            ClubMembership.user_id == current_user.id,
            ClubMembership.club_id == meeting.club_id,
            ClubMembership.status.in_(MEMBERSHIP_ACTIVE_STATUSES)
        )
    ).first()

    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="해당 클럽의 멤버가 아닙니다."
        )

    # 참가자 목록 조회 (게스트 포함)
    participants = db.query(MeetingParticipant).filter(
        MeetingParticipant.meeting_id == meeting_id
    ).all()

    result = []
    for p in participants:
        if p.guest_id:
            guest = db.query(Guest).filter(Guest.id == p.guest_id).first()
            result.append({
                "id": p.id,
                "user_id": None,
                "guest_id": p.guest_id,
                "user_name": guest.name if guest else "게스트",
                "user_nickname": guest.name if guest else "게스트",
                "name": guest.name if guest else "게스트",
                "status": p.status.value if hasattr(p.status, "value") else str(p.status),
                "role": p.role.value if hasattr(p.role, "value") else str(p.role),
                "is_guest": True,
                "created_at": p.created_at.isoformat() if p.created_at else None,
            })
        else:
            user = db.query(User).filter(User.id == p.user_id).first() if p.user_id else None
            if user:
                result.append({
                    "id": p.id,
                    "user_id": p.user_id,
                    "guest_id": None,
                    "user_name": user.realname or user.nickname or "이름 없음",
                    "user_nickname": user.nickname or "닉네임 없음",
                    "name": user.realname or user.nickname or "이름 없음",
                    "status": p.status.value if hasattr(p.status, "value") else str(p.status),
                    "role": p.role.value if hasattr(p.role, "value") else str(p.role),
                    "is_guest": False,
                    "created_at": p.created_at.isoformat() if p.created_at else None,
                })
    return result


# =============================================================================
# 소셜 모임 참가/탈퇴
# =============================================================================

@router.post("/{meeting_id}/join")
async def join_social(
    meeting_id: int,
    current_user: User = Depends(get_current_user_allow_both),
    db: Session = Depends(get_db)
):
    """소셜 모임 참가"""
    
    # 모임 조회
    meeting = db.query(Meeting).filter(
        and_(
            Meeting.id == meeting_id,
            Meeting.meeting_type == MeetingType.SOCIAL
        )
    ).first()
    
    if not meeting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="소셜 모임을 찾을 수 없습니다."
        )
    
    # 클럽 멤버십 확인
    membership = db.query(ClubMembership).filter(
        and_(
            ClubMembership.user_id == current_user.id,
            ClubMembership.club_id == meeting.club_id,
            ClubMembership.status.in_(MEMBERSHIP_ACTIVE_STATUSES)
        )
    ).first()
    
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="해당 클럽의 멤버가 아닙니다."
        )
    
    # 이미 참가했는지 확인
    existing_participant = db.query(MeetingParticipant).filter(
        and_(
            MeetingParticipant.meeting_id == meeting_id,
            MeetingParticipant.user_id == current_user.id
        )
    ).first()
    
    if existing_participant:
        # 이미 참가한 경우에도 200 (idempotent - 프론트 반복 클릭 대응)
        return {"message": "이미 참가한 소셜 모임입니다.", "already_joined": True}
    
    # 최대 참가자 수 확인 (max_participants가 null이면 제한 없음)
    if meeting.max_participants is not None:
        current_participants = db.query(MeetingParticipant).filter(
            and_(
                MeetingParticipant.meeting_id == meeting_id,
                MeetingParticipant.status == MeetingParticipantStatus.CONFIRMED
            )
        ).count()
        
        if current_participants >= meeting.max_participants:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="소셜 모임 정원이 가득 찼습니다."
            )
    
    # 참가자 추가
    participant = MeetingParticipant(
        meeting_id=meeting_id,
        user_id=current_user.id,
        guest_id=None,
        participant_type=ParticipantType.USER,
        status=MeetingParticipantStatus.CONFIRMED,
        role=MeetingParticipantRole.PARTICIPANT
    )
    
    db.add(participant)
    db.commit()
    
    return {"message": "소셜 모임에 참가했습니다."}

@router.delete("/{meeting_id}/leave")
async def leave_social(
    meeting_id: int,
    current_user: User = Depends(get_current_user_allow_both),
    db: Session = Depends(get_db)
):
    """소셜 모임 탈퇴"""
    
    # 참가자 조회
    participant = db.query(MeetingParticipant).filter(
        and_(
            MeetingParticipant.meeting_id == meeting_id,
            MeetingParticipant.user_id == current_user.id
        )
    ).first()
    
    if not participant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="참가하지 않은 소셜 모임입니다."
        )
    
    # 매니저는 탈퇴 불가
    if participant.role == MeetingParticipantRole.ORGANIZER:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="소셜 모임 매니저는 탈퇴할 수 없습니다."
        )
    
    db.delete(participant)
    db.commit()
    
    return {"message": "소셜 모임에서 탈퇴했습니다."}

# =============================================================================
# 소셜 모임 취소
# =============================================================================

@router.post("/{meeting_id}/cancel")
async def cancel_social(
    meeting_id: int,
    reason: str,
    current_user: User = Depends(get_current_user_allow_both),
    db: Session = Depends(get_db)
):
    """소셜 모임 취소 (매니저만 가능)"""
    
    # 모임 조회
    meeting = db.query(Meeting).filter(
        and_(
            Meeting.id == meeting_id,
            Meeting.meeting_type == MeetingType.SOCIAL
        )
    ).first()
    
    if not meeting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="소셜 모임을 찾을 수 없습니다."
        )
    
    # 매니저 권한 확인
    participant = db.query(MeetingParticipant).filter(
        and_(
            MeetingParticipant.meeting_id == meeting_id,
            MeetingParticipant.user_id == current_user.id,
            MeetingParticipant.role == MeetingParticipantRole.ORGANIZER
        )
    ).first()
    
    if not participant:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="소셜 모임 매니저만 취소할 수 있습니다."
        )
    
    # 모임 취소
    meeting.status = MeetingStatus.CANCELED
    meeting.cancel_reason = reason
    meeting.updated_at = get_kst_now()
    
    db.commit()
    
    return {"message": "소셜 모임이 취소되었습니다."}
