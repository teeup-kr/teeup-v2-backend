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


@router.get("/meetings")
async def admin_get_meetings(
    page: int = Query(1, ge=1, description="페이지 번호"),
    limit: int = Query(10, ge=1, le=100, description="페이지당 항목 수"),
    status: Optional[str] = Query(None, description="모임 상태 필터"),
    search: Optional[str] = Query(None, description="검색어"),
    club_id: Optional[int] = Query(None, description="클럽 ID 필터"),
    meeting_type: Optional[str] = Query(None, description="모임 유형: ROUND, SOCIAL"),
    current_user: dict = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """관리자용 모임 목록 조회 (라운딩+소셜 통합, 유형 필터 가능)"""
    try:
        from models import Meeting, Club, MeetingParticipant
        from schemas import MeetingType, MeetingParticipantStatus, MeetingParticipantRole
        from sqlalchemy import desc, and_, or_

        query = db.query(Meeting).join(Club)
        if meeting_type == "ROUND":
            query = query.filter(Meeting.meeting_type == MeetingType.ROUND)
        elif meeting_type == "SOCIAL":
            query = query.filter(Meeting.meeting_type == MeetingType.SOCIAL)

        if club_id:
            query = query.filter(Meeting.club_id == club_id)
        if status:
            query = query.filter(Meeting.status == status)
        if search:
            query = query.filter(
                or_(
                    Meeting.name.contains(search),
                    Meeting.location.contains(search),
                    Meeting.course_name.contains(search),
                    Meeting.venue_name.contains(search),
                )
            )

        total = query.count()
        meetings = query.order_by(desc(Meeting.created_at)).offset((page - 1) * limit).limit(limit).all()

        meeting_data = []
        for meeting in meetings:
            participant_count = db.query(MeetingParticipant).filter(
                and_(MeetingParticipant.meeting_id == meeting.id, MeetingParticipant.status == MeetingParticipantStatus.CONFIRMED)
            ).count()
            organizer_participant = db.query(MeetingParticipant).filter(
                and_(MeetingParticipant.meeting_id == meeting.id, MeetingParticipant.role == MeetingParticipantRole.ORGANIZER)
            ).first()
            creator_info = None
            if organizer_participant and organizer_participant.user:
                creator_info = {
                    "id": organizer_participant.user.id,
                    "realname": organizer_participant.user.realname,
                    "nickname": organizer_participant.user.nickname,
                    "email": organizer_participant.user.email,
                }
            meeting_type_str = meeting.meeting_type.value if hasattr(meeting.meeting_type, "value") else str(meeting.meeting_type)
            meeting_subtype_str = meeting.meeting_subtype.value if meeting.meeting_subtype and hasattr(meeting.meeting_subtype, "value") else str(meeting.meeting_subtype) if meeting.meeting_subtype else None
            status_str = meeting.status.value if hasattr(meeting.status, "value") else str(meeting.status)
            meeting_data.append({
                "id": meeting.id,
                "name": meeting.name or "",
                "description": meeting.description or "",
                "meeting_type": meeting_type_str,
                "meeting_subtype": meeting_subtype_str,
                "location": meeting.location or "",
                "course_name": meeting.course_name or "",
                "venue_name": getattr(meeting, "venue_name", None) or "",
                "tee_time": meeting.tee_times[0] if meeting.tee_times and len(meeting.tee_times) > 0 else None,
                "meeting_time": meeting.meeting_time.isoformat() if meeting.meeting_time else None,
                "max_participants": int(meeting.max_participants) if meeting.max_participants else 0,
                "status": status_str,
                "club_id": meeting.club_id,
                "club_name": meeting.club.name if meeting.club else "",
                "participant_count": participant_count,
                "creator": creator_info,
                "created_at": meeting.created_at.isoformat() if meeting.created_at else None,
                "updated_at": meeting.updated_at.isoformat() if meeting.updated_at else None,
            })

        total_pages = (total + limit - 1) // limit
        return {"data": meeting_data, "total": total, "page": page, "limit": limit, "total_pages": total_pages}
    except Exception as e:
        logger.error(f"관리자 모임 목록 조회 중 오류: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="모임 목록 조회 중 오류가 발생했습니다")


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
        from models import Meeting, Club, MeetingParticipant, User
        from schemas import MeetingType
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
                MeetingParticipant.meeting_id == meeting.id
            ).count()

            # 개설자(생성자) 조회
            creator_info = None
            if meeting.created_by:
                creator = db.query(User).filter(User.id == meeting.created_by).first()
                if creator:
                    creator_info = {
                        "id": creator.id,
                        "realname": creator.realname,
                        "nickname": creator.nickname,
                        "email": creator.email
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
        from models import Meeting, Club, MeetingParticipant, User
        from schemas import MeetingType
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
                MeetingParticipant.meeting_id == meeting.id
            ).count()

            # 개설자(생성자) 조회
            creator_info = None
            if meeting.created_by:
                creator = db.query(User).filter(User.id == meeting.created_by).first()
                if creator:
                    creator_info = {
                        "id": creator.id,
                        "realname": creator.realname,
                        "nickname": creator.nickname,
                        "email": creator.email
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


@router.get("/meetings/{meeting_id}/participants")
async def get_admin_meeting_participants(
    meeting_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_admin_user),
):
    """관리자용 모임 참가자 목록 조회 (라운딩/소셜 공통)"""
    try:
        from models import Meeting, MeetingParticipant, User, Guest
        from schemas import MeetingParticipantStatus

        meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
        if not meeting:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="모임을 찾을 수 없습니다.")

        participants = db.query(MeetingParticipant).filter(MeetingParticipant.meeting_id == meeting_id).all()
        result = []
        for p in participants:
            if p.guest_id:
                guest = db.query(Guest).filter(Guest.id == p.guest_id).first()
                name = guest.name if guest else "게스트"
                result.append({
                    "id": p.id, "user_id": p.user_id, "guest_id": p.guest_id,
                    "user_name": name, "user_nickname": name, "name": name,
                    "status": p.status.value if hasattr(p.status, "value") else str(p.status),
                    "role": p.role.value if hasattr(p.role, "value") else str(p.role),
                    "is_guest": True, "created_at": p.created_at.isoformat() if p.created_at else None,
                })
            else:
                user = db.query(User).filter(User.id == p.user_id).first() if p.user_id else None
                if not user:
                    continue
                result.append({
                    "id": p.id, "user_id": p.user_id, "guest_id": None,
                    "user_name": user.realname or "이름 없음", "user_nickname": user.nickname or "닉네임 없음",
                    "name": user.realname or "이름 없음",
                    "status": p.status.value if hasattr(p.status, "value") else str(p.status),
                    "role": p.role.value if hasattr(p.role, "value") else str(p.role),
                    "is_guest": False, "created_at": p.created_at.isoformat() if p.created_at else None,
                })
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"관리자 참가자 목록 조회 중 오류: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/meetings/{meeting_id}/settlement")
async def get_admin_meeting_settlement(
    meeting_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_admin_user),
):
    """관리자용 모임 정산 조회 (라운딩/소셜 공통)"""
    try:
        from routers.meetings.settlement import _build_settlement_response
        return _build_settlement_response(meeting_id, db)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"관리자 정산 조회 중 오류: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/meetings/{meeting_id}/settlement/available-participants")
