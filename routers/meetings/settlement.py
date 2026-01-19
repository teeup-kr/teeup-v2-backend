"""
모임 정산 관리 API
- 라운딩/소셜 모임 정산
- 비용 항목 관리
- 정산 대상자 관리
"""

from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, and_, or_
from typing import List, Optional
from datetime import datetime
from decimal import Decimal
import logging

from database import get_db
from models import (
    User, Club, ClubMembership, Meeting, MeetingParticipant, 
    Team, TeamMember, Expense, ExpenseParticipant, Guest
)
from schemas import (
    MeetingType, MeetingSubtype, SettlementMethod, SocialSettlementMethod,
    MeetingStatus, MeetingParticipantStatus, MeetingParticipantRole,
    ClubRole
)
from schemas import (
    RoundingMeetingCreate, SocialMeetingCreate, MeetingUpdate, 
    MeetingResponse, MeetingParticipantResponse, PaginatedResponse
)
from routers.auth import get_current_active_user
from routers.auth import get_current_user_or_admin
from utils.permissions import MEMBERSHIP_ACTIVE_STATUSES
from models import Notification
from schemas import NotificationType, NotificationStatus
from utils.cuid import generate_cuid

router = APIRouter(prefix="/meetings", tags=["meeting-settlement"])
logger = logging.getLogger(__name__)

# =============================================================================
# 권한 체크 유틸리티 함수
# =============================================================================

def send_settlement_created_notification(meeting_id: int, db: Session, is_edit: bool = False):
    """정산 생성/수정 완료 시 참가자들에게 알림 전송"""
    try:
        # 모임 정보 조회
        meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
        if not meeting:
            logger.error(f"모임을 찾을 수 없습니다: {meeting_id}")
            return
        
        # 클럽 정보 조회
        club = db.query(Club).filter(Club.id == meeting.club_id).first()
        club_name = club.name if club else "알 수 없는 클럽"
        
        # 참가자들 조회 (CONFIRMED 상태)
        participants = db.query(MeetingParticipant).filter(
            MeetingParticipant.meeting_id == meeting_id,
            MeetingParticipant.status == MeetingParticipantStatus.CONFIRMED
        ).all()
        
        if not participants:
            logger.info(f"알림을 받을 참가자가 없습니다: {meeting_id}")
            return
        
        # 알림 메시지 생성
        action = "수정" if is_edit else "생성"
        title = f"정산 {action} 완료 - {meeting.name}"
        content = f"""
{club_name}의 모임 '{meeting.name}' 정산이 {action}되었습니다.

📅 모임 일시: {meeting.meeting_time.strftime('%Y년 %m월 %d일 %H:%M') if meeting.meeting_time else '미정'}
📍 장소: {meeting.location or meeting.venue_name or '미정'}

정산 내역을 확인해보세요!
        """.strip()
        
        # 각 참가자에게 알림 전송 (게스트는 알림을 받을 수 없으므로 제외)
        sent_count = 0
        for participant in participants:
            # 게스트는 알림을 받을 수 없음
            if participant.guest_id or not participant.user_id:
                continue
                
            try:
                notification = Notification(
                    user_id=participant.user_id,
                    type=NotificationType.MEETING_SETTLEMENT_COMPLETED.value,
                    title=title,
                    content=content,
                    status=NotificationStatus.UNREAD.value
                )
                
                db.add(notification)
                sent_count += 1
                
            except Exception as e:
                logger.error(f"정산 {action} 알림 생성 실패 - user_id: {participant.user_id}, error: {str(e)}")
                continue
        
        db.commit()
        logger.info(f"정산 {action} 알림 전송 완료 - meeting_id: {meeting_id}, sent_count: {sent_count}")
        
    except Exception as e:
        logger.error(f"정산 {action} 알림 전송 오류: {str(e)}")
        db.rollback()

def can_manage_settlement(meeting_id: int, user_id: int, db: Session) -> bool:
    """
    정산 관리 권한 체크
    
    권한이 있는 경우:
    1. 주최자: 참가자 목록에서 ORGANIZER 역할을 가진 사용자 (참가 여부와 무관)
    2. 참가자이면서 클럽 리더/매니저: isParticipant && club_role ∈ {LEADER, MANAGER}
    
    Args:
        meeting_id: 모임 ID
        user_id: 사용자 ID
        db: 데이터베이스 세션
    
    Returns:
        bool: 정산 관리 권한이 있으면 True
    """
    try:
        # 모임 조회
        meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
        if not meeting:
            return False
        
        # 1. 주최자 확인: 참가자 목록에서 ORGANIZER 역할 확인
        organizer = db.query(MeetingParticipant).filter(
            MeetingParticipant.meeting_id == meeting_id,
            MeetingParticipant.user_id == user_id,
            MeetingParticipant.role == MeetingParticipantRole.ORGANIZER,
            MeetingParticipant.status == MeetingParticipantStatus.CONFIRMED
        ).first()
        
        is_organizer = organizer is not None
        if is_organizer:
            return True
        
        # 2. 참가자 여부 확인
        participant = db.query(MeetingParticipant).filter(
            MeetingParticipant.meeting_id == meeting_id,
            MeetingParticipant.user_id == user_id,
            MeetingParticipant.status == MeetingParticipantStatus.CONFIRMED
        ).first()
        
        is_participant = participant is not None
        if not is_participant:
            return False
        
        # 3. 클럽 리더/매니저 권한 확인
        from .clubs import get_user_club_role
        club_role = get_user_club_role(meeting.club_id, user_id, db)
        is_club_leader_or_manager = club_role in ['LEADER', 'MANAGER']
        
        # 4. 최종 권한 확인: 참가자이면서 클럽 리더/매니저
        return is_participant and is_club_leader_or_manager
        
    except Exception as e:
        logger.error(f"정산 권한 체크 중 오류: {str(e)}")
        return False

