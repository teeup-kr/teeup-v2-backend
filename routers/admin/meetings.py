"""
백오피스 모임 API
"""
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func, extract
from typing import Optional, List
import logging

from database import get_db
from utils.datetime_utils import get_kst_now

from .deps import get_admin_user

logger = logging.getLogger(__name__)
router = APIRouter(tags=["admin-meetings"])


class MeetingStatsResponse(BaseModel):
    total_meetings: int
    active_meetings: int
    canceled_meetings: int
    completed_meetings: int
    meetings_by_type: dict
    meetings_by_month: List[dict]
    total_participants: int
    average_participants_per_meeting: float
    meetings_by_club: List[dict]
    upcoming_meetings_count: int
    past_meetings_count: int


@router.get("/meetings/rounding")
async def admin_get_rounding_meetings(page: int = Query(1, ge=1, description="페이지 번호"),
                                      limit: int = Query(10, ge=1, le=100, description="페이지당 항목 수"),
                                      status: Optional[str] = Query(None, description="모임 상태 필터"),
                                      search: Optional[str] = Query(None, description="검색어"),
                                      club_id: Optional[int] = Query(None, description="클럽 ID 필터"),
                                      current_user: dict = Depends(get_admin_user),
                                      db: Session = Depends(get_db)):
    """관리자용 라운딩 모임 목록 조회 (모든 클럽 조회 가능)"""
    try:
        from models import Meeting, Club, MeetingParticipant
        from schemas import MeetingType, MeetingParticipantStatus, MeetingParticipantRole
        from sqlalchemy import desc, and_, or_

        query = db.query(Meeting).join(Club).filter(Meeting.meeting_type == MeetingType.ROUND)

        # 클럽 필터
        if club_id:
            query = query.filter(Meeting.club_id == club_id)

        # 상태 필터
        if status:
            query = query.filter(Meeting.status == status)

        # 검색 필터
        if search:
            search_filter = or_(Meeting.name.contains(search), Meeting.course_name.contains(search),
                                Meeting.location.contains(search))
            query = query.filter(search_filter)

        # 총 개수 조회
        total = query.count()

        # 페이지네이션
        meetings = query.offset((page - 1) * limit).limit(limit).all()

        # 응답 데이터 구성
        meeting_data = []
        for meeting in meetings:
            # 참가자 수 조회
            participant_count = db.query(MeetingParticipant).filter(
                and_(MeetingParticipant.meeting_id == meeting.id,
                     MeetingParticipant.status == MeetingParticipantStatus.CONFIRMED)).count()

            # 개설자(ORGANIZER) 조회
            organizer_participant = db.query(MeetingParticipant).filter(
                and_(MeetingParticipant.meeting_id == meeting.id,
                     MeetingParticipant.role == MeetingParticipantRole.ORGANIZER)).first()

            creator_info = None
            if organizer_participant and organizer_participant.user:
                creator_info = {
                    "id": organizer_participant.user.id,
                    "realname": organizer_participant.user.realname,
                    "nickname": organizer_participant.user.nickname,
                    "email": organizer_participant.user.email
                }

            # meeting_type과 status는 데이터베이스에서 문자열로 저장되므로 .value 접근 불필요
            meeting_type_str = meeting.meeting_type
            if hasattr(meeting_type_str, 'value'):
                meeting_type_str = meeting_type_str.value

            meeting_subtype_str = meeting.meeting_subtype
            if meeting_subtype_str and hasattr(meeting_subtype_str, 'value'):
                meeting_subtype_str = meeting_subtype_str.value

            status_str = meeting.status
            if hasattr(status_str, 'value'):
                status_str = status_str.value

            meeting_data.append({
                "id":
                str(meeting.id),
                "name":
                str(meeting.name) if meeting.name else "",
                "description":
                str(meeting.description) if meeting.description else "",
                "meeting_type":
                str(meeting_type_str) if meeting_type_str else "",
                "meeting_subtype":
                str(meeting_subtype_str) if meeting_subtype_str else "",
                "location":
                str(meeting.location) if meeting.location else "",
                "course_name":
                str(meeting.course_name) if meeting.course_name else "",
                "tee_time":
                meeting.tee_times[0] if meeting.tee_times and len(meeting.tee_times) > 0 else None,
                "meeting_time":
                meeting.meeting_time.isoformat() if meeting.meeting_time else None,
                "max_participants":
                int(meeting.max_participants) if meeting.max_participants else 0,
                "status":
                str(status_str) if status_str else "",
                "club_id":
                str(meeting.club_id),
                "club_name":
                str(meeting.club.name) if meeting.club and meeting.club.name else "",
                "participant_count":
                int(participant_count),
                "creator":
                creator_info,
                "created_at":
                meeting.created_at.isoformat() if meeting.created_at else None,
                "updated_at":
                meeting.updated_at.isoformat() if meeting.updated_at else None
            })

        total_pages = (total + limit - 1) // limit

        return {"data": meeting_data, "total": total, "page": page, "limit": limit, "total_pages": total_pages}

    except Exception as e:
        logger.error(f"관리자 라운딩 모임 목록 조회 중 오류: {str(e)}")
        from fastapi import status as http_status
        raise HTTPException(status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR, detail="라운딩 모임 목록 조회 중 오류가 발생했습니다")