async def get_admin_settlement_available_participants(
    meeting_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_admin_user),
):
    """관리자용 정산 대상자(참가자) 목록 조회"""
    try:
        from models import Meeting, MeetingParticipant
        from schemas import MeetingParticipantStatus
        from sqlalchemy.orm import joinedload

        meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
        if not meeting:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="모임을 찾을 수 없습니다.")

        participants = db.query(MeetingParticipant).options(
            joinedload(MeetingParticipant.user),
            joinedload(MeetingParticipant.guest)
        ).filter(
            MeetingParticipant.meeting_id == meeting_id,
            MeetingParticipant.status == MeetingParticipantStatus.CONFIRMED
        ).all()

        participant_list = []
        for mp in participants:
            if mp.guest_id:
                guest = mp.guest
                participant_list.append({
                    "id": mp.guest_id,
                    "participant_id": mp.id,
                    "name": guest.name if guest else "게스트",
                    "email": None,
                    "role": mp.role.value if mp.role else None,
                    "is_guest": True,
                })
            else:
                user = mp.user
                if user:
                    participant_list.append({
                        "id": user.id,
                        "participant_id": mp.id,
                        "name": user.nickname or user.realname,
                        "email": user.email,
                        "role": mp.role.value if mp.role else None,
                        "is_guest": False,
                    })
        return {"participants": participant_list}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"관리자 정산 대상자 조회 중 오류: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/meetings/{meeting_id}/settlement/rounding")