# =============================================================================
# 라운딩 정산 API
# =============================================================================

@router.post("/{meeting_id}/settlement/rounding")
async def create_rounding_settlement(
    meeting_id: int,
    settlement_data: dict = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """라운딩 정산 생성 (매니저/리더만 가능)"""
    try:
        # 모임 존재 확인
        meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
        if not meeting:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="모임을 찾을 수 없습니다."
            )
        
        if meeting.meeting_type != MeetingType.ROUND:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="라운딩 모임이 아닙니다."
            )
        
        # 정산이 이미 확정된 경우 생성/수정 불가
        if meeting.settlement_confirmed:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="정산이 이미 확정되어 수정할 수 없습니다."
            )
        
        # 정산 권한 확인: 주최자 또는 참가자이면서 클럽 리더/매니저
        if not can_manage_settlement(meeting_id, current_user.id, db):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="모임 개설자 또는 참가자인 클럽 리더/매니저만 정산을 생성할 수 있습니다."
            )
        
        # 기존 정산 삭제 (수정인지 확인)
        existing_expenses = db.query(Expense).filter(Expense.meeting_id == meeting_id).all()
        is_edit = len(existing_expenses) > 0
        for expense in existing_expenses:
            # 기존 정산의 expense_participants도 함께 삭제
            existing_participants = db.query(ExpenseParticipant).filter(
                ExpenseParticipant.expense_id == expense.id
            ).all()
            for participant in existing_participants:
                db.delete(participant)
            db.delete(expense)
        
        # 정산 데이터 추출
        total_cost = Decimal(str(settlement_data.get('total_cost', 0)))
        green_fee = Decimal(str(settlement_data.get('green_fee', 0)))
        caddy_fee = Decimal(str(settlement_data.get('caddy_fee', 0)))
        cart_fee = Decimal(str(settlement_data.get('cart_fee', 0)))
        other_fee = Decimal(str(settlement_data.get('other_fee', 0)))
        notes = settlement_data.get('notes', '')
        
        # 필드별 정산 대상자 추출
        total_cost_participants = settlement_data.get('total_cost_participants', [])
        total_cost_exempted = settlement_data.get('total_cost_exempted', [])
        green_fee_participants = settlement_data.get('green_fee_participants', [])
        green_fee_exempted = settlement_data.get('green_fee_exempted', [])
        cart_fee_participants = settlement_data.get('cart_fee_participants', [])
        cart_fee_exempted = settlement_data.get('cart_fee_exempted', [])
        caddy_fee_participants = settlement_data.get('caddy_fee_participants', [])
        caddy_fee_exempted = settlement_data.get('caddy_fee_exempted', [])
        other_expense_items = settlement_data.get('other_expense_items', [])
        exempted_participants = settlement_data.get('exempted_participants', [])
        exclude_remaining_amount = settlement_data.get('exclude_remaining_amount', False)
        
        # 회비 처리 필드 추출 (검증 전에)
        all_covered_by_fee = settlement_data.get('all_covered_by_fee', False)
        green_fee_covered_by_fee = settlement_data.get('green_fee_covered_by_fee', False)
        caddy_fee_covered_by_fee = settlement_data.get('caddy_fee_covered_by_fee', False)
        cart_fee_covered_by_fee = settlement_data.get('cart_fee_covered_by_fee', False)
        
        # 전체 정산 대상자 수집 (중복 제거, 회비 처리된 항목 제외)
        all_settlement_targets = set()
        # 그린피: 모두 회비 처리 또는 그린피 회비 처리가 아닌 경우만 수집
        if not all_covered_by_fee and not green_fee_covered_by_fee:
            all_settlement_targets.update(green_fee_participants)
        # 카트비: 모두 회비 처리 또는 카트비 회비 처리가 아닌 경우만 수집
        if not all_covered_by_fee and not cart_fee_covered_by_fee:
            all_settlement_targets.update(cart_fee_participants)
        # 캐디피: 모두 회비 처리 또는 캐디피 회비 처리가 아닌 경우만 수집
        if not all_covered_by_fee and not caddy_fee_covered_by_fee:
            all_settlement_targets.update(caddy_fee_participants)
        # 기타 비용: 모두 회비 처리가 아닌 경우만 수집
        if not all_covered_by_fee:
            for item in other_expense_items:
                item_participants = item.get('participants', [])
                if isinstance(item_participants, list):
                    for participant_id in item_participants:
                        if participant_id and participant_id != 'UNSETTLED':
                            all_settlement_targets.add(participant_id)
        
        settlement_targets = list(all_settlement_targets)
        
        # 정산 대상자 수 계산
        target_count = len(settlement_targets)
        # 모두 회비에서 처리되면 정산 대상자가 0명이어도 괜찮음
        if target_count == 0 and not exclude_remaining_amount and not all_covered_by_fee:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="정산 대상자를 선택해주세요."
            )
        
        # 필수 필드별 정산 대상자 확인 (회비 처리되지 않은 경우만)
        if not all_covered_by_fee and not green_fee_covered_by_fee and len(green_fee_participants) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="그린피의 정산 대상자를 선택해주세요."
            )
        if not all_covered_by_fee and not cart_fee_covered_by_fee and len(cart_fee_participants) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="카트비의 정산 대상자를 선택해주세요."
            )
        if not all_covered_by_fee and not caddy_fee_covered_by_fee and len(caddy_fee_participants) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="캐디피의 정산 대상자를 선택해주세요."
            )
        
        # 기타 비용 항목 검증 (모두 회비에서 처리되지 않은 경우만)
        if not all_covered_by_fee:
            for idx, item in enumerate(other_expense_items):
                item_participants = item.get('participants', [])
                if not item_participants or len(item_participants) == 0:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"기타 비용 항목 {idx + 1}의 정산 대상자를 선택해주세요."
                    )
        
        # 1인당 비용 계산 (모두 회비에서 처리되면 0원)
        amount_per_person = Decimal('0') if all_covered_by_fee else (total_cost / target_count if target_count > 0 else Decimal('0'))
        
        # 정산 생성
        expense = Expense(            title=f"{meeting.name} 라운딩 정산",
            description=f"그린피: {green_fee:,}원, 캐디피: {caddy_fee:,}원, 카트비: {cart_fee:,}원, 기타: {other_fee:,}원",
            amount=total_cost,
            green_fee=green_fee,
            caddy_fee=caddy_fee,
            cart_fee=cart_fee,
            other_fee=other_fee,
            total_participants=target_count,
            amount_per_person=amount_per_person,
            meeting_id=meeting_id,
            club_id=meeting.club_id,
            created_by=current_user.id,
            notes=notes,
            # 필드별 participants와 기타 비용 항목 저장
            total_cost_participants=total_cost_participants,
            total_cost_exempted=total_cost_exempted if total_cost_exempted else [],
            green_fee_participants=green_fee_participants,
            green_fee_exempted=green_fee_exempted if green_fee_exempted else [],
            cart_fee_participants=cart_fee_participants,
            cart_fee_exempted=cart_fee_exempted if cart_fee_exempted else [],
            caddy_fee_participants=caddy_fee_participants,
            caddy_fee_exempted=caddy_fee_exempted if caddy_fee_exempted else [],
            other_expense_items=other_expense_items if other_expense_items else [],
            exempted_participants=exempted_participants if exempted_participants else [],
            exclude_remaining_amount=exclude_remaining_amount,
            # 회비 처리 필드
            all_covered_by_fee=all_covered_by_fee,
            green_fee_covered_by_fee=green_fee_covered_by_fee,
            caddy_fee_covered_by_fee=caddy_fee_covered_by_fee,
            cart_fee_covered_by_fee=cart_fee_covered_by_fee
        )
        
        db.add(expense)
        db.flush()  # ID 생성
        
        # 정산 대상자별 비용 정산 생성 (게스트 지원)
        logger.info(f"라운딩 정산 생성 - settlement_targets: {settlement_targets}, target_count: {target_count}")
        for target_id in settlement_targets:
            # MeetingParticipant 조회하여 user_id 또는 guest_id 설정
            meeting_participant = db.query(MeetingParticipant).filter(
                MeetingParticipant.meeting_id == meeting_id,
                or_(
                    MeetingParticipant.user_id == target_id,
                    MeetingParticipant.guest_id == target_id
                )
            ).first()
            
            if meeting_participant:
                if meeting_participant.guest_id:
                    expense_participant = ExpenseParticipant(
                        expense_id=expense.id,
                        user_id=None,
                        guest_id=meeting_participant.guest_id
                    )
                    logger.info(f"라운딩 정산 생성 - ExpenseParticipant 생성: guest_id={meeting_participant.guest_id}")
                else:
                    expense_participant = ExpenseParticipant(
                        expense_id=expense.id,
                        user_id=meeting_participant.user_id,
                        guest_id=None
                    )
                    logger.info(f"라운딩 정산 생성 - ExpenseParticipant 생성: user_id={meeting_participant.user_id}")
                db.add(expense_participant)
        
        db.commit()
        logger.info(f"라운딩 정산 생성 완료 - expense.id: {expense.id}, 생성된 ExpenseParticipant 수: {len(settlement_targets)}")
        
        # 정산 생성/수정 완료 알림 전송
        try:
            send_settlement_created_notification(meeting_id, db, is_edit=is_edit)
        except Exception as e:
            logger.error(f"정산 생성 알림 전송 실패: {str(e)}")
        
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
        logger.error(f"라운딩 정산 생성 오류: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="서버 내부 오류가 발생했습니다."
        )