@router.get("/meetings/event")
async def admin_get_event_meetings(page: int = Query(1, ge=1, description="페이지 번호"),
                                   limit: int = Query(10, ge=1, le=100, description="페이지당 항목 수"),
                                   status: Optional[str] = Query(None, description="모임 상태 필터"),
                                   search: Optional[str] = Query(None, description="검색어"),
                                   club_id: Optional[int] = Query(None, description="클럽 ID 필터"),
                                   current_user: dict = Depends(get_admin_user),
                                   db: Session = Depends(get_db)):
    """관리자용 이벤트 모임 목록 조회 (모든 클럽 조회 가능)"""
    try:
        from models import Meeting, Club, MeetingParticipant
        from schemas import MeetingType, MeetingParticipantStatus, MeetingParticipantRole
        from sqlalchemy import desc, and_, or_

        query = db.query(Meeting).join(Club).filter(Meeting.meeting_type == MeetingType.SOCIAL)

        # 클럽 필터
        if club_id:
            query = query.filter(Meeting.club_id == club_id)

        # 상태 필터
        if status:
            query = query.filter(Meeting.status == status)

        # 검색 필터
        if search:
            search_filter = or_(Meeting.name.contains(search), Meeting.venue_name.contains(search),
                                Meeting.location.contains(search))
            query = query.filter(search_filter)

        # 총 개수 조회
        total = query.count()

        # 페이지네이션
        meetings = query.offset((page - 1) * limit).limit(limit).all()

        # 응답 데이터 구성
        meeting_data = []
        for meeting in meetings:
            # 참가자 수 조회
            participant_count = db.query(MeetingParticipant).filter(
                and_(MeetingParticipant.meeting_id == meeting.id,
                     MeetingParticipant.status == MeetingParticipantStatus.CONFIRMED)).count()

            # 개설자(ORGANIZER) 조회
            organizer_participant = db.query(MeetingParticipant).filter(
                and_(MeetingParticipant.meeting_id == meeting.id,
                     MeetingParticipant.role == MeetingParticipantRole.ORGANIZER)).first()

            creator_info = None
            if organizer_participant and organizer_participant.user:
                creator_info = {
                    "id": organizer_participant.user.id,
                    "realname": organizer_participant.user.realname,
                    "nickname": organizer_participant.user.nickname,
                    "email": organizer_participant.user.email
                }

            meeting_data.append({
                "id":
                meeting.id,
                "name":
                meeting.name,
                "description":
                meeting.description,
                "meeting_type":
                meeting.meeting_type.value if hasattr(meeting.meeting_type, 'value') else str(meeting.meeting_type),
                "meeting_subtype":
                meeting.meeting_subtype.value
                if hasattr(meeting.meeting_subtype, 'value') else str(meeting.meeting_subtype),
                "location":
                meeting.location,
                "venue_name":
                meeting.venue_name,
                "meeting_time":
                meeting.meeting_time.isoformat() if meeting.meeting_time else None,
                "max_participants":
                meeting.max_participants,
                "status":
                meeting.status.value if hasattr(meeting.status, 'value') else str(meeting.status),
                "club_id":
                meeting.club_id,
                "club_name":
                meeting.club.name,
                "participant_count":
                participant_count,
                "creator":
                creator_info,
                "created_at":
                meeting.created_at.isoformat() if meeting.created_at else None,
                "updated_at":
                meeting.updated_at.isoformat() if meeting.updated_at else None
            })

        total_pages = (total + limit - 1) // limit

        return {"data": meeting_data, "total": total, "page": page, "limit": limit, "total_pages": total_pages}

    except Exception as e:
        logger.error(f"관리자 이벤트 모임 목록 조회 중 오류: {str(e)}")
        from fastapi import status as http_status
        raise HTTPException(status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR, detail="이벤트 모임 목록 조회 중 오류가 발생했습니다")