async def create_admin_rounding_settlement(
    meeting_id: int,
    settlement_data: dict,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_admin_user),
):
    """관리자용 라운딩 정산 생성/수정 (정규화 모델: Expense → ExpenseItem → ExpenseItemParticipant)"""
    try:
        from models import Meeting, MeetingParticipant, Expense, ExpenseItem, ExpenseItemParticipant
        from models.enums import ExpenseItemType
        from schemas import MeetingType, MeetingParticipantStatus, MeetingParticipantRole
        from routers.meetings.settlement import send_settlement_created_notification
        from decimal import Decimal
        from sqlalchemy import or_

        meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
        if not meeting:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="모임을 찾을 수 없습니다.")
        if meeting.meeting_type != MeetingType.ROUND:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="라운딩 모임이 아닙니다.")
        if meeting.settlement_confirmed:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="정산이 이미 확정되어 수정할 수 없습니다.")

        created_by_user_id = meeting.created_by
        if not created_by_user_id:
            organizer = db.query(MeetingParticipant).filter(
                MeetingParticipant.meeting_id == meeting_id,
                MeetingParticipant.role == MeetingParticipantRole.ORGANIZER,
                MeetingParticipant.status == MeetingParticipantStatus.CONFIRMED
            ).first()
            if organizer and organizer.user_id:
                created_by_user_id = organizer.user_id
            else:
                first_p = db.query(MeetingParticipant).filter(
                    MeetingParticipant.meeting_id == meeting_id,
                    MeetingParticipant.status == MeetingParticipantStatus.CONFIRMED,
                    MeetingParticipant.user_id.isnot(None)
                ).first()
                created_by_user_id = first_p.user_id if first_p else None
        if not created_by_user_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="정산 생성자(user_id)를 찾을 수 없습니다. 참가자를 추가해주세요.")

        total_cost = Decimal(str(settlement_data.get('total_cost', 0)))
        green_fee = Decimal(str(settlement_data.get('green_fee', 0)))
        caddy_fee = Decimal(str(settlement_data.get('caddy_fee', 0)))
        cart_fee = Decimal(str(settlement_data.get('cart_fee', 0)))
        other_fee = Decimal(str(settlement_data.get('other_fee', 0)))
        notes = settlement_data.get('notes', '')
        green_fee_participants = settlement_data.get('green_fee_participants', [])
        green_fee_exempted = settlement_data.get('green_fee_exempted', [])
        cart_fee_participants = settlement_data.get('cart_fee_participants', [])
        cart_fee_exempted = settlement_data.get('cart_fee_exempted', [])
        caddy_fee_participants = settlement_data.get('caddy_fee_participants', [])
        caddy_fee_exempted = settlement_data.get('caddy_fee_exempted', [])
        other_expense_items = settlement_data.get('other_expense_items', [])
        exclude_remaining_amount = settlement_data.get('exclude_remaining_amount', False)
        all_covered_by_fee = settlement_data.get('all_covered_by_fee', False)
        green_fee_covered_by_fee = settlement_data.get('green_fee_covered_by_fee', False)
        caddy_fee_covered_by_fee = settlement_data.get('caddy_fee_covered_by_fee', False)
        cart_fee_covered_by_fee = settlement_data.get('cart_fee_covered_by_fee', False)

        all_settlement_targets = set()
        if not all_covered_by_fee and not green_fee_covered_by_fee:
            all_settlement_targets.update(green_fee_participants)
        if not all_covered_by_fee and not cart_fee_covered_by_fee:
            all_settlement_targets.update(cart_fee_participants)
        if not all_covered_by_fee and not caddy_fee_covered_by_fee:
            all_settlement_targets.update(caddy_fee_participants)
        if not all_covered_by_fee:
            for item in other_expense_items:
                for pid in (item.get('participants') or []):
                    if pid and pid != 'UNSETTLED':
                        all_settlement_targets.add(pid)

        settlement_targets = list(all_settlement_targets)
        target_count = len(settlement_targets)
        if target_count == 0 and not exclude_remaining_amount and not all_covered_by_fee:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="정산 대상자를 선택해주세요.")
        if not all_covered_by_fee and not green_fee_covered_by_fee and len(green_fee_participants) == 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="그린피의 정산 대상자를 선택해주세요.")
        if not all_covered_by_fee and not cart_fee_covered_by_fee and len(cart_fee_participants) == 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="카트비의 정산 대상자를 선택해주세요.")
        if not all_covered_by_fee and not caddy_fee_covered_by_fee and len(caddy_fee_participants) == 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="캐디피의 정산 대상자를 선택해주세요.")
        if not all_covered_by_fee:
            for idx, item in enumerate(other_expense_items):
                if not (item.get('participants') or []):
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"기타 비용 항목 {idx + 1}의 정산 대상자를 선택해주세요.")

        amount_per_person = Decimal('0') if all_covered_by_fee else (total_cost / target_count if target_count > 0 else Decimal('0'))

        def _add_item_participants(expense_item, participant_ids, exempted_ids, amount_per_person_val):
            for pid in participant_ids:
                if pid in (exempted_ids or []):
                    continue
                mp = db.query(MeetingParticipant).filter(
                    MeetingParticipant.meeting_id == meeting_id,
                    or_(MeetingParticipant.user_id == pid, MeetingParticipant.guest_id == pid)
                ).first()
                if mp:
                    eip = ExpenseItemParticipant(
                        expense_item_id=expense_item.id,
                        user_id=mp.user_id,
                        guest_id=mp.guest_id,
                        is_exempted=False,
                        amount=amount_per_person_val
                    )
                    db.add(eip)

        expense = Expense(
            title=f"{meeting.name} 라운딩 정산",
            description=f"그린피: {green_fee:,}원, 캐디피: {caddy_fee:,}원, 카트비: {cart_fee:,}원, 기타: {other_fee:,}원",
            meeting_id=meeting_id,
            club_id=meeting.club_id,
            created_by=created_by_user_id,
            notes=notes,
            exclude_remaining_amount=exclude_remaining_amount,
        )
        db.add(expense)
        db.flush()

        order_idx = 0
        if green_fee > 0:
            gf_item = ExpenseItem(
                expense_id=expense.id,
                type=ExpenseItemType.GREEN_FEE,
                amount=green_fee,
                covered_by_fee=green_fee_covered_by_fee,
                order_index=order_idx,
            )
            db.add(gf_item)
            db.flush()
            if not green_fee_covered_by_fee and green_fee_participants:
                amt = green_fee / len(green_fee_participants)
                _add_item_participants(gf_item, green_fee_participants, green_fee_exempted, amt)
            order_idx += 1

        if caddy_fee > 0:
            cf_item = ExpenseItem(
                expense_id=expense.id,
                type=ExpenseItemType.CADDY_FEE,
                amount=caddy_fee,
                covered_by_fee=caddy_fee_covered_by_fee,
                order_index=order_idx,
            )
            db.add(cf_item)
            db.flush()
            if not caddy_fee_covered_by_fee and caddy_fee_participants:
                amt = caddy_fee / len(caddy_fee_participants)
                _add_item_participants(cf_item, caddy_fee_participants, caddy_fee_exempted, amt)
            order_idx += 1

        if cart_fee > 0:
            crf_item = ExpenseItem(
                expense_id=expense.id,
                type=ExpenseItemType.CART_FEE,
                amount=cart_fee,
                covered_by_fee=cart_fee_covered_by_fee,
                order_index=order_idx,
            )
            db.add(crf_item)
            db.flush()
            if not cart_fee_covered_by_fee and cart_fee_participants:
                amt = cart_fee / len(cart_fee_participants)
                _add_item_participants(crf_item, cart_fee_participants, cart_fee_exempted, amt)
            order_idx += 1

        for oi in (other_expense_items or []):
            amt = Decimal(str(oi.get('amount', 0)))
            if amt <= 0:
                continue
            participants = oi.get('participants') or []
            title = oi.get('title') or oi.get('name') or '기타 비용'
            other_item = ExpenseItem(
                expense_id=expense.id,
                type=ExpenseItemType.OTHER,
                title=title,
                amount=amt,
                covered_by_fee=False,
                order_index=order_idx,
            )
            db.add(other_item)
            db.flush()
            if participants:
                per_amt = amt / len(participants)
                _add_item_participants(other_item, participants, [], per_amt)
            order_idx += 1

        db.commit()
        logger.info(f"관리자 라운딩 정산 생성 완료 - expense.id: {expense.id}")
        try:
            send_settlement_created_notification(meeting_id, db, is_edit=False)
        except Exception as e:
            logger.error(f"정산 알림 전송 실패: {str(e)}")

        return {
            "message": "라운딩 정산이 생성되었습니다.",
            "settlement_id": expense.id,
            "total_cost": float(total_cost),
            "amount_per_person": float(amount_per_person),
            "target_count": target_count
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"관리자 라운딩 정산 생성 오류: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/meetings/{meeting_id}")
async def get_admin_meeting(meeting_id: int,
                            db: Session = Depends(get_db),
                            current_user: dict = Depends(get_admin_user)):
    """관리자용 모임 상세 조회"""
    try:
        from models import Meeting, Club, MeetingParticipant
        from sqlalchemy import and_

        # 모임 조회
        meeting = db.query(Meeting).join(Club).filter(Meeting.id == meeting_id).first()

        if not meeting:
            from fastapi import status as http_status
            raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="모임을 찾을 수 없습니다.")

        # 참가자 수 조회
        participant_count = db.query(MeetingParticipant).filter(
            MeetingParticipant.meeting_id == meeting.id
        ).count()

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
        from models import Meeting, Club, MeetingParticipant, MeetingType, MeetingStatus, ParticipantType
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
                          status=MeetingStatus.SCHEDULED,
                          created_by=current_user['id'])

        db.add(meeting)
        db.commit()
        db.refresh(meeting)

        # 관리자를 참가자로 자동 추가
        participant = MeetingParticipant(
            meeting_id=meeting.id,
            user_id=current_user['id'],
            participant_type=ParticipantType.USER
        )
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
        from models import Meeting, Club, MeetingParticipant, MeetingType, MeetingStatus, ParticipantType
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
                          status=MeetingStatus.SCHEDULED,
                          created_by=current_user['id'])

        db.add(meeting)
        db.commit()
        db.refresh(meeting)

        # 관리자를 참가자로 자동 추가
        participant = MeetingParticipant(
            meeting_id=meeting.id,
            user_id=current_user['id'],
            participant_type=ParticipantType.USER
        )
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
        from models import Meeting, Club, MeetingParticipant
        from sqlalchemy import and_

        # 모임 조회
        meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()

        if not meeting:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="모임을 찾을 수 없습니다.")

        # 모임 데이터 업데이트
        update_fields = ['name', 'description', 'location', 'meeting_time', 'max_participants', 'status']
        for field in update_fields:
            if field in meeting_data:
                value = meeting_data[field]
                if field == 'meeting_time' and value and isinstance(value, str):
                    try:
                        value = datetime.fromisoformat(value.replace('Z', '+00:00'))
                    except (ValueError, TypeError):
                        pass
                setattr(meeting, field, value)

        meeting.updated_at = get_kst_now()
        db.commit()
        db.refresh(meeting)

        # 클럽 정보 조회
        club = db.query(Club).filter(Club.id == meeting.club_id).first()

        # 참가자 수 조회
        participant_count = db.query(MeetingParticipant).filter(
            MeetingParticipant.meeting_id == meeting.id
        ).count()

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

        type_stats = meetings_query.with_entities(Meeting.meeting_type, func.count(Meeting.id).label("count")).group_by(Meeting.meeting_type).all()
        meetings_by_type = {t.value: c for t, c in type_stats if t}

        twelve_months_ago = datetime.now() - timedelta(days=365)
        monthly_stats = meetings_query.filter(Meeting.created_at >= twelve_months_ago).with_entities(
            extract("year", Meeting.created_at).label("year"),
            extract("month", Meeting.created_at).label("month"),
            func.count(Meeting.id).label("count"),
        ).group_by(extract("year", Meeting.created_at), extract("month", Meeting.created_at)).order_by(
            extract("year", Meeting.created_at), extract("month", Meeting.created_at)
        ).all()
        meetings_by_month = [{"year": int(y), "month": int(m), "count": c} for y, m, c in monthly_stats]

        participants_query = db.query(MeetingParticipant)
        if club_id:
            participants_query = participants_query.join(Meeting).filter(Meeting.club_id == club_id)
        total_participants = participants_query.filter(MeetingParticipant.status == MeetingParticipantStatus.CONFIRMED).count()
        average_participants_per_meeting = round(total_participants / total_meetings, 2) if total_meetings > 0 else 0

        club_stats = meetings_query.with_entities(Meeting.club_id, Club.name.label("club_name"), func.count(Meeting.id).label("count")).join(Club).group_by(Meeting.club_id, Club.name).all()
        meetings_by_club = [{"club_id": cid, "club_name": cname, "count": c} for cid, cname, c in club_stats]

        upcoming_meetings_count = meetings_query.filter(Meeting.meeting_time > datetime.now(), Meeting.status == MeetingStatus.SCHEDULED).count()
        past_meetings_count = meetings_query.filter(Meeting.meeting_time <= datetime.now()).count()

        return MeetingStatsResponse(
            total_meetings=total_meetings, active_meetings=active_meetings,
            canceled_meetings=canceled_meetings, completed_meetings=completed_meetings,
            meetings_by_type=meetings_by_type, meetings_by_month=meetings_by_month,
            total_participants=total_participants, average_participants_per_meeting=average_participants_per_meeting,
            meetings_by_club=meetings_by_club, upcoming_meetings_count=upcoming_meetings_count,
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