# =============================================================================
# 소셜 모임 정산 API
# =============================================================================

@router.post("/{meeting_id}/settlement/social")
async def create_social_settlement(
    meeting_id: int,
    settlement_data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """소셜 모임 정산 생성 (매니저/리더만 가능)"""
    try:
        # 모임 존재 확인
        meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
        if not meeting:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="모임을 찾을 수 없습니다."
            )
        
        if meeting.meeting_type != MeetingType.SOCIAL:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="소셜 모임이 아닙니다."
            )
        
        # 정산이 이미 확정된 경우 생성/수정 불가
        if meeting.settlement_confirmed:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="정산이 이미 확정되어 수정할 수 없습니다."
            )
        
        # 정산 권한 확인: 주최자 또는 참가자이면서 클럽 리더/매니저
        if not can_manage_settlement(meeting_id, current_user.id, db):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="모임 개설자 또는 참가자인 클럽 리더/매니저만 정산을 생성할 수 있습니다."
            )
        
        # 기존 정산 삭제 (수정인지 확인)
        existing_expenses = db.query(Expense).filter(Expense.meeting_id == meeting_id).all()
        is_edit = len(existing_expenses) > 0
        for expense in existing_expenses:
            db.delete(expense)
        
        # 정산 데이터 추출
        expense_items = settlement_data.get('expense_items', [])
        settlement_targets = settlement_data.get('settlement_targets', [])
        notes = settlement_data.get('notes', '')
        exclude_remaining_amount = settlement_data.get('exclude_remaining_amount', False)
        
        # 입력 데이터 확인 로그
        logger.info(f"소셜 정산 생성 요청 데이터 - expense_items: {expense_items}, type: {type(expense_items)}, len: {len(expense_items) if isinstance(expense_items, list) else 'N/A'}")
        logger.info(f"소셜 정산 생성 요청 데이터 - settlement_targets: {settlement_targets}, exclude_remaining_amount: {exclude_remaining_amount}")
        
        # 총 비용 계산: total_cost 필드 우선 사용, 없으면 expense_items 합계
        total_cost = settlement_data.get('total_cost')
        if total_cost is None:
            total_cost = sum(Decimal(str(item.get('amount', 0))) for item in expense_items)
        else:
            total_cost = Decimal(str(total_cost))
        
        # 정산 대상자 수 계산
        target_count = len(settlement_targets)
        
        # exclude_remaining_amount가 false일 때만 settlement_targets 검증
        if not exclude_remaining_amount and target_count == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="정산 대상자를 선택해주세요."
            )
        
        # 1인당 비용 계산 (exclude_remaining_amount가 true이거나 target_count가 0이면 0)
        if exclude_remaining_amount or target_count == 0:
            amount_per_person = Decimal('0')
        else:
            amount_per_person = total_cost / target_count
        
        # 정산 생성
        logger.info(f"소셜 정산 생성 - expense_items: {expense_items}, exclude_remaining_amount: {exclude_remaining_amount}")
        expense = Expense(
            title=f"{meeting.name} 소셜 모임 정산",
            description=f"총 {len(expense_items)}개 항목",
            amount=total_cost,
            total_participants=target_count,
            amount_per_person=amount_per_person,
            meeting_id=meeting_id,
            club_id=meeting.club_id,
            created_by=current_user.id,
            notes=notes,
            expense_items=expense_items,  # 비용 항목 배열 저장
            exclude_remaining_amount=exclude_remaining_amount  # 나머지 금액 정산 제외 여부 저장
        )
        
        db.add(expense)
        db.flush()  # ID 생성
        
        # 저장된 데이터 확인
        logger.info(f"소셜 정산 저장 후 - expense.expense_items: {expense.expense_items}, expense.exclude_remaining_amount: {expense.exclude_remaining_amount}")
        
        # 정산 대상자별 비용 정산 생성 (게스트 지원)
        logger.info(f"소셜 정산 생성 - settlement_targets: {settlement_targets}, target_count: {target_count}")
        for target_id in settlement_targets:
            # MeetingParticipant 조회하여 user_id 또는 guest_id 설정
            meeting_participant = db.query(MeetingParticipant).filter(
                MeetingParticipant.meeting_id == meeting_id,
                or_(
                    MeetingParticipant.user_id == target_id,
                    MeetingParticipant.guest_id == target_id
                )
            ).first()
            
            if meeting_participant:
                if meeting_participant.guest_id:
                    expense_participant = ExpenseParticipant(
                        expense_id=expense.id,
                        user_id=None,
                        guest_id=meeting_participant.guest_id
                    )
                    logger.info(f"소셜 정산 생성 - ExpenseParticipant 생성: guest_id={meeting_participant.guest_id}")
                else:
                    expense_participant = ExpenseParticipant(
                        expense_id=expense.id,
                        user_id=meeting_participant.user_id,
                        guest_id=None
                    )
                    logger.info(f"소셜 정산 생성 - ExpenseParticipant 생성: user_id={meeting_participant.user_id}")
                db.add(expense_participant)
        
        db.commit()
        logger.info(f"소셜 정산 생성 완료 - expense.id: {expense.id}, 생성된 ExpenseParticipant 수: {len(settlement_targets)}")
        
        # commit 후 실제 저장된 데이터 확인 (DB에서 다시 조회)
        db.refresh(expense)
        logger.info(f"소셜 정산 commit 후 - expense.expense_items: {expense.expense_items}, type: {type(expense.expense_items)}, expense.exclude_remaining_amount: {expense.exclude_remaining_amount}")
        
        # 정산 생성/수정 완료 알림 전송
        try:
            send_settlement_created_notification(meeting_id, db, is_edit=is_edit)
        except Exception as e:
            logger.error(f"정산 생성 알림 전송 실패: {str(e)}")
        
        return {
            "message": "소셜 모임 정산이 생성되었습니다.",
            "settlement_id": expense.id,
            "total_cost": float(total_cost),
            "amount_per_person": float(amount_per_person),
            "target_count": target_count
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"소셜 모임 정산 생성 오류: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="서버 내부 오류가 발생했습니다."
        )

