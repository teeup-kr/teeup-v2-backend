"""
라운딩 관리 API - ROUND 타입 전용
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, and_, or_, case
from typing import List, Optional
from datetime import date, datetime, time
from utils.datetime_utils import get_kst_now
import logging

from database import get_db
from models import (User, Club, ClubMembership, Meeting, MeetingParticipant, Team, TeamMember, MeetingResult, Guest,
                    ParticipantType, Gender)
from schemas import (MeetingType, MeetingSubtype, SettlementMethod, MeetingStatus, ClubRole, TeamFormationMode)
from schemas import (RoundingMeetingCreate, MeetingUpdate, MeetingResponse, MeetingParticipantResponse,
                     PaginatedResponse, TeamResponse, TeamMemberResponse, TeamStatus)
from routers.auth import get_current_active_user, get_current_user, get_current_user_allow_both, get_user_role_from_token
from fastapi.security import HTTPAuthorizationCredentials
from utils.jwt_auth import security
from utils.permissions import MEMBERSHIP_ACTIVE_STATUSES
from utils.notification_service import (
    notify_organizer_participant_added_after_recruitment_closed,
    notify_round_participants_status_changed,
)
from utils.handicap_calculator import calculate_handicap_from_average_score
from routers.meetings.workflow import close_meetings_with_passed_deadline

router = APIRouter(prefix="/rounds", tags=["라운딩 관리"])
logger = logging.getLogger(__name__)

# =============================================================================
# 라운딩 목록 조회
# =============================================================================


@router.get("/", response_model=PaginatedResponse[MeetingResponse])
async def get_rounds(page: int = Query(1, ge=1, description="페이지 번호"),
                     limit: int = Query(10, ge=1, le=100, description="페이지당 항목 수"),
                     status_group: Optional[str] = Query(None, description="상태 그룹(active|completed)"),
                     search: Optional[str] = Query(None, description="검색어"),
                     start_date: Optional[date] = Query(None, description="시작일(YYYY-MM-DD)"),
                     end_date: Optional[date] = Query(None, description="종료일(YYYY-MM-DD)"),
                     current_user: User = Depends(get_current_active_user),
                     db: Session = Depends(get_db)):
    """라운딩 목록 조회 - 모든 라운딩 노출(완료/취소 포함). 프라이빗은 참가한 모임에서만 노출."""

    # 마감일 지난 모임을 IN_PROGRESS로 갱신 (크론 없이 목록 조회 시 반영)
    try:
        close_meetings_with_passed_deadline(db)
    except Exception as e:
        logger.warning(f"마감일 경과 자동 갱신 스킵: {e}")

    # 프라이빗 라운딩: 목록에는 참가자/생성자/클럽 리더·매니저만 노출
    user_participant_meeting_ids = db.query(
        MeetingParticipant.meeting_id).filter(MeetingParticipant.user_id == current_user.id).subquery()
    user_created_meeting_ids = db.query(Meeting.id).filter(Meeting.created_by == current_user.id).subquery()
    manager_club_ids = db.query(ClubMembership.club_id).filter(
        and_(
            ClubMembership.user_id == current_user.id,
            ClubMembership.status.in_(MEMBERSHIP_ACTIVE_STATUSES),
            ClubMembership.role.in_([ClubRole.LEADER, ClubRole.MANAGER]),
        )
    ).subquery()

    # 모든 라운딩(클럽 무관) 중: 일반 라운딩이거나, 프라이빗이면 참가/생성/매니저인 경우만
    query = db.query(Meeting).join(Club).filter(
        and_(
            Meeting.meeting_type == MeetingType.ROUND,
            or_(
                Meeting.is_private == False,
                and_(
                    Meeting.is_private == True,
                    or_(
                        Meeting.id.in_(user_participant_meeting_ids),
                        Meeting.id.in_(user_created_meeting_ids),
                        Meeting.club_id.in_(manager_club_ids),
                    ),
                ),
            ),
        )
    )

    # 상태 필터
    if status_group == "active":
        query = query.filter(Meeting.status.in_([MeetingStatus.SCHEDULED, MeetingStatus.IN_PROGRESS]))
    elif status_group == "completed":
        query = query.filter(Meeting.status.in_([MeetingStatus.COMPLETED, MeetingStatus.CANCELED]))

    # 검색 필터
    if search:
        search_filter = or_(Meeting.name.contains(search), Meeting.course_name.contains(search),
                            Meeting.location.contains(search))
        query = query.filter(search_filter)
    if start_date:
        query = query.filter(Meeting.meeting_time >= datetime.combine(start_date, time.min))
    if end_date:
        query = query.filter(Meeting.meeting_time <= datetime.combine(end_date, time.max))

    # 총 개수
    total = query.count()
    logger.info(f"🔍 라운딩 모임 조회 - total: {total}, page: {page}, limit: {limit}")

    # 정렬: 상태별 우선순위 (SCHEDULED → IN_PROGRESS → COMPLETED)
    # CANCELED는 999로 설정하여 맨 뒤로
    # 동일 상태 내에서는 최신 모임부터 (created_at 내림차순)
    status_order = case((Meeting.status == MeetingStatus.SCHEDULED, 1),
                        (Meeting.status == MeetingStatus.IN_PROGRESS, 2),
                        (Meeting.status == MeetingStatus.COMPLETED, 3), (Meeting.status == MeetingStatus.CANCELED, 999),
                        else_=5)
    query = query.order_by(status_order.asc(), Meeting.created_at.desc())

    # 페이지네이션
    meetings = query.offset((page - 1) * limit).limit(limit).all()

    # 응답 데이터 구성
    meeting_responses = []
    for meeting in meetings:
        participant_count = db.query(MeetingParticipant).filter(MeetingParticipant.meeting_id == meeting.id).count()

        # 디버깅: 첫 번째 모임의 참가자 수 확인
        if len(meeting_responses) == 0:
            logger.info(
                f"🔍 첫 번째 모임 참가자 수 - meeting_id: {meeting.id}, name: {meeting.name}, participant_count: {participant_count}"
            )

        # tee_times에서 첫 번째 시간을 tee_time으로 설정
        tee_time = None
        if meeting.tee_times and len(meeting.tee_times) > 0:
            tee_time_str = meeting.tee_times[0]
            if isinstance(tee_time_str, str):
                # "18:53" 형태의 문자열을 time 객체로 변환
                hour, minute = map(int, tee_time_str.split(':'))
                tee_time = time(hour, minute)

        # 생성자 정보 조회
        created_by_name = None
        if meeting.created_by:
            creator = db.query(User).filter(User.id == meeting.created_by).first()
            if creator:
                created_by_name = creator.nickname or creator.name

        meeting_dict = {**meeting.__dict__}
        meeting_dict.pop("_sa_instance_state", None)
        meeting_dict["tee_times"] = meeting.tee_times or []

        meeting_responses.append(
            MeetingResponse(**meeting_dict,
                            club_name=meeting.club.name,
                            participant_count=participant_count,
                            created_by_name=created_by_name,
                            tee_time=tee_time))

    calculated_total_pages = (total + limit - 1) // limit
    logger.info(
        f"🔍 라운딩 모임 응답 - total: {total}, total_pages: {calculated_total_pages}, meetings_count: {len(meeting_responses)}"
    )

    return PaginatedResponse(data=meeting_responses,
                             total=total,
                             page=page,
                             limit=limit,
                             total_pages=calculated_total_pages)


# =============================================================================
# 라운딩 생성
# =============================================================================


@router.post("/", response_model=MeetingResponse)
async def create_round(meeting_data: RoundingMeetingCreate,
                       current_user: User = Depends(get_current_user_allow_both),
                       db: Session = Depends(get_db)):
    """라운딩 생성 (리더/매니저만 가능). club_id는 body에 포함."""
    club_id = meeting_data.club_id

    # 클럽 멤버십 확인
    membership = db.query(ClubMembership).filter(
        and_(ClubMembership.user_id == current_user.id, ClubMembership.club_id == club_id,
             ClubMembership.status.in_(MEMBERSHIP_ACTIVE_STATUSES))).first()

    if not membership:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="해당 클럽의 멤버가 아닙니다.")

    # 라운딩은 리더/매니저만 생성 가능
    if membership.role not in [ClubRole.LEADER, ClubRole.MANAGER]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="라운딩은 클럽 리더/매니저만 생성할 수 있습니다.")

    # 프라이빗 라운딩인 경우 참가자 선택 검증
    is_private = meeting_data.is_private or False
    if is_private:
        if not meeting_data.selected_participants or len(meeting_data.selected_participants) == 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="프라이빗 라운딩은 최소 1명 이상의 참가자를 선택해야 합니다.")

    if meeting_data.selected_guests:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="게스트는 라운딩 생성 후 /api/v1/meetings/{meeting_id}/guests로 추가해주세요.")

    # 모임 생성
    meeting = Meeting(name=meeting_data.name,
                      description=meeting_data.description,
                      location=meeting_data.location,
                      meeting_time=meeting_data.meeting_time,
                      tee_times=meeting_data.tee_times,
                      max_participants=meeting_data.max_participants,
                      meeting_type=MeetingType.ROUND,
                      meeting_subtype=meeting_data.meeting_subtype,
                      total_cost=meeting_data.total_cost,
                      green_fee=meeting_data.green_fee,
                      caddy_fee=meeting_data.caddy_fee,
                      cart_fee=meeting_data.cart_fee,
                      settlement_method=meeting_data.settlement_method,
                      course_name=meeting_data.course_name,
                      hole_count=meeting_data.hole_count,
                      reservation_name=meeting_data.reservation_name,
                      application_deadline=meeting_data.application_deadline,
                      team_formation_mode=meeting_data.team_formation_mode,
                      team_size=meeting_data.team_size,
                      club_id=meeting_data.club_id,
                      status=MeetingStatus.SCHEDULED,
                      is_private=is_private,
                      created_by=current_user.id)

    db.add(meeting)
    db.commit()
    db.refresh(meeting)

    participant_count = 0

    # 프라이빗 라운딩인 경우
    if is_private:
        # 선택된 참가자들을 참가자로 추가
        if meeting_data.selected_participants:
            # 참가자 검증: 모두 해당 클럽의 활성 멤버인지 확인
            for user_id in meeting_data.selected_participants:
                member_check = db.query(ClubMembership).filter(
                    and_(ClubMembership.user_id == user_id, ClubMembership.club_id == club_id,
                         ClubMembership.status.in_(MEMBERSHIP_ACTIVE_STATUSES))).first()

                if not member_check:
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                        detail=f"user_id {user_id}는 해당 클럽의 활성 멤버가 아닙니다.")

                # 중복 체크
                existing_participant = db.query(MeetingParticipant).filter(
                    and_(MeetingParticipant.meeting_id == meeting.id, MeetingParticipant.user_id == user_id)).first()

                if not existing_participant:
                    participant = MeetingParticipant(meeting_id=meeting.id,
                                                     user_id=user_id,
                                                     participant_type=ParticipantType.USER)
                    db.add(participant)
                    participant_count += 1

        db.commit()

        # 선택된 참가자들에게 프라이빗 라운딩 초대 알림 전송
        if meeting_data.selected_participants:
            try:
                from utils.notification_service import create_notification
                from models import NotificationType

                for user_id in meeting_data.selected_participants:
                    try:
                        create_notification(
                            db=db,
                            user_id=user_id,
                            notification_type=NotificationType.MEETING_REMINDER,  # 적절한 타입으로 변경 가능
                            title="프라이빗 라운딩 초대",
                            content=
                            f"'{club.name}' 클럽의 프라이빗 라운딩 '{meeting_data.name}'에 초대되었습니다.\n일시: {meeting_data.meeting_time.strftime('%Y년 %m월 %d일 %H:%M') if meeting_data.meeting_time else '미정'}\n장소: {meeting_data.location or '미정'}"
                        )
                    except Exception as e:
                        logger.error(f"프라이빗 라운딩 초대 알림 전송 실패 - user_id: {user_id}, error: {str(e)}")
                        # 알림 실패해도 계속 진행
            except Exception as e:
                logger.error(f"프라이빗 라운딩 알림 전송 중 오류: {str(e)}")
                # 알림 실패해도 계속 진행

    else:
        # 일반 라운딩: 생성자를 참가자로 자동 추가
        participant = MeetingParticipant(meeting_id=meeting.id,
                                         user_id=current_user.id,
                                         participant_type=ParticipantType.USER)
        db.add(participant)
        db.commit()
        participant_count = 1

    # 클럽 정보 조회
    club = db.query(Club).filter(Club.id == meeting.club_id).first()

    # 생성자 정보 조회
    created_by_name = None
    if meeting.created_by:
        creator = db.query(User).filter(User.id == meeting.created_by).first()
        if creator:
            created_by_name = creator.nickname or creator.name

    # tee_times에서 첫 번째 시간을 tee_time으로 설정
    tee_time = None
    if meeting.tee_times and len(meeting.tee_times) > 0:
        tee_time_str = meeting.tee_times[0]
        if isinstance(tee_time_str, str):
            # "18:53" 형태의 문자열을 time 객체로 변환
            hour, minute = map(int, tee_time_str.split(':'))
            tee_time = time(hour, minute)

    meeting_dict = {**meeting.__dict__}
    meeting_dict.pop("_sa_instance_state", None)
    meeting_dict["tee_times"] = meeting.tee_times or []

    return MeetingResponse(**meeting_dict,
                           club_name=club.name,
                           participant_count=participant_count,
                           created_by_name=created_by_name,
                           tee_time=tee_time)


# =============================================================================
# 라운딩 상세 조회
# =============================================================================


@router.get("/{meeting_id}", response_model=MeetingResponse)
async def get_round(meeting_id: int,
                    current_user: User = Depends(get_current_user_allow_both),
                    db: Session = Depends(get_db)):
    """라운딩 상세 조회"""

    # 모임 조회
    meeting = db.query(Meeting).join(Club).filter(
        and_(Meeting.id == meeting_id, Meeting.meeting_type == MeetingType.ROUND)).first()

    if not meeting:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="라운딩을 찾을 수 없습니다.")

    # 프라이빗 라운딩인 경우 권한 체크
    if meeting.is_private:
        # 관리자는 접근 가능
        from models import Admin
        admin = db.query(Admin).filter(Admin.id == current_user.id, Admin.deleted_at.is_(None)).first()

        if not admin:
            # 참가자 또는 생성자인지 확인
            is_participant = db.query(MeetingParticipant).filter(
                and_(MeetingParticipant.meeting_id == meeting.id,
                     MeetingParticipant.user_id == current_user.id)).first()

            is_creator = meeting.created_by == current_user.id
            is_manager_or_leader = db.query(ClubMembership).filter(
                and_(
                    ClubMembership.user_id == current_user.id,
                    ClubMembership.club_id == meeting.club_id,
                    ClubMembership.status.in_(MEMBERSHIP_ACTIVE_STATUSES),
                    ClubMembership.role.in_([ClubRole.LEADER, ClubRole.MANAGER]),
                )
            ).first()

            if not is_participant and not is_creator and not is_manager_or_leader:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                    detail="프라이빗 라운딩은 참가자/생성자/클럽 리더·매니저만 조회할 수 있습니다.")
    else:
        # 일반 라운딩: 클럽 멤버십 확인 (관리자는 제외)
        from models import Admin
        admin = db.query(Admin).filter(Admin.id == current_user.id, Admin.deleted_at.is_(None)).first()

        if not admin:
            membership = db.query(ClubMembership).filter(
                and_(ClubMembership.user_id == current_user.id, ClubMembership.club_id == meeting.club_id,
                     ClubMembership.status.in_(MEMBERSHIP_ACTIVE_STATUSES))).first()

            if not membership:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="해당 클럽의 멤버가 아닙니다.")

    # 참가자 수 조회
    participant_count = db.query(MeetingParticipant).filter(MeetingParticipant.meeting_id == meeting.id).count()

    # 생성자 정보 조회
    created_by_name = None
    if meeting.created_by:
        creator = db.query(User).filter(User.id == meeting.created_by).first()
        if creator:
            created_by_name = creator.nickname or creator.name

    meeting_dict = {**meeting.__dict__}
    meeting_dict.pop("_sa_instance_state", None)
    meeting_dict["tee_times"] = meeting.tee_times or []

    return MeetingResponse(**meeting_dict,
                           club_name=meeting.club.name,
                           participant_count=participant_count,
                           created_by_name=created_by_name)


# =============================================================================
# 라운딩 수정
# =============================================================================


@router.put("/{meeting_id}", response_model=MeetingResponse)
async def update_round(meeting_id: int,
                       meeting_data: MeetingUpdate,
                       current_user: User = Depends(get_current_user_allow_both),
                       db: Session = Depends(get_db)):
    """라운딩 수정 (매니저만 가능)"""

    # 모임 조회
    meeting = db.query(Meeting).filter(and_(Meeting.id == meeting_id,
                                            Meeting.meeting_type == MeetingType.ROUND)).first()

    if not meeting:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="라운딩을 찾을 수 없습니다.")

    # 매니저 권한 확인 (개설자 또는 리더/매니저)
    # 프라이빗 라운딩 생성자가 참가하지 않은 경우에도 수정 권한 확인
    from utils.permissions import is_meeting_organizer_or_manager
    is_creator = meeting.created_by == current_user.id
    if not is_meeting_organizer_or_manager(meeting_id, current_user.id, db) and not is_creator:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="라운딩 매니저만 수정할 수 있습니다.")

    previous_status = meeting.status

    # is_private 변경 여부 확인
    was_private = meeting.is_private
    is_private_changing = False
    if meeting_data.is_private is not None and meeting_data.is_private != meeting.is_private:
        is_private_changing = True

    # 수정 가능한 필드들만 업데이트 (Enum 컬럼에는 모델 Enum 인스턴스로 저장)
    update_data = meeting_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        if value is None:
            setattr(meeting, field, None)
            continue
        if field == "settlement_method":
            val_str = value.value if hasattr(value, "value") else value
            try:
                setattr(meeting, field, SettlementMethod(val_str))
            except (ValueError, TypeError):
                setattr(meeting, field, value)
            continue
        if field == "meeting_subtype":
            val_str = value.value if hasattr(value, "value") else value
            try:
                setattr(meeting, field, MeetingSubtype(val_str))
            except (ValueError, TypeError):
                setattr(meeting, field, value)
            continue
        if hasattr(value, "value"):
            value = value.value
        setattr(meeting, field, value)

    meeting.updated_at = get_kst_now()

    db.commit()
    db.refresh(meeting)

    try:
        notify_round_participants_status_changed(
            db=db,
            meeting_id=meeting_id,
            previous_status=previous_status,
            current_status=meeting.status,
        )
    except Exception as e:
        logger.error(f"라운딩 상태 변경 알림 전송 실패 - meeting_id: {meeting_id}, error: {str(e)}")

    # 프라이빗 → 공개 변경 시: 기존 참가자 유지, 클럽 전체 알림 전송하지 않음
    # 공개 → 프라이빗 변경 시: 기존 참가자 유지, 일반 멤버에게는 숨김 처리
    # (별도 처리 불필요, 필터링 로직에서 자동 처리됨)

    # 클럽 정보 조회
    club = db.query(Club).filter(Club.id == meeting.club_id).first()

    # 참가자 수 조회
    participant_count = db.query(MeetingParticipant).filter(MeetingParticipant.meeting_id == meeting.id).count()

    # 생성자 정보 조회
    created_by_name = None
    if meeting.created_by:
        creator = db.query(User).filter(User.id == meeting.created_by).first()
        if creator:
            created_by_name = creator.nickname or creator.name

    meeting_dict = {**meeting.__dict__}
    meeting_dict.pop("_sa_instance_state", None)
    meeting_dict["tee_times"] = meeting.tee_times or []

    return MeetingResponse(**meeting_dict,
                           club_name=club.name,
                           participant_count=participant_count,
                           created_by_name=created_by_name)


# =============================================================================
# 라운딩 삭제
# =============================================================================


@router.delete("/{meeting_id}")
async def delete_round(meeting_id: int,
                       current_user: User = Depends(get_current_user_allow_both),
                       db: Session = Depends(get_db)):
    """라운딩 삭제 (매니저만 가능)"""

    # 모임 조회
    meeting = db.query(Meeting).filter(and_(Meeting.id == meeting_id,
                                            Meeting.meeting_type == MeetingType.ROUND)).first()

    if not meeting:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="라운딩을 찾을 수 없습니다.")

    # 매니저 권한 확인 (개설자 또는 리더/매니저)
    # 프라이빗 라운딩 생성자가 참가하지 않은 경우에도 삭제 권한 확인
    from utils.permissions import is_meeting_organizer_or_manager
    is_creator = meeting.created_by == current_user.id
    if not is_meeting_organizer_or_manager(meeting_id, current_user.id, db) and not is_creator:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="라운딩 매니저만 삭제할 수 있습니다.")

    db.delete(meeting)
    db.commit()

    return {"message": "라운딩이 삭제되었습니다."}


# =============================================================================
# 라운딩 참가/탈퇴
# =============================================================================


@router.post("/{meeting_id}/join")
async def join_round(meeting_id: int,
                     current_user: User = Depends(get_current_user_allow_both),
                     db: Session = Depends(get_db)):
    """라운딩 참가"""

    # 모임 조회
    meeting = db.query(Meeting).filter(and_(Meeting.id == meeting_id,
                                            Meeting.meeting_type == MeetingType.ROUND)).first()

    if not meeting:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="라운딩을 찾을 수 없습니다.")

    # 클럽 멤버십 확인
    membership = db.query(ClubMembership).filter(
        and_(ClubMembership.user_id == current_user.id, ClubMembership.club_id == meeting.club_id,
             ClubMembership.status.in_(MEMBERSHIP_ACTIVE_STATUSES))).first()

    if not membership:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="해당 클럽의 멤버가 아닙니다.")

    # 이미 참가했는지 확인
    existing_participant = db.query(MeetingParticipant).filter(
        and_(MeetingParticipant.meeting_id == meeting_id, MeetingParticipant.user_id == current_user.id)).first()

    if existing_participant:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="이미 참가한 라운딩입니다.")

    # 최대 참가자 수 확인
    current_participants = db.query(MeetingParticipant).filter(MeetingParticipant.meeting_id == meeting_id).count()

    if current_participants >= meeting.max_participants:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="라운딩 정원이 가득 찼습니다.")

    # 참가자 추가
    participant = MeetingParticipant(meeting_id=meeting_id,
                                     user_id=current_user.id,
                                     participant_type=ParticipantType.USER)

    db.add(participant)
    db.commit()

    try:
        notify_organizer_participant_added_after_recruitment_closed(
            db=db,
            meeting_id=meeting_id,
            participant_user_id=current_user.id,
        )
    except Exception as e:
        logger.error(
            f"모집 완료 단계 organizer 알림 전송 실패 - meeting_id: {meeting_id}, user_id: {current_user.id}, error: {str(e)}")

    return {"message": "라운딩에 참가했습니다."}


@router.delete("/{meeting_id}/leave")
async def leave_round(meeting_id: int,
                      current_user: User = Depends(get_current_user_allow_both),
                      db: Session = Depends(get_db)):
    """라운딩 탈퇴"""

    # 참가자 조회
    participant = db.query(MeetingParticipant).filter(
        and_(MeetingParticipant.meeting_id == meeting_id, MeetingParticipant.user_id == current_user.id)).first()

    if not participant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="참가하지 않은 라운딩입니다.")

    # 생성자는 탈퇴 불가
    meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
    if meeting and meeting.created_by == current_user.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="라운딩 생성자는 탈퇴할 수 없습니다.")

    db.delete(participant)
    db.commit()

    return {"message": "라운딩에서 탈퇴했습니다."}


# =============================================================================
# 참가자 관리 API
# =============================================================================


@router.get("/{meeting_id}/participants")
async def get_round_participants(meeting_id: int,
                                 current_user: User = Depends(get_current_active_user),
                                 credentials: HTTPAuthorizationCredentials = Depends(security),
                                 request: Request = None,
                                 db: Session = Depends(get_db)):
    """라운딩 참가자 목록 조회"""
    try:
        # 모임 존재 확인
        meeting = db.query(Meeting).filter(and_(Meeting.id == meeting_id,
                                                Meeting.meeting_type == MeetingType.ROUND)).first()

        if not meeting:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="라운딩을 찾을 수 없습니다.")

        # 프라이빗 라운딩인 경우 권한 체크
        user_role = get_user_role_from_token(credentials, request)
        if meeting.is_private:
            # 관리자는 접근 가능
            if user_role != "ADMIN":
                # 참가자 또는 생성자인지 확인
                is_participant = db.query(MeetingParticipant).filter(
                    and_(MeetingParticipant.meeting_id == meeting.id,
                         MeetingParticipant.user_id == current_user.id)).first()

                is_creator = meeting.created_by == current_user.id
                is_manager_or_leader = db.query(ClubMembership).filter(
                    and_(
                        ClubMembership.user_id == current_user.id,
                        ClubMembership.club_id == meeting.club_id,
                        ClubMembership.status.in_(MEMBERSHIP_ACTIVE_STATUSES),
                        ClubMembership.role.in_([ClubRole.LEADER, ClubRole.MANAGER]),
                    )
                ).first()

                if not is_participant and not is_creator and not is_manager_or_leader:
                    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                        detail="프라이빗 라운딩의 참가자 목록은 참가자/생성자/클럽 리더·매니저만 조회할 수 있습니다.")
        else:
            # 일반 라운딩: 클럽 멤버십 확인 (관리자는 제외)
            if user_role != "ADMIN":
                membership = db.query(ClubMembership).filter(
                    and_(ClubMembership.user_id == current_user.id, ClubMembership.club_id == meeting.club_id,
                         ClubMembership.status.in_(MEMBERSHIP_ACTIVE_STATUSES))).first()

                if not membership:
                    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="해당 클럽의 멤버가 아닙니다.")

        # 참가자 목록 조회 (게스트와 일반 사용자 모두 포함)
        participants = db.query(MeetingParticipant).filter(MeetingParticipant.meeting_id == meeting_id).all()

        participant_responses = []
        for participant in participants:
            # 클라이언트 권한 판단용: role, club_role, status
            role = "ORGANIZER" if participant.user_id and participant.user_id == meeting.created_by else "PARTICIPANT"
            club_role = None
            if participant.user_id:
                membership = db.query(ClubMembership).filter(
                    and_(ClubMembership.user_id == participant.user_id, ClubMembership.club_id == meeting.club_id,
                         ClubMembership.status.in_(MEMBERSHIP_ACTIVE_STATUSES))).first()
                if membership and membership.role:
                    club_role = membership.role.value if hasattr(membership.role, 'value') else str(membership.role)
            participant_status = "CONFIRMED"  # 라운딩 참가자는 기본 확정 (로컬명으로 FastAPI status 가리지 않음)
            # 게스트인 경우와 일반 참가자인 경우 구분
            if participant.guest_id:
                # 게스트인 경우 - guest_id를 통해 Guest 모델에서 정보 조회
                guest = db.query(Guest).filter(Guest.id == participant.guest_id).first()

                guest_name = guest.name if guest else "게스트"
                guest_handicap = guest.handicap if guest else None
                guest_gender = guest.gender if guest else None
                guest_birthdate = guest.birthdate if guest else None

                participant_responses.append({
                    "id":
                    participant.id,
                    "user_id":
                    participant.user_id,
                    "user_email":
                    None,
                    "guest_id":
                    participant.guest_id,
                    "user_name":
                    guest_name,
                    "user_nickname":
                    guest_name,
                    "name":
                    guest_name,
                    "handicap":
                    float(guest_handicap) if guest_handicap else None,
                    "average_score":
                    None,
                    "pace_preference":
                    participant.pace_preference,
                    "tee_preference":
                    participant.tee_preference,
                    "is_newbie":
                    participant.is_newbie,
                    "prefer_with":
                    participant.prefer_with or [],
                    "avoid_with":
                    participant.avoid_with or [],
                    "is_guest":
                    True,
                    "guest_name":
                    guest_name,
                    "guest_gender":
                    guest_gender.value if guest_gender and hasattr(guest_gender, 'value') else
                    (str(guest_gender) if guest_gender else None),
                    "guest_handicap":
                    float(guest_handicap) if guest_handicap else None,
                    "guest_birthdate":
                    guest_birthdate.isoformat() if guest_birthdate else None,
                    "gender":
                    guest_gender.value if guest_gender and hasattr(guest_gender, 'value') else
                    (str(guest_gender) if guest_gender else None),
                    "created_at":
                    participant.created_at.isoformat() if participant.created_at else None,
                    "role":
                    "PARTICIPANT",
                    "club_role":
                    None,
                    "membership_role":
                    None,
                    "status":
                    "CONFIRMED",
                })
            else:
                # 일반 참가자인 경우 - user_id를 통해 User 모델에서 정보 조회
                if participant.user_id:
                    user = db.query(User).filter(User.id == participant.user_id).first()
                    if not user:
                        continue

                    participant_responses.append({
                        "id":
                        participant.id,
                        "user_id":
                        participant.user_id,
                        "user_email":
                        user.email,
                        "guest_id":
                        None,
                        "user_name":
                        user.realname or "이름 없음",
                        "user_nickname":
                        user.nickname or "닉네임 없음",
                        "name":
                        user.realname or "이름 없음",
                        "handicap":
                        user.handicap if user.handicap is not None else user.handicap_init,
                        "average_score":
                        user.average_score if user.average_score is not None else user.average_score,
                        "pace_preference":
                        participant.pace_preference,
                        "tee_preference":
                        participant.tee_preference,
                        "is_newbie":
                        participant.is_newbie,
                        "prefer_with":
                        participant.prefer_with or [],
                        "avoid_with":
                        participant.avoid_with or [],
                        "is_guest":
                        False,
                        "gender":
                        user.gender.value if user.gender and hasattr(user.gender, 'value') else
                        (str(user.gender) if user.gender else None),
                        "created_at":
                        participant.created_at.isoformat() if participant.created_at else None,
                        "role":
                        role,
                        "club_role":
                        club_role,
                        "membership_role":
                        club_role,
                        "status":
                        participant_status,
                    })

        return participant_responses

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="서버 내부 오류가 발생했습니다.")


@router.get("/{meeting_id}/teams", response_model=List[TeamResponse])
async def get_round_teams(meeting_id: int,
                          current_user: User = Depends(get_current_user_allow_both),
                          credentials: HTTPAuthorizationCredentials = Depends(security),
                          request: Request = None,
                          db: Session = Depends(get_db)):
    """라운딩의 팀 목록 조회"""
    try:
        # 모임 존재 확인
        meeting = db.query(Meeting).filter(and_(Meeting.id == meeting_id,
                                                Meeting.meeting_type == MeetingType.ROUND)).first()

        if not meeting:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="라운딩을 찾을 수 없습니다.")

        # 클럽 멤버십 확인 (관리자는 제외)
        user_role = get_user_role_from_token(credentials, request)
        if user_role != "ADMIN":
            membership = db.query(ClubMembership).filter(
                and_(ClubMembership.user_id == current_user.id, ClubMembership.club_id == meeting.club_id,
                     ClubMembership.status.in_(MEMBERSHIP_ACTIVE_STATUSES))).first()

            if not membership:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="해당 클럽의 멤버가 아닙니다.")

        # 팀 목록 조회
        teams = db.query(Team).filter(Team.meeting_id == meeting_id).all()

        team_responses = []
        for team in teams:
            members = []
            team_members = db.query(TeamMember).filter(TeamMember.team_id == team.id).all()

            for team_member in team_members:
                # user_id 또는 guest_id를 통해 MeetingParticipant 조회
                if team_member.user_id:
                    participant = db.query(MeetingParticipant).filter(
                        MeetingParticipant.meeting_id == meeting_id,
                        MeetingParticipant.user_id == team_member.user_id).first()
                elif team_member.guest_id:
                    participant = db.query(MeetingParticipant).filter(
                        MeetingParticipant.meeting_id == meeting_id,
                        MeetingParticipant.guest_id == team_member.guest_id).first()
                else:
                    participant = None

                if participant:
                    # 게스트인 경우와 멤버인 경우 구분 (MeetingParticipant에는 is_guest 없음, guest_id로 판별)
                    gender = None
                    handicap = None
                    average_score = None

                    if participant.guest_id:
                        # guest_id를 통해 Guest 모델에서 정보 조회
                        if participant.guest_id:
                            guest = db.query(Guest).filter(Guest.id == participant.guest_id).first()
                            if guest:
                                user_name = guest.name or "게스트"
                                user_nickname = guest.name or "게스트"
                                gender = guest.gender.value if guest.gender else None
                                handicap = int(guest.handicap) if guest.handicap else None
                            else:
                                # 하위 호환성: guest 필드 사용
                                user_name = participant.guest_name or "게스트"
                                user_nickname = participant.guest_name or "게스트"
                                gender = participant.guest_gender.value if participant.guest_gender else None
                                handicap = int(participant.guest_handicap) if participant.guest_handicap else None
                        else:
                            # 하위 호환성: guest 필드 사용
                            user_name = participant.guest_name or "게스트"
                            user_nickname = participant.guest_name or "게스트"
                            gender = participant.guest_gender.value if participant.guest_gender else None
                            handicap = int(participant.guest_handicap) if participant.guest_handicap else None
                    else:
                        if participant.user_id:
                            user = db.query(User).filter(User.id == participant.user_id).first()
                            if user:
                                user_name = user.realname or user.nickname or "이름 없음"
                                user_nickname = user.nickname or "닉네임 없음"
                                gender = user.gender.value if user.gender else None

                                # 핸디캡 우선순위: participant.handicap → user.handicap → user.handicap_init → user.average_score(공통 계산 유틸)
                                if participant.handicap is not None:
                                    handicap = participant.handicap
                                elif user.handicap is not None:
                                    handicap = int(user.handicap)
                                elif user.handicap is not None:
                                    handicap = int(user.handicap)
                                elif user.handicap_init is not None:
                                    handicap = int(user.handicap_init)
                                elif user.average_score is not None:
                                    handicap = calculate_handicap_from_average_score(user.average_score)
                                else:
                                    handicap = None

                                # MeetingResult에서 실제 직전 대회 성적 조회
                                average_score = None
                                last_result = db.query(MeetingResult).filter(
                                    MeetingResult.user_id == participant.user_id,
                                    MeetingResult.meeting_id != meeting.id  # 현재 모임 제외
                                ).order_by(MeetingResult.completed_at.desc()).first()

                                if last_result:
                                    average_score = last_result.gross_score

                                # 디버깅: 핸디캡과 직전대회성적 확인
                                logger.debug(f"팀 멤버 정보 - user_id: {participant.user_id}, name: {user_name}, "
                                             f"handicap: {handicap}, average_score: {average_score}")
                            else:
                                continue
                        else:
                            continue

                    member_response = TeamMemberResponse(
                        id=team_member.id,
                        team_id=team_member.team_id,
                        user_id=team_member.user_id,
                        user_name=user_name,
                        user_nickname=user_nickname,
                        order=team_member.order,
                        gender=gender,
                        handicap=handicap,
                        average_score=average_score,
                        is_guest=(participant.guest_id is not None) if participant else None,
                        created_at=team_member.created_at)
                    members.append(member_response)

            team_response = TeamResponse(
                id=team.id,
                name=team.name,
                meeting_id=team.meeting_id,
                meeting_name=meeting.name,
                formation_mode=TeamFormationMode(team.formation_mode) if team.formation_mode else None,
                status=TeamStatus(team.status) if team.status else TeamStatus.DRAFT,
                total_handicap=float(team.total_handicap) if team.total_handicap else None,
                tee_off_order=team.tee_off_order,
                formation_notes=team.formation_notes,
                member_count=len(members),
                members=members,
                created_at=team.created_at,
                updated_at=team.updated_at)
            team_responses.append(team_response)

        return team_responses

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"팀 목록 조회 오류: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="서버 내부 오류가 발생했습니다.")


# =============================================================================
# 팀 멤버 관리 API
# =============================================================================


@router.post("/{meeting_id}/teams/{team_id}/members", response_model=TeamMemberResponse)
async def add_team_member(
    meeting_id: int,
    team_id: int,
    member_data: dict,  # { user_id: int }
    current_user: User = Depends(get_current_user_allow_both),
    db: Session = Depends(get_db)):
    """팀 멤버 추가"""
    try:
        # 모임 존재 확인
        meeting = db.query(Meeting).filter(and_(Meeting.id == meeting_id,
                                                Meeting.meeting_type == MeetingType.ROUND)).first()

        if not meeting:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="라운딩을 찾을 수 없습니다.")

        # 팀 존재 확인
        team = db.query(Team).filter(and_(Team.id == team_id, Team.meeting_id == meeting_id)).first()

        if not team:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="팀을 찾을 수 없습니다.")

        # user_id 또는 guest_id 추출
        user_id = member_data.get("user_id")
        guest_id = member_data.get("guest_id")

        if not user_id and not guest_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="user_id 또는 guest_id가 필요합니다.")

        # 참가자 확인 (MeetingParticipant에 존재하는지)
        if user_id:
            participant = db.query(MeetingParticipant).filter(
                and_(MeetingParticipant.meeting_id == meeting_id, MeetingParticipant.user_id == user_id)).first()
        elif guest_id:
            participant = db.query(MeetingParticipant).filter(
                and_(MeetingParticipant.meeting_id == meeting_id, MeetingParticipant.guest_id == guest_id)).first()
        else:
            participant = None

        if not participant:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="해당 사용자는 이 라운딩의 참가자가 아닙니다.")

        # 이미 팀 멤버인지 확인
        if user_id:
            existing_member = db.query(TeamMember).filter(
                and_(TeamMember.team_id == team_id, TeamMember.user_id == user_id)).first()
        elif guest_id:
            existing_member = db.query(TeamMember).filter(
                and_(TeamMember.team_id == team_id, TeamMember.guest_id == guest_id)).first()
        else:
            existing_member = None

        if existing_member:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="이미 해당 팀의 멤버입니다.")

        # 기존 멤버 수 확인하여 order 설정
        existing_members_count = db.query(TeamMember).filter(TeamMember.team_id == team_id).count()

        # 팀 멤버 생성
        team_member = TeamMember(team_id=team_id, user_id=user_id, guest_id=guest_id, order=existing_members_count + 1)

        db.add(team_member)
        db.commit()
        db.refresh(team_member)

        # 사용자 정보 조회 (게스트인 경우와 일반 사용자인 경우 구분)
        user_name = None
        user_nickname = None
        gender = None
        handicap = None
        average_score = None

        if participant.guest_id:
            # guest_id를 통해 Guest 모델에서 정보 조회
            if participant.guest_id:
                guest = db.query(Guest).filter(Guest.id == participant.guest_id).first()
                if guest:
                    user_name = guest.name or "게스트"
                    user_nickname = guest.name or "게스트"
                    gender = guest.gender.value if guest.gender else None
                    handicap = int(guest.handicap) if guest.handicap else None
                else:
                    # 하위 호환성: guest 필드 사용
                    user_name = participant.guest_name or "게스트"
                    user_nickname = participant.guest_name or "게스트"
                    gender = participant.guest_gender.value if participant.guest_gender else None
                    handicap = int(participant.guest_handicap) if participant.guest_handicap else None
            else:
                # 하위 호환성: guest 필드 사용
                user_name = participant.guest_name or "게스트"
                user_nickname = participant.guest_name or "게스트"
                gender = participant.guest_gender.value if participant.guest_gender else None
                handicap = int(participant.guest_handicap) if participant.guest_handicap else None
        else:
            if participant.user_id:
                user = db.query(User).filter(User.id == participant.user_id).first()
                if user:
                    user_name = user.realname or user.nickname or "이름 없음"
                    user_nickname = user.nickname or "닉네임 없음"
                    gender = user.gender.value if user.gender else None

                    # 핸디캡 우선순위: participant.handicap → user.handicap → user.handicap_init → user.average_score(공통 계산 유틸)
                    if participant.handicap is not None:
                        handicap = participant.handicap
                    elif user.handicap is not None:
                        handicap = int(user.handicap)
                    elif user.handicap is not None:
                        handicap = int(user.handicap)
                    elif user.handicap_init is not None:
                        handicap = int(user.handicap_init)
                    elif user.average_score is not None:
                        handicap = calculate_handicap_from_average_score(user.average_score)

                    # MeetingResult에서 실제 직전 대회 성적 조회
                    last_result = db.query(MeetingResult).filter(
                        MeetingResult.user_id == participant.user_id,
                        MeetingResult.meeting_id != meeting_id  # 현재 모임 제외
                    ).order_by(MeetingResult.completed_at.desc()).first()

                    if last_result:
                        average_score = last_result.gross_score
                else:
                    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="사용자 정보를 찾을 수 없습니다.")
            else:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="참가자 정보가 올바르지 않습니다.")

        return TeamMemberResponse(id=team_member.id,
                                  team_id=team_member.team_id,
                                  user_id=team_member.user_id,
                                  user_name=user_name or "이름 없음",
                                  user_nickname=user_nickname or "닉네임 없음",
                                  order=team_member.order,
                                  gender=gender,
                                  handicap=handicap,
                                  average_score=average_score,
                                  created_at=team_member.created_at)

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"팀 멤버 추가 오류: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"서버 내부 오류가 발생했습니다: {str(e)}")


@router.delete("/{meeting_id}/teams/{team_id}/members/{member_id}")
async def remove_team_member(meeting_id: int,
                             team_id: int,
                             member_id: int,
                             current_user: User = Depends(get_current_active_user),
                             db: Session = Depends(get_db)):
    """팀 멤버 제거"""
    try:
        # 모임 존재 확인
        meeting = db.query(Meeting).filter(and_(Meeting.id == meeting_id,
                                                Meeting.meeting_type == MeetingType.ROUND)).first()

        if not meeting:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="라운딩을 찾을 수 없습니다.")

        # 팀 존재 확인
        team = db.query(Team).filter(and_(Team.id == team_id, Team.meeting_id == meeting_id)).first()

        if not team:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="팀을 찾을 수 없습니다.")

        # 팀 멤버 존재 확인
        team_member = db.query(TeamMember).filter(and_(TeamMember.id == member_id,
                                                       TeamMember.team_id == team_id)).first()

        if not team_member:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="팀 멤버를 찾을 수 없습니다.")

        # 팀 멤버 삭제
        db.delete(team_member)
        db.commit()

        return {"message": "팀 멤버가 제거되었습니다."}

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"팀 멤버 제거 오류: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"서버 내부 오류가 발생했습니다: {str(e)}")
