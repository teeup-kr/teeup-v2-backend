"""
백오피스 스코어/모임참가자 API
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import logging

from database import get_db
from utils.datetime_utils import get_kst_now
from .deps import get_admin_user

logger = logging.getLogger(__name__)

router = APIRouter(tags=["admin-scores"])


@router.get("/scores")
async def get_admin_scores(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_admin_user),
):
    """관리자용 점수 목록 조회"""
    try:
        from models import Score
        from sqlalchemy import desc

        scores = db.query(Score).order_by(desc(Score.created_at)).limit(20).all()
        score_list = []
        for s in scores:
            score_list.append({
                "id": s.id, "user_id": s.user_id, "meeting_id": s.meeting_id,
                "score": s.score, "handicap": s.handicap,
                "created_at": s.created_at.isoformat() if s.created_at else None,
            })
        return {"data": score_list, "total": len(score_list)}
    except Exception as e:
        logger.error(f"관리자 점수 목록 조회 중 오류: {str(e)}")
        return {"data": [], "total": 0}


@router.get("/meeting_participants")
async def get_admin_meeting_participants(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_admin_user),
):
    """관리자용 모임 참가자 목록 조회"""
    try:
        from models import MeetingParticipant
        from sqlalchemy import desc

        participants = db.query(MeetingParticipant).order_by(desc(MeetingParticipant.created_at)).limit(20).all()
        participant_list = []
        for p in participants:
            participant_list.append({
                "id": p.id, "meeting_id": p.meeting_id, "user_id": p.user_id,
                "status": p.status.value,
                "created_at": p.created_at.isoformat() if p.created_at else None,
            })
        return {"data": participant_list, "total": len(participant_list)}
    except Exception as e:
        logger.error(f"관리자 모임 참가자 목록 조회 중 오류: {str(e)}")
        return {"data": [], "total": 0}


@router.put("/meeting_participants/{participant_id}/status")
async def update_admin_participant_status(
    participant_id: int,
    status_data: dict,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_admin_user),
):
    """관리자용 모임 참가자 상태 업데이트"""
    try:
        from models import MeetingParticipant, MeetingParticipantStatus

        participant = db.query(MeetingParticipant).filter(MeetingParticipant.id == participant_id).first()
        if not participant:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="모임 참가자를 찾을 수 없습니다")
        if "status" in status_data:
            try:
                participant.status = MeetingParticipantStatus(status_data["status"])
            except ValueError:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="유효하지 않은 상태입니다")
        participant.updated_at = get_kst_now()
        db.commit()
        db.refresh(participant)
        return {
            "message": "모임 참가자 상태가 성공적으로 업데이트되었습니다",
            "success": True,
            "participant": {
                "id": participant.id,
                "status": participant.status.value if hasattr(participant.status, "value") else str(participant.status),
            },
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"관리자 모임 참가자 상태 업데이트 중 오류: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="모임 참가자 상태 업데이트 중 오류가 발생했습니다")
