"""
모임 참가자 관리 API
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from database import get_db
from models import MeetingParticipant, User, Meeting, Guest
from schemas import MessageResponse
from routers.auth import get_current_active_user

router = APIRouter(prefix="/meetings", tags=["모임 참가자 관리"])

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
        if participant.is_guest or participant.guest_id:
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
            "handicap_index": participant.handicap_index,
            "recent_avg_score": participant.recent_avg_score,
            "pace_preference": participant.pace_preference,
            "tee_preference": participant.tee_preference,
            "is_newbie": participant.is_newbie,
            "prefer_with": participant.prefer_with,
            "avoid_with": participant.avoid_with,
            "is_guest": participant.is_guest or participant.guest_id is not None,
            "created_at": participant.created_at,
            "updated_at": participant.updated_at,
            "user_email": user.email if user else None,
            "user_nickname": user.nickname if user else (guest.name if guest else None),
            "guest_name": guest.name if guest else (participant.guest_name if participant.is_guest else None),
            "meeting_name": meeting.name if meeting else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"참가자 조회 중 오류가 발생했습니다: {str(e)}")