@router.get("/meetings/{meeting_id}")
async def get_admin_meeting(meeting_id: int,
                            db: Session = Depends(get_db),
                            current_user: dict = Depends(get_admin_user)):
    """관리자용 모임 상세 조회"""
    try:
        from models import Meeting, Club, MeetingParticipant
        from schemas import MeetingParticipantStatus
        from sqlalchemy import and_

        # 모임 조회
        meeting = db.query(Meeting).join(Club).filter(Meeting.id == meeting_id).first()

        if not meeting:
            from fastapi import status as http_status
            raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="모임을 찾을 수 없습니다.")

        # 참가자 수 조회
        participant_count = db.query(MeetingParticipant).filter(
            and_(MeetingParticipant.meeting_id == meeting.id,
                 MeetingParticipant.status == MeetingParticipantStatus.CONFIRMED)).count()

        return {
            "id":
            meeting.id,
            "name":
            meeting.name,
            "description":
            meeting.description,
            "meeting_type":
            meeting.meeting_type.value if hasattr(meeting.meeting_type, 'value') else str(meeting.meeting_type),
            "meeting_subtype":
            meeting.meeting_subtype.value
            if hasattr(meeting.meeting_subtype, 'value') else str(meeting.meeting_subtype),
            "location":
            meeting.location,
            "course_name":
            meeting.course_name,
            "venue_name":
            meeting.venue_name,
            "tee_time":
            meeting.tee_times[0] if meeting.tee_times and len(meeting.tee_times) > 0 else None,
            "meeting_time":
            meeting.meeting_time.isoformat() if meeting.meeting_time else None,
            "max_participants":
            meeting.max_participants,
            "status":
            meeting.status.value if hasattr(meeting.status, 'value') else str(meeting.status),
            "club_id":
            meeting.club_id,
            "club_name":
            meeting.club.name,
            "participant_count":
            participant_count,
            "created_at":
            meeting.created_at.isoformat() if meeting.created_at else None,
            "updated_at":
            meeting.updated_at.isoformat() if meeting.updated_at else None
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"관리자 모임 상세 조회 중 오류: {str(e)}")
        from fastapi import status as http_status
        raise HTTPException(status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR, detail="모임 상세 조회 중 오류가 발생했습니다")


