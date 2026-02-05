"""
모임 참가자 관리 API
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import List, Optional
from database import get_db
from models import MeetingParticipant, User, Meeting, Guest, ClubMembership
from schemas import MessageResponse, GuestCreate
from routers.auth import get_current_active_user, get_current_user_allow_both
from utils.team_formation import add_guest_to_meeting
from utils.permissions import MEMBERSHIP_ACTIVE_STATUSES

router = APIRouter(prefix="/meetings", tags=["모임 참가자 관리"])


def _normalize_birthdate(val: Optional[str]) -> Optional[str]:
    """생년월일을 YYYY-MM-DD 형식으로 변환 (19971523 -> 1997-15-23은 잘못됨, 19970115 -> 1997-01-15)"""
    if not val:
        return None
    s = str(val).strip().replace("-", "").replace(".", "")
    if len(s) == 8 and s.isdigit():
        return f"{s[:4]}-{s[4:6]}-{s[6:8]}"
    if len(s) == 10 and s[4] == "-":  # 이미 YYYY-MM-DD
        return val
    return val


@router.post("/{meeting_id}/guests")
def add_guest_to_meeting_api(
    meeting_id: int,
    guest_data: GuestCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user_allow_both),
):
    """모임에 게스트 추가"""
    meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
    if not meeting:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="모임을 찾을 수 없습니다.")

    user_id = current_user.get("id") if isinstance(current_user, dict) else getattr(current_user, "id", None)
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="인증이 필요합니다.")

    # 클럽 멤버십 확인 (리더/매니저 또는 참가자만 게스트 추가 가능)
    membership = db.query(ClubMembership).filter(
        ClubMembership.club_id == meeting.club_id,
        ClubMembership.user_id == user_id,
        ClubMembership.status.in_(MEMBERSHIP_ACTIVE_STATUSES),
    ).first()
    if not membership:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="해당 클럽 멤버만 게스트를 추가할 수 있습니다.")

    # 정원 확인
    if meeting.max_participants is not None:
        from sqlalchemy import or_
        from schemas import MeetingParticipantStatus
        count = db.query(MeetingParticipant).filter(
            MeetingParticipant.meeting_id == meeting_id,
            MeetingParticipant.status.in_([MeetingParticipantStatus.CONFIRMED, MeetingParticipantStatus.PENDING]),
        ).count()
        if count >= meeting.max_participants:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="모임 정원이 마감되었습니다.")

    birthdate_str = _normalize_birthdate(guest_data.birthdate)
    guest_gender = None
    if guest_data.gender:
        from models.enums import Gender
        try:
            guest_gender = Gender(guest_data.gender)
        except ValueError:
            guest_gender = None

    try:
        from decimal import Decimal
        participant = add_guest_to_meeting(
            meeting_id=meeting_id,
            guest_name=guest_data.name,
            guest_handicap=Decimal(str(guest_data.handicap)) if guest_data.handicap is not None else None,
            average_score=guest_data.average_score,
            guest_birthdate=birthdate_str,
            guest_gender=guest_gender,
            db=db,
        )
        guest = db.query(Guest).filter(Guest.id == participant.guest_id).first()
        return {
            "message": "게스트가 추가되었습니다.",
            "participant_id": participant.id,
            "guest_id": participant.guest_id,
            "guest_name": guest.name if guest else guest_data.name,
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"게스트 추가 중 오류가 발생했습니다: {str(e)}")


@router.get("/", response_model=List[dict])
def get_meeting_participants(
    user_id: Optional[int] = Query(None, description="사용자 ID로 필터링"),
    meeting_id: Optional[int] = Query(None, description="모임 ID로 필터링"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_active_user)
):
    """모임 참가자 목록 조회"""
    try:
        query = db.query(MeetingParticipant)
        
        if user_id:
            query = query.filter(MeetingParticipant.user_id == user_id)
        if meeting_id:
            query = query.filter(MeetingParticipant.meeting_id == meeting_id)
            
        participants = query.all()
        
        # 사용자와 모임 정보를 포함하여 반환
        result = []
        for participant in participants:
            # 게스트인 경우와 일반 사용자인 경우 구분
            user = None
            guest = None
            if participant.guest_id:
                # 게스트인 경우
                guest = db.query(Guest).filter(Guest.id == participant.guest_id).first()
            else:
                # 일반 사용자인 경우
                if participant.user_id:
                    user = db.query(User).filter(User.id == participant.user_id).first()
            
            meeting = db.query(Meeting).filter(Meeting.id == participant.meeting_id).first()
            
            result.append({
                "id": participant.id,
                "user_id": participant.user_id,
                "guest_id": participant.guest_id,
                "meeting_id": participant.meeting_id,
                "status": participant.status,
                "role": participant.role,
                "handicap_index": participant.handicap_index,
                "recent_avg_score": participant.recent_avg_score,
                "pace_preference": participant.pace_preference,
                "tee_preference": participant.tee_preference,
                "is_newbie": participant.is_newbie,
                "prefer_with": participant.prefer_with,
                "avoid_with": participant.avoid_with,
                "is_guest": participant.guest_id is not None,
                "created_at": participant.created_at,
                "updated_at": participant.updated_at,
                "user_email": user.email if user else None,
                "user_nickname": user.nickname if user else (guest.name if guest else None),
                "guest_name": guest.name if guest else None,
                "meeting_name": meeting.name if meeting else None
            })
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"참가자 목록 조회 중 오류가 발생했습니다: {str(e)}")

@router.get("/{participant_id}", response_model=dict)
def get_meeting_participant(
    participant_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_active_user)
):
    """모임 참가자 상세 조회"""
    try:
        participant = db.query(MeetingParticipant).filter(MeetingParticipant.id == participant_id).first()
        
        if not participant:
            raise HTTPException(status_code=404, detail="참가자를 찾을 수 없습니다")
        
        # 게스트인 경우와 일반 사용자인 경우 구분
        user = None
        guest = None
        if participant.guest_id is not None:
            # 게스트인 경우
            if participant.guest_id:
                guest = db.query(Guest).filter(Guest.id == participant.guest_id).first()
        else:
            # 일반 사용자인 경우
            if participant.user_id:
                user = db.query(User).filter(User.id == participant.user_id).first()
        
        meeting = db.query(Meeting).filter(Meeting.id == participant.meeting_id).first()
        
        return {
            "id": participant.id,
            "user_id": participant.user_id,
            "guest_id": participant.guest_id,
            "meeting_id": participant.meeting_id,
            "status": participant.status,
            "role": participant.role,
            "handicap_index": participant.handicap_index,
            "recent_avg_score": participant.recent_avg_score,
            "pace_preference": participant.pace_preference,
            "tee_preference": participant.tee_preference,
            "is_newbie": participant.is_newbie,
            "prefer_with": participant.prefer_with,
            "avoid_with": participant.avoid_with,
            "is_guest": participant.guest_id is not None,
            "created_at": participant.created_at,
            "updated_at": participant.updated_at,
            "user_email": user.email if user else None,
            "user_nickname": user.nickname if user else (guest.name if guest else None),
            "guest_name": guest.name if guest else None,
            "meeting_name": meeting.name if meeting else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"참가자 조회 중 오류가 발생했습니다: {str(e)}")