# =============================================================================
# 정산 조회 API
# =============================================================================

@router.get("/{meeting_id}/settlement")
async def get_meeting_settlement(
    meeting_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_or_admin)
):
    """모임 정산 조회"""
    try:
        # 모임 존재 확인
        meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
        if not meeting:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="모임을 찾을 수 없습니다."
            )
        
        # 관리자가 아닌 경우에만 클럽 멤버십 확인
        from models import Admin
        admin = db.query(Admin).filter(
            Admin.id == current_user.id,
            Admin.deleted_at.is_(None)
        ).first()
        
        if not admin:
            membership = db.query(ClubMembership).filter(
                ClubMembership.club_id == meeting.club_id,
                ClubMembership.user_id == current_user.id,
                ClubMembership.status.in_(MEMBERSHIP_ACTIVE_STATUSES)
            ).first()
            
            if not membership:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="클럽 멤버만 정산을 조회할 수 있습니다."
                )
        
        # 정산 조회
        expense = db.query(Expense).filter(Expense.meeting_id == meeting_id).first()
        
        if not expense:
            return {"settlement": None}
        
        # 조회된 데이터 확인
        logger.info(f"정산 조회 - expense.id: {expense.id}, expense.expense_items: {expense.expense_items}, expense.exclude_remaining_amount: {expense.exclude_remaining_amount}")
        
        # 정산 대상자 조회 (게스트 포함)
        participants = db.query(ExpenseParticipant).options(
            joinedload(ExpenseParticipant.user),
            joinedload(ExpenseParticipant.guest)
        ).filter(ExpenseParticipant.expense_id == expense.id).all()
        
        logger.info(f"정산 조회 - ExpenseParticipant 수: {len(participants)}")
        
        participant_list = []
        settlement_targets = []  # 정산 대상자 user_id 또는 guest_id 배열
        
        # ExpenseParticipant 모델에 is_settlement_target 필드가 없으므로
        # 모든 ExpenseParticipant를 정산 대상자로 간주
        for expense_participant in participants:
            if expense_participant.guest_id:
                # 게스트인 경우
                guest = expense_participant.guest
                participant_data = {
                    "id": expense_participant.id,
                    "user_id": None,
                    "guest_id": expense_participant.guest_id,
                    "user_name": guest.name if guest else "게스트",
                    "user_email": None,
                    "is_guest": True,
                    "amount_paid": float(expense_participant.amount_paid) if expense_participant.amount_paid else 0,
                    "is_paid": expense_participant.is_paid,
                    "paid_at": expense_participant.paid_at.isoformat() if expense_participant.paid_at else None,
                    "is_settlement_target": True,
                }
                settlement_targets.append(expense_participant.guest_id)
            else:
                # 일반 사용자인 경우
                user = expense_participant.user
                participant_data = {
                    "id": expense_participant.id,
                    "user_id": user.id if user else None,
                    "guest_id": None,
                    "user_name": user.nickname if user else "알 수 없음",
                    "user_email": user.email if user else None,
                    "is_guest": False,
                    "amount_paid": float(expense_participant.amount_paid) if expense_participant.amount_paid else 0,
                    "is_paid": expense_participant.is_paid,
                    "paid_at": expense_participant.paid_at.isoformat() if expense_participant.paid_at else None,
                    "is_settlement_target": True,
                }
                if user:
                    settlement_targets.append(user.id)
            
            # 존재하는 필드만 추가
            if hasattr(expense_participant, 'amount_due'):
                participant_data["amount_due"] = float(expense_participant.amount_due) if expense_participant.amount_due else 0
            if hasattr(expense_participant, 'status'):
                participant_data["status"] = expense_participant.status
            if hasattr(expense_participant, 'notes'):
                participant_data["notes"] = expense_participant.notes
            
            participant_list.append(participant_data)
        
        # 정산 대상자 수 계산: 모든 ExpenseParticipant를 정산 대상자로 간주
        total_participants_count = len(participants)
        logger.info(f"정산 조회 - total_participants_count: {total_participants_count}, settlement_targets: {len(settlement_targets)}")
        
        # 기본 정산 정보
        settlement_data = {
            "id": expense.id,            "title": expense.title,
            "description": expense.description,
            "total_cost": float(expense.amount),
            "amount_per_person": float(expense.amount_per_person),
            "total_participants": total_participants_count,  # 실제 정산 대상자 수 사용
            "notes": expense.notes,
            "created_at": expense.created_at,
            "participants": participant_list,
            "settlement_targets": settlement_targets  # 정산 대상자 user_id 배열
        }
        
        # 소셜 정산일 때 expense_items와 exclude_remaining_amount 포함
        if meeting.meeting_type == MeetingType.SOCIAL:
            # expense_items는 항상 배열로 반환 (None이면 빈 배열)
            logger.info(f"정산 조회 - expense.expense_items: {expense.expense_items}, type: {type(expense.expense_items)}, is None: {expense.expense_items is None}")
            logger.info(f"정산 조회 - hasattr(expense, 'expense_items'): {hasattr(expense, 'expense_items')}")
            
            # expense_items 처리
            if hasattr(expense, 'expense_items'):
                if expense.expense_items is None:
                    settlement_data["expense_items"] = []
                    logger.info("정산 조회 - expense.expense_items가 None이므로 빈 배열로 설정")
                elif isinstance(expense.expense_items, (list, dict)):
                    # JSON 필드가 이미 Python 객체로 역직렬화되어 있음
                    if isinstance(expense.expense_items, dict):
                        # dict인 경우 (잘못된 형식) 빈 배열로 처리
                        logger.warning(f"정산 조회 - expense.expense_items가 dict 형식입니다: {expense.expense_items}")
                        settlement_data["expense_items"] = []
                    else:
                        settlement_data["expense_items"] = expense.expense_items
                        logger.info(f"정산 조회 - expense.expense_items를 그대로 사용: {settlement_data['expense_items']}")
                else:
                    # 문자열인 경우 JSON 파싱 시도
                    logger.warning(f"정산 조회 - expense.expense_items가 예상치 못한 형식입니다: {type(expense.expense_items)}")
                    settlement_data["expense_items"] = []
            else:
                settlement_data["expense_items"] = []
                logger.info("정산 조회 - expense에 expense_items 속성이 없음")
            
            # exclude_remaining_amount는 Boolean 또는 None
            logger.info(f"정산 조회 - expense.exclude_remaining_amount: {expense.exclude_remaining_amount}, type: {type(expense.exclude_remaining_amount)}, is None: {expense.exclude_remaining_amount is None if hasattr(expense, 'exclude_remaining_amount') else 'N/A'}")
            if hasattr(expense, 'exclude_remaining_amount'):
                settlement_data["exclude_remaining_amount"] = expense.exclude_remaining_amount if expense.exclude_remaining_amount is not None else False
            else:
                settlement_data["exclude_remaining_amount"] = False
                logger.info("정산 조회 - expense에 exclude_remaining_amount 속성이 없음")
            
            logger.info(f"정산 조회 최종 응답 - expense_items: {settlement_data['expense_items']}, exclude_remaining_amount: {settlement_data['exclude_remaining_amount']}")
            
            # exclude_remaining_amount가 true이고 ExpenseParticipant가 없을 때
            # expense_items의 participants를 기반으로 total_participants 계산
            if settlement_data.get('exclude_remaining_amount') and total_participants_count == 0:
                expense_items = settlement_data.get('expense_items', [])
                if expense_items:
                    all_participants_from_items = set()
                    for item in expense_items:
                        item_participants = item.get('participants', [])
                        if isinstance(item_participants, list):
                            for participant_id in item_participants:
                                if participant_id and participant_id != 'UNSETTLED':
                                    all_participants_from_items.add(participant_id)
                    
                    if all_participants_from_items:
                        total_participants_count = len(all_participants_from_items)
                        settlement_targets = list(all_participants_from_items)
                        settlement_data["total_participants"] = total_participants_count
                        settlement_data["settlement_targets"] = settlement_targets
                        logger.info(f"정산 조회 - exclude_remaining_amount=true이고 ExpenseParticipant가 없어서 expense_items 기반으로 계산: total_participants={total_participants_count}, settlement_targets={settlement_targets}")
        
        # 라운딩 정산일 때만 추가 필드 포함
        if meeting.meeting_type == MeetingType.ROUND:
            # Expense 모델에 해당 필드가 있는지 확인 후 포함
            if hasattr(expense, 'green_fee'):
                settlement_data["green_fee"] = float(expense.green_fee) if expense.green_fee else 0
            if hasattr(expense, 'caddy_fee'):
                settlement_data["caddy_fee"] = float(expense.caddy_fee) if expense.caddy_fee else 0
            if hasattr(expense, 'cart_fee'):
                settlement_data["cart_fee"] = float(expense.cart_fee) if expense.cart_fee else 0
            if hasattr(expense, 'other_fee'):
                settlement_data["other_fee"] = float(expense.other_fee) if expense.other_fee else 0
            if hasattr(expense, 'status'):
                settlement_data["status"] = expense.status
            
            # 필드별 정산 대상자 포함
            if hasattr(expense, 'total_cost_participants'):
                settlement_data["total_cost_participants"] = expense.total_cost_participants if expense.total_cost_participants else []
            if hasattr(expense, 'total_cost_exempted'):
                settlement_data["total_cost_exempted"] = expense.total_cost_exempted if expense.total_cost_exempted else []
            if hasattr(expense, 'green_fee_participants'):
                settlement_data["green_fee_participants"] = expense.green_fee_participants if expense.green_fee_participants else []
            if hasattr(expense, 'green_fee_exempted'):
                settlement_data["green_fee_exempted"] = expense.green_fee_exempted if expense.green_fee_exempted else []
            if hasattr(expense, 'cart_fee_participants'):
                settlement_data["cart_fee_participants"] = expense.cart_fee_participants if expense.cart_fee_participants else []
            if hasattr(expense, 'cart_fee_exempted'):
                settlement_data["cart_fee_exempted"] = expense.cart_fee_exempted if expense.cart_fee_exempted else []
            if hasattr(expense, 'caddy_fee_participants'):
                settlement_data["caddy_fee_participants"] = expense.caddy_fee_participants if expense.caddy_fee_participants else []
            if hasattr(expense, 'caddy_fee_exempted'):
                settlement_data["caddy_fee_exempted"] = expense.caddy_fee_exempted if expense.caddy_fee_exempted else []
            if hasattr(expense, 'other_expense_items'):
                settlement_data["other_expense_items"] = expense.other_expense_items if expense.other_expense_items else []
            if hasattr(expense, 'exempted_participants'):
                settlement_data["exempted_participants"] = expense.exempted_participants if expense.exempted_participants else []
            
            # 회비 처리 필드 포함
            if hasattr(expense, 'all_covered_by_fee'):
                settlement_data["all_covered_by_fee"] = expense.all_covered_by_fee if expense.all_covered_by_fee is not None else False
            else:
                settlement_data["all_covered_by_fee"] = False
            if hasattr(expense, 'green_fee_covered_by_fee'):
                settlement_data["green_fee_covered_by_fee"] = expense.green_fee_covered_by_fee if expense.green_fee_covered_by_fee is not None else False
            else:
                settlement_data["green_fee_covered_by_fee"] = False
            if hasattr(expense, 'caddy_fee_covered_by_fee'):
                settlement_data["caddy_fee_covered_by_fee"] = expense.caddy_fee_covered_by_fee if expense.caddy_fee_covered_by_fee is not None else False
            else:
                settlement_data["caddy_fee_covered_by_fee"] = False
            if hasattr(expense, 'cart_fee_covered_by_fee'):
                settlement_data["cart_fee_covered_by_fee"] = expense.cart_fee_covered_by_fee if expense.cart_fee_covered_by_fee is not None else False
            else:
                settlement_data["cart_fee_covered_by_fee"] = False
        
        return {
            "settlement": settlement_data
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"정산 조회 오류: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="서버 내부 오류가 발생했습니다."
        )