@router.post("/meetings/rounding")
async def create_admin_rounding_meeting(meeting_data: dict,
                                        db: Session = Depends(get_db),
                                        current_user: dict = Depends(get_admin_user)):
    """관리자용 라운딩 모임 생성"""
    try:
        from models import Meeting, Club, MeetingParticipant, MeetingType, MeetingStatus, MeetingParticipantStatus, MeetingParticipantRole
        from utils import generate_id
        from datetime import datetime

        # 클럽 존재 확인
        club = db.query(Club).filter(Club.id == meeting_data.get('club_id')).first()
        if not club:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="클럽을 찾을 수 없습니다.")

        # 모임 생성
        meeting = Meeting(name=meeting_data.get('name'),
                          description=meeting_data.get('description'),
                          location=meeting_data.get('location'),
                          meeting_time=datetime.fromisoformat(meeting_data.get('meeting_time').replace('Z', '+00:00'))
                          if meeting_data.get('meeting_time') else None,
                          tee_time=datetime.strptime(meeting_data.get('tee_time'), '%H:%M').time()
                          if meeting_data.get('tee_time') and ':' in meeting_data.get('tee_time') else None,
                          max_participants=meeting_data.get('max_participants', 4),
                          meeting_type=MeetingType.ROUND,
                          meeting_subtype=meeting_data.get('meeting_subtype'),
                          total_cost=meeting_data.get('total_cost'),
                          green_fee=meeting_data.get('green_fee'),
                          caddy_fee=meeting_data.get('caddy_fee'),
                          cart_fee=meeting_data.get('cart_fee'),
                          settlement_method=meeting_data.get('settlement_method'),
                          course_name=meeting_data.get('course_name'),
                          hole_count=meeting_data.get('hole_count'),
                          reservation_name=meeting_data.get('reservation_name'),
                          club_id=meeting_data.get('club_id'),
                          status=MeetingStatus.SCHEDULED)

        db.add(meeting)
        db.commit()
        db.refresh(meeting)

        # 관리자를 매니저로 자동 참가
        participant = MeetingParticipant(meeting_id=meeting.id,
                                         user_id=current_user['id'],
                                         status=MeetingParticipantStatus.CONFIRMED,
                                         role=MeetingParticipantRole.ORGANIZER)
        db.add(participant)
        db.commit()

        return {
            "id":
            meeting.id,
            "name":
            meeting.name,
            "description":
            meeting.description,
            "meeting_type":
            meeting.meeting_type.value if hasattr(meeting.meeting_type, 'value') else str(meeting.meeting_type),
            "meeting_subtype":
            meeting.meeting_subtype.value
            if hasattr(meeting.meeting_subtype, 'value') else str(meeting.meeting_subtype),
            "location":
            meeting.location,
            "course_name":
            meeting.course_name,
            "tee_time":
            meeting.tee_times[0] if meeting.tee_times and len(meeting.tee_times) > 0 else None,
            "meeting_time":
            meeting.meeting_time.isoformat() if meeting.meeting_time else None,
            "max_participants":
            meeting.max_participants,
            "status":
            meeting.status.value if hasattr(meeting.status, 'value') else str(meeting.status),
            "club_id":
            meeting.club_id,
            "club_name":
            club.name,
            "participant_count":
            1,
            "created_at":
            meeting.created_at.isoformat() if meeting.created_at else None,
            "updated_at":
            meeting.updated_at.isoformat() if meeting.updated_at else None
        }

    except Exception as e:
        logger.error(f"관리자 라운딩 모임 생성 중 오류: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="라운딩 모임 생성 중 오류가 발생했습니다")


@router.post("/meetings/event")
async def create_admin_event_meeting(meeting_data: dict,
                                     db: Session = Depends(get_db),
                                     current_user: dict = Depends(get_admin_user)):
    """관리자용 이벤트 모임 생성"""
    try:
        from models import Meeting, Club, MeetingParticipant, MeetingType, MeetingStatus, MeetingParticipantStatus, MeetingParticipantRole
        from utils import generate_id
        from datetime import datetime

        # 클럽 존재 확인
        club = db.query(Club).filter(Club.id == meeting_data.get('club_id')).first()
        if not club:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="클럽을 찾을 수 없습니다.")

        # 모임 생성
        meeting = Meeting(name=meeting_data.get('name'),
                          description=meeting_data.get('description'),
                          meeting_time=datetime.fromisoformat(meeting_data.get('meeting_time').replace('Z', '+00:00'))
                          if meeting_data.get('meeting_time') else None,
                          max_participants=meeting_data.get('max_participants', 20),
                          meeting_type=MeetingType.SOCIAL,
                          venue_name=meeting_data.get('venue_name'),
                          social_cost=meeting_data.get('social_cost'),
                          social_settlement_method=meeting_data.get('social_settlement_method'),
                          club_id=meeting_data.get('club_id'),
                          status=MeetingStatus.SCHEDULED)

        db.add(meeting)
        db.commit()
        db.refresh(meeting)

        # 관리자를 매니저로 자동 참가
        participant = MeetingParticipant(meeting_id=meeting.id,
                                         user_id=current_user['id'],
                                         status=MeetingParticipantStatus.CONFIRMED,
                                         role=MeetingParticipantRole.ORGANIZER)
        db.add(participant)
        db.commit()

        return {
            "id":
            meeting.id,
            "name":
            meeting.name,
            "description":
            meeting.description,
            "meeting_type":
            meeting.meeting_type.value if hasattr(meeting.meeting_type, 'value') else str(meeting.meeting_type),
            "venue_name":
            meeting.venue_name,
            "meeting_time":
            meeting.meeting_time.isoformat() if meeting.meeting_time else None,
            "max_participants":
            meeting.max_participants,
            "status":
            meeting.status.value if hasattr(meeting.status, 'value') else str(meeting.status),
            "club_id":
            meeting.club_id,
            "club_name":
            club.name,
            "participant_count":
            1,
            "created_at":
            meeting.created_at.isoformat() if meeting.created_at else None,
            "updated_at":
            meeting.updated_at.isoformat() if meeting.updated_at else None
        }

    except Exception as e:
        logger.error(f"관리자 이벤트 모임 생성 중 오류: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="이벤트 모임 생성 중 오류가 발생했습니다")


@router.post("/meetings")
async def create_admin_meeting(meeting_data: dict,
                               db: Session = Depends(get_db),
                               current_user: dict = Depends(get_admin_user)):
    """관리자용 모임 생성 (일반)"""
    # 관리자용 모임 생성은 별도 엔드포인트를 사용하세요
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED,
                        detail="관리자용 모임 생성은 /admin/meetings/rounding 또는 /admin/meetings/event 엔드포인트를 사용하세요")


