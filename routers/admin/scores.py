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
                "created_at": p.created_at.isoformat() if p.created_at else None,
            })
        return {"data": participant_list, "total": len(participant_list)}
    except Exception as e:
        logger.error(f"관리자 모임 참가자 목록 조회 중 오류: {str(e)}")
        return {"data": [], "total": 0}