# =============================================================================
# 내 정산 보기 API
# =============================================================================

@router.get("/{meeting_id}/settlement/my")
async def get_my_settlement(
    meeting_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """현재 사용자의 정산 정보 조회 (납부해야 할 금액만)"""
    try:
        # 모임 존재 확인
        meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
        if not meeting:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="모임을 찾을 수 없습니다."
            )
        
        # 정산 존재 확인 (정산 확정 여부는 체크하지 않음)
        
        # 클럽 멤버십 확인
        membership = db.query(ClubMembership).filter(
            ClubMembership.club_id == meeting.club_id,
            ClubMembership.user_id == current_user.id,
            ClubMembership.status.in_(MEMBERSHIP_ACTIVE_STATUSES)
        ).first()
        
        if not membership:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="클럽 멤버만 정산을 조회할 수 있습니다."
            )
        
        # 정산 조회
        expense = db.query(Expense).filter(Expense.meeting_id == meeting_id).first()
        
        if not expense:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="정산 정보를 찾을 수 없습니다."
            )
        
        # 현재 사용자의 ExpenseParticipant 조회
        expense_participant = db.query(ExpenseParticipant).filter(
            ExpenseParticipant.expense_id == expense.id,
            ExpenseParticipant.user_id == current_user.id
        ).first()
        
        amount_paid = float(expense_participant.amount_paid) if expense_participant and expense_participant.amount_paid else 0
        is_paid = expense_participant.is_paid if expense_participant else False
        
        items = []
        total_amount_due_decimal = Decimal('0')
        
        if meeting.meeting_type == MeetingType.ROUND:
            # 라운딩 정산: 필드별로 사용자가 포함된 항목만 계산
            user_id = current_user.id
            
            # 그린피
            green_fee_participants = expense.green_fee_participants if expense.green_fee_participants else []
            green_fee_exempted = expense.green_fee_exempted if expense.green_fee_exempted else []
            if user_id in green_fee_participants and user_id not in green_fee_exempted:
                green_fee = Decimal(str(expense.green_fee)) if expense.green_fee else Decimal('0')
                participants_count = len([p for p in green_fee_participants if p not in green_fee_exempted])
                if participants_count > 0:
                    my_green_fee = green_fee / participants_count
                    total_amount_due_decimal += my_green_fee
                    items.append({
                        "type": "green_fee",
                        "name": "그린피",
                        "amount": float(green_fee),
                        "participants_count": participants_count,
                        "my_amount": float(my_green_fee)
                    })
            
            # 카트비
            cart_fee_participants = expense.cart_fee_participants if expense.cart_fee_participants else []
            cart_fee_exempted = expense.cart_fee_exempted if expense.cart_fee_exempted else []
            if user_id in cart_fee_participants and user_id not in cart_fee_exempted:
                cart_fee = Decimal(str(expense.cart_fee)) if expense.cart_fee else Decimal('0')
                participants_count = len([p for p in cart_fee_participants if p not in cart_fee_exempted])
                if participants_count > 0:
                    my_cart_fee = cart_fee / participants_count
                    total_amount_due_decimal += my_cart_fee
                    items.append({
                        "type": "cart_fee",
                        "name": "카트비",
                        "amount": float(cart_fee),
                        "participants_count": participants_count,
                        "my_amount": float(my_cart_fee)
                    })
            
            # 캐디피
            caddy_fee_participants = expense.caddy_fee_participants if expense.caddy_fee_participants else []
            caddy_fee_exempted = expense.caddy_fee_exempted if expense.caddy_fee_exempted else []
            if user_id in caddy_fee_participants and user_id not in caddy_fee_exempted:
                caddy_fee = Decimal(str(expense.caddy_fee)) if expense.caddy_fee else Decimal('0')
                participants_count = len([p for p in caddy_fee_participants if p not in caddy_fee_exempted])
                if participants_count > 0:
                    my_caddy_fee = caddy_fee / participants_count
                    total_amount_due_decimal += my_caddy_fee
                    items.append({
                        "type": "caddy_fee",
                        "name": "캐디피",
                        "amount": float(caddy_fee),
                        "participants_count": participants_count,
                        "my_amount": float(my_caddy_fee)
                    })
            
            # 기타 비용
            other_expense_items = expense.other_expense_items if expense.other_expense_items else []
            for item in other_expense_items:
                item_participants = item.get('participants', [])
                if user_id in item_participants:
                    item_amount = Decimal(str(item.get('amount', 0)))
                    participants_count = len(item_participants)
                    if participants_count > 0:
                        my_item_amount = item_amount / participants_count
                        total_amount_due_decimal += my_item_amount
                        items.append({
                            "type": "other_expense",
                            "name": item.get('title', '기타 비용'),
                            "amount": float(item_amount),
                            "participants_count": participants_count,
                            "my_amount": float(my_item_amount)
                        })
        else:
            # 소셜 정산: expense_items에서 사용자가 포함된 항목만 계산
            expense_items = expense.expense_items if expense.expense_items else []
            user_id = current_user.id
            
            for item in expense_items:
                item_participants = item.get('participants', [])
                if user_id in item_participants:
                    item_amount = Decimal(str(item.get('amount', 0)))
                    participants_count = len(item_participants)
                    if participants_count > 0:
                        my_item_amount = item_amount / participants_count
                        total_amount_due_decimal += my_item_amount
                        items.append({
                            "type": "expense_item",
                            "name": item.get('title', '비용 항목'),
                            "amount": float(item_amount),
                            "participants_count": participants_count,
                            "my_amount": float(my_item_amount)
                        })
            
            # exclude_remaining_amount가 false이고 나머지 금액이 있으면 추가
            if not expense.exclude_remaining_amount:
                total_cost = Decimal(str(expense.amount))
                expense_items_total = sum(Decimal(str(item.get('amount', 0))) for item in expense_items)
                remaining_amount = total_cost - expense_items_total
                if remaining_amount > 0:
                    # 나머지 금액은 전체 정산 대상자에게 분배
                    # ExpenseParticipant에서 정산 대상자 추출
                    all_participants = db.query(ExpenseParticipant).filter(
                        ExpenseParticipant.expense_id == expense.id
                    ).all()
                    # 게스트와 일반 사용자 모두 포함
                    settlement_targets = []
                    for p in all_participants:
                        if p.guest_id:
                            settlement_targets.append(p.guest_id)
                        elif p.user_id:
                            settlement_targets.append(p.user_id)
                    
                    if user_id in settlement_targets and len(settlement_targets) > 0:
                        my_remaining_amount = remaining_amount / len(settlement_targets)
                        total_amount_due_decimal += my_remaining_amount
                        items.append({
                            "type": "remaining_amount",
                            "name": "나머지 금액",
                            "amount": float(remaining_amount),
                            "participants_count": len(settlement_targets),
                            "my_amount": float(my_remaining_amount)
                        })
        
        # total_amount_due를 각 항목의 my_amount 합으로 재계산하여 정확도 보장
        total_amount_due = sum(Decimal(str(item['my_amount'])) for item in items)
        total_amount_due_float = float(total_amount_due)
        remaining_amount = total_amount_due_float - amount_paid
        
        return {
            "total_amount_due": total_amount_due_float,
            "amount_paid": amount_paid,
            "remaining_amount": remaining_amount,
            "is_paid": is_paid,
            "items": items
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"내 정산 조회 오류: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="서버 내부 오류가 발생했습니다."
        )