@router.put("/meetings/{meeting_id}")
async def update_admin_meeting(meeting_id: int,
                               meeting_data: dict,
                               db: Session = Depends(get_db),
                               current_user: dict = Depends(get_admin_user)):
    """관리자용 모임 수정"""
    try:
        from models import Meeting, Club, MeetingParticipant, MeetingParticipantStatus
        from sqlalchemy import and_

        # 모임 조회
        meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()

        if not meeting:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="모임을 찾을 수 없습니다.")

        # 모임 데이터 업데이트
        update_fields = ['name', 'description', 'location', 'meeting_time', 'max_participants', 'status']
        for field in update_fields:
            if field in meeting_data:
                setattr(meeting, field, meeting_data[field])

        meeting.updated_at = get_kst_now()
        db.commit()
        db.refresh(meeting)

        # 클럽 정보 조회
        club = db.query(Club).filter(Club.id == meeting.club_id).first()

        # 참가자 수 조회
        participant_count = db.query(MeetingParticipant).filter(
            and_(MeetingParticipant.meeting_id == meeting.id,
                 MeetingParticipant.status == MeetingParticipantStatus.CONFIRMED)).count()

        return {
            "id":
            meeting.id,
            "name":
            meeting.name,
            "description":
            meeting.description,
            "meeting_type":
            meeting.meeting_type.value if hasattr(meeting.meeting_type, 'value') else str(meeting.meeting_type),
            "meeting_subtype":
            meeting.meeting_subtype.value
            if hasattr(meeting.meeting_subtype, 'value') else str(meeting.meeting_subtype),
            "location":
            meeting.location,
            "course_name":
            meeting.course_name,
            "venue_name":
            meeting.venue_name,
            "tee_time":
            meeting.tee_times[0] if meeting.tee_times and len(meeting.tee_times) > 0 else None,
            "meeting_time":
            meeting.meeting_time.isoformat() if meeting.meeting_time else None,
            "max_participants":
            meeting.max_participants,
            "status":
            meeting.status.value if hasattr(meeting.status, 'value') else str(meeting.status),
            "club_id":
            meeting.club_id,
            "club_name":
            club.name,
            "participant_count":
            participant_count,
            "created_at":
            meeting.created_at.isoformat() if meeting.created_at else None,
            "updated_at":
            meeting.updated_at.isoformat() if meeting.updated_at else None
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"관리자 모임 수정 중 오류: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="모임 수정 중 오류가 발생했습니다")


@router.get("/meetings/stats", response_model=MeetingStatsResponse)
async def get_meeting_statistics(
        club_id: Optional[int] = Query(None, description="클럽 ID 필터"),
        db: Session = Depends(get_db),
        current_user: dict = Depends(get_admin_user),
):
    """모임 통계 조회 (관리자)"""
    try:
        from models import Meeting, Club, MeetingParticipant
        from schemas import MeetingStatus, MeetingParticipantStatus

        meetings_query = db.query(Meeting)
        if club_id:
            meetings_query = meetings_query.filter(Meeting.club_id == club_id)

        total_meetings = meetings_query.count()
        active_meetings = meetings_query.filter(Meeting.status == MeetingStatus.SCHEDULED).count()
        canceled_meetings = meetings_query.filter(Meeting.status == MeetingStatus.CANCELED).count()
        completed_meetings = meetings_query.filter(Meeting.status == MeetingStatus.COMPLETED).count()

        type_stats = meetings_query.with_entities(Meeting.meeting_type,
                                                  func.count(Meeting.id).label("count")).group_by(
                                                      Meeting.meeting_type).all()
        meetings_by_type = {t.value: c for t, c in type_stats if t}

        twelve_months_ago = datetime.now() - timedelta(days=365)
        monthly_stats = meetings_query.filter(Meeting.created_at >= twelve_months_ago).with_entities(
            extract("year", Meeting.created_at).label("year"),
            extract("month", Meeting.created_at).label("month"),
            func.count(Meeting.id).label("count"),
        ).group_by(extract("year", Meeting.created_at),
                   extract("month", Meeting.created_at)).order_by(extract("year", Meeting.created_at),
                                                                  extract("month", Meeting.created_at)).all()
        meetings_by_month = [{"year": int(y), "month": int(m), "count": c} for y, m, c in monthly_stats]

        participants_query = db.query(MeetingParticipant)
        if club_id:
            participants_query = participants_query.join(Meeting).filter(Meeting.club_id == club_id)
        total_participants = participants_query.filter(
            MeetingParticipant.status == MeetingParticipantStatus.CONFIRMED).count()
        average_participants_per_meeting = round(total_participants / total_meetings, 2) if total_meetings > 0 else 0

        club_stats = meetings_query.with_entities(Meeting.club_id, Club.name.label("club_name"),
                                                  func.count(Meeting.id).label("count")).join(Club).group_by(
                                                      Meeting.club_id, Club.name).all()
        meetings_by_club = [{"club_id": cid, "club_name": cname, "count": c} for cid, cname, c in club_stats]

        upcoming_meetings_count = meetings_query.filter(Meeting.meeting_time > datetime.now(),
                                                        Meeting.status == MeetingStatus.SCHEDULED).count()
        past_meetings_count = meetings_query.filter(Meeting.meeting_time <= datetime.now()).count()

        return MeetingStatsResponse(
            total_meetings=total_meetings,
            active_meetings=active_meetings,
            canceled_meetings=canceled_meetings,
            completed_meetings=completed_meetings,
            meetings_by_type=meetings_by_type,
            meetings_by_month=meetings_by_month,
            total_participants=total_participants,
            average_participants_per_meeting=average_participants_per_meeting,
            meetings_by_club=meetings_by_club,
            upcoming_meetings_count=upcoming_meetings_count,
            past_meetings_count=past_meetings_count,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"모임 통계 조회 중 오류: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.delete("/meetings/{meeting_id}")
async def delete_admin_meeting(meeting_id: int,
                               db: Session = Depends(get_db),
                               current_user: dict = Depends(get_admin_user)):
    """관리자용 모임 삭제"""
    try:
        logger.info(f"관리자 모임 삭제 시작 - meeting_id: {meeting_id}")

        # 모임 조회
        meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
        if not meeting:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="모임을 찾을 수 없습니다")

        # 모임 삭제 (실제 삭제 또는 소프트 삭제)
        # 참가자, 팀 등 관련 데이터도 함께 삭제됨 (CASCADE 설정)
        db.delete(meeting)
        db.commit()

        logger.info(f"관리자 모임 삭제 완료 - meeting_id: {meeting_id}")
        return {"message": "모임이 삭제되었습니다"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"관리자 모임 삭제 중 오류: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"서버 오류: {str(e)}")