# =============================================================================
# 정산 대상자 관리 API
# =============================================================================

@router.get("/{meeting_id}/settlement/available-participants")
async def get_available_participants(
    meeting_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """정산 대상자로 선택 가능한 참가자 목록 조회"""
    try:
        # 모임 존재 확인
        meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
        if not meeting:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="모임을 찾을 수 없습니다."
            )
        
        # 정산 권한 확인: 주최자 또는 참가자이면서 클럽 리더/매니저
        if not can_manage_settlement(meeting_id, current_user.id, db):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="모임 개설자 또는 참가자인 클럽 리더/매니저만 정산 대상자를 조회할 수 있습니다."
            )
        
        # 확정된 참가자 조회 (게스트 포함)
        participants = db.query(MeetingParticipant).options(
            joinedload(MeetingParticipant.user),
            joinedload(MeetingParticipant.guest)
        ).filter(
            MeetingParticipant.meeting_id == meeting_id,
            MeetingParticipant.status == MeetingParticipantStatus.CONFIRMED
        ).all()
        
        participant_list = []
        for meeting_participant in participants:
            if meeting_participant.guest_id:
                # 게스트인 경우
                guest = meeting_participant.guest
                if guest:
                    participant_list.append({
                        "id": None,  # 게스트는 id가 없음
                        "name": guest.name or "게스트",
                        "email": None,
                        "role": meeting_participant.role,
                        "joined_at": meeting_participant.created_at,
                        "is_guest": True
                    })
            else:
                # 일반 사용자인 경우
                user = meeting_participant.user
                if user:
                    participant_list.append({
                        "id": user.id,
                        "name": user.nickname or user.realname,
                        "email": user.email,
                        "role": meeting_participant.role,
                        "joined_at": meeting_participant.created_at,
                        "is_guest": False
                    })
        
        return {"participants": participant_list}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"정산 대상자 조회 오류: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="서버 내부 오류가 발생했습니다."
        )



















