# Meeting 관련 모델
from sqlalchemy import Column, String, Text, DateTime, Boolean, Integer, Enum, ForeignKey, DECIMAL, JSON, CheckConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base
from .enums import Gender, ParticipantStatus, ParticipantRole, ParticipantType, ExpenseItemType, SettlementMethod, MeetingType, MeetingSubtype, SocialType

class Guest(Base):
    """게스트 정보 테이블"""
    __tablename__ = "guests"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="순번 ID (AUTO_INCREMENT)")
    name = Column(String(255), nullable=False, comment="게스트 이름")
    handicap = Column(DECIMAL(4, 1), nullable=True, comment="게스트 핸디캡 (평균 타수 - 72)")
    birthdate = Column(DateTime, nullable=True, comment="게스트 생년월일")
    gender = Column(Enum(Gender), nullable=True, comment="게스트 성별")
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # 관계 설정
    meeting_participations = relationship("MeetingParticipant",
                                          backref="guest",
                                          foreign_keys="MeetingParticipant.guest_id")


class Meeting(Base):
    __tablename__ = "meetings"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="순번 ID (AUTO_INCREMENT)")
    name = Column(String(255), nullable=False)
    description = Column(Text)
    location = Column(String(255))
    meeting_time = Column(DateTime)
    tee_times = Column(JSON)
    max_participants = Column(Integer)
    meeting_type = Column(Enum(MeetingType), nullable=False, comment="모임 타입 (ROUND/SOCIAL)")
    meeting_subtype = Column(Enum(MeetingSubtype), nullable=True, comment="모임 하위 타입 (라운딩: REGULAR/IRREGULAR/ONE_TIME)")
    total_cost = Column(DECIMAL(10, 2))
    green_fee = Column(DECIMAL(10, 2))
    caddy_fee = Column(DECIMAL(10, 2))
    cart_fee = Column(DECIMAL(10, 2))
    settlement_method = Column(Enum(SettlementMethod), nullable=True, comment="정산 방법 (라운딩/소셜 공통)")
    course_name = Column(String(255))
    hole_count = Column(Integer)
    reservation_name = Column(String(255))
    venue_name = Column(String(255))
    club_id = Column(Integer, ForeignKey("clubs.id", ondelete="CASCADE"), nullable=False)
    status = Column(String(50), default="SCHEDULED")
    cancel_reason = Column(Text)
    application_deadline = Column(DateTime)
    application_closed_early = Column(Boolean, default=False)
    team_formation_mode = Column(String(50))
    team_size = Column(Integer)
    team_formation_confirmed_at = Column(DateTime, nullable=True, comment="팀 편성 확정일자")
    rounding_started_at = Column(DateTime, nullable=True, comment="모임 진행 시작일자")
    rounding_completed_at = Column(DateTime, nullable=True, comment="라운딩 종료일자")
    is_completed = Column(Boolean, default=False)
    settlement_confirmed = Column(Boolean, default=False)
    social_cost = Column(DECIMAL(10, 2))
    social_notes = Column(Text)
    social_type = Column(Enum(SocialType), nullable=True, comment="소셜 모임 유형 (CASUAL/DINNER/EVENT)")
    is_private = Column(Boolean, default=False, nullable=False, comment="프라이빗 라운딩 여부")
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True, comment="라운딩 생성자 ID")
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # 관계 설정
    club = relationship("Club", backref="meetings")
    creator = relationship("User", foreign_keys=[created_by], backref="created_meetings")


class MeetingParticipant(Base):
    __tablename__ = "meeting_participants"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="순번 ID (AUTO_INCREMENT)")
    meeting_id = Column(Integer, ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False)
    # user_id와 guest_id 중 하나만 있어야 함 (일반 사용자 또는 게스트)
    user_id = Column(Integer,
                     ForeignKey("users.id", ondelete="CASCADE"),
                     nullable=True,
                     comment="일반 사용자 ID (게스트가 아닌 경우)")
    guest_id = Column(Integer, ForeignKey("guests.id", ondelete="CASCADE"), nullable=True, comment="게스트 ID (게스트인 경우)")
    participant_type = Column(Enum(ParticipantType),
                              nullable=False,
                              comment="참가자 타입: USER 또는 GUEST (user_id가 있으면 USER, guest_id가 있으면 GUEST)")
    status = Column(Enum(ParticipantStatus), default=ParticipantStatus.CONFIRMED, nullable=False,
                    comment="참가 상태: PENDING/CONFIRMED/CANCELED/WAITING_LIST")
    role = Column(Enum(ParticipantRole), default=ParticipantRole.PARTICIPANT, nullable=False,
                  comment="참가 역할: PARTICIPANT/ORGANIZER/CO_ORGANIZER")
    handicap = Column(Integer)
    average_score = Column(Integer)
    pace_preference = Column(String(50))
    tee_preference = Column(String(50))
    is_newbie = Column(Boolean, default=False)
    has_hole_scores = Column(Boolean, nullable=False, default=False, comment="홀별 점수 입력 여부")
    prefer_with = Column(JSON)
    avoid_with = Column(JSON)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # 제약조건: user_id와 guest_id 중 하나만 있어야 함
    __table_args__ = (CheckConstraint(
        '(user_id IS NOT NULL AND guest_id IS NULL) OR (user_id IS NULL AND guest_id IS NOT NULL)',
        name='check_user_or_guest'), )

    # 관계 설정
    meeting = relationship("Meeting", backref="participants", passive_deletes=True)
    user = relationship("User", backref="meeting_participations", foreign_keys=[user_id])


class Team(Base):
    __tablename__ = "teams"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="순번 ID (AUTO_INCREMENT)")
    name = Column(String(255), nullable=False)
    meeting_id = Column(Integer, ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False)
    formation_mode = Column(String(50))
    status = Column(String(50), default="DRAFT")
    formation_notes = Column(Text)
    total_handicap = Column(DECIMAL(5, 1), comment="팀 총 핸디캡")
    tee_off_order = Column(Integer, comment="티오프 순서")
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # 관계 설정
    meeting = relationship("Meeting", backref="teams")


class TeamMember(Base):
    __tablename__ = "team_members"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="순번 ID (AUTO_INCREMENT)")
    team_id = Column(Integer, ForeignKey("teams.id", ondelete="CASCADE"), nullable=False)
    # user_id와 guest_id 중 하나만 있어야 함 (일반 사용자 또는 게스트)
    user_id = Column(Integer,
                     ForeignKey("users.id", ondelete="CASCADE"),
                     nullable=True,
                     comment="일반 사용자 ID (게스트가 아닌 경우)")
    guest_id = Column(Integer, ForeignKey("guests.id", ondelete="CASCADE"), nullable=True, comment="게스트 ID (게스트인 경우)")
    order = Column(Integer)
    created_at = Column(DateTime, default=func.now())

    # 제약조건: user_id와 guest_id 중 하나만 있어야 함
    __table_args__ = (CheckConstraint(
        '(user_id IS NOT NULL AND guest_id IS NULL) OR (user_id IS NULL AND guest_id IS NOT NULL)',
        name='check_team_member_user_or_guest'), )

    # 관계 설정
    team = relationship("Team", backref="members")
    user = relationship("User", backref="team_memberships", foreign_keys=[user_id])
    guest = relationship("Guest", backref="team_memberships", foreign_keys=[guest_id])


class Expense(Base):
    """정산 묶음 (Expense → ExpenseItem → ExpenseItemParticipant)"""
    __tablename__ = "expenses"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="순번 ID (AUTO_INCREMENT)")
    meeting_id = Column(Integer, ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False)
    club_id = Column(Integer, ForeignKey("clubs.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    created_by = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    notes = Column(Text)
    exclude_remaining_amount = Column(Boolean, default=False, nullable=True, comment="나머지 금액 정산 제외")
    amount = Column(DECIMAL(10, 2), nullable=True, comment="총액 (ExpenseItem 합계 캐시)")
    total_participants = Column(Integer, default=0, nullable=True, comment="정산 대상자 수 캐시")
    amount_per_person = Column(DECIMAL(10, 2), nullable=True, comment="1인당 금액 캐시")
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # 관계 설정
    meeting = relationship("Meeting", backref="expenses")
    club = relationship("Club", backref="expenses")
    creator = relationship("User", backref="created_expenses")
    items = relationship("ExpenseItem", backref="expense", cascade="all, delete-orphan", order_by="ExpenseItem.id")


class ExpenseItem(Base):
    """비용 항목 (그린피/캐디피/카트비/기타 = 행으로 관리)"""
    __tablename__ = "expense_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    expense_id = Column(Integer, ForeignKey("expenses.id", ondelete="CASCADE"), nullable=False)

    type = Column(Enum(ExpenseItemType), nullable=False, comment="GREEN_FEE/CADDY_FEE/CART_FEE/OTHER/SOCIAL_ITEM")
    title = Column(String(255), nullable=True, comment="OTHER 타입 시 항목명 (예: 점심비)")
    memo = Column(String(2000), nullable=True, comment="항목별 메모 (소셜/기타 비용)")
    amount = Column(DECIMAL(10, 2), nullable=False)
    covered_by_fee = Column(Boolean, default=False, comment="회비에서 처리 여부")
    order_index = Column(Integer, default=0, comment="표시 순서")

    created_at = Column(DateTime, default=func.now())

    # 관계 설정
    participants = relationship("ExpenseItemParticipant", backref="expense_item", cascade="all, delete-orphan")


class ExpenseItemParticipant(Base):
    """비용 항목별 정산 대상자"""
    __tablename__ = "expense_item_participants"

    id = Column(Integer, primary_key=True, autoincrement=True)
    expense_item_id = Column(Integer, ForeignKey("expense_items.id", ondelete="CASCADE"), nullable=False)

    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    guest_id = Column(Integer, ForeignKey("guests.id", ondelete="CASCADE"), nullable=True)

    is_exempted = Column(Boolean, default=False, comment="면제 여부")
    amount = Column(DECIMAL(10, 2), nullable=True, comment="해당 참가자 부담액")
    amount_paid = Column(DECIMAL(10, 2), nullable=True, comment="실제 지불액")
    is_paid = Column(Boolean, default=False)
    paid_at = Column(DateTime, nullable=True)

    __table_args__ = (CheckConstraint(
        "(user_id IS NOT NULL AND guest_id IS NULL) OR (user_id IS NULL AND guest_id IS NOT NULL)",
        name="chk_expense_item_user_or_guest",
    ), )

    # 관계 설정
    user = relationship("User", backref="expense_item_participations")
    guest = relationship("Guest", backref="expense_item_participations", foreign_keys=[guest_id])


class Score(Base):
    __tablename__ = "scores"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="순번 ID (AUTO_INCREMENT)")
    participant_id = Column(Integer, ForeignKey("meeting_participants.id", ondelete="CASCADE"), nullable=False)
    hole_number = Column(Integer, nullable=False)
    strokes = Column(Integer, nullable=False)
    par = Column(Integer, nullable=False)
    score_to_par = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # 관계 설정
    participant = relationship("MeetingParticipant", backref="scores")


class UserScoreHistory(Base):
    """사용자의 최근 경기 스코어 히스토리"""
    __tablename__ = "user_score_history"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="순번 ID (AUTO_INCREMENT)")
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    meeting_id = Column(Integer, ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False)
    gross_score = Column(Integer, nullable=False, comment="실제 타수 (Gross Score)")
    net_score = Column(DECIMAL(5, 1), comment="넷 스코어 (Gross Score - Handicap)")
    handicap_used = Column(DECIMAL(4, 1), nullable=False, comment="해당 경기에서 사용된 핸디캡 (넷 계산 기준)")
    handicap_after_round = Column(
        DECIMAL(4, 1),
        nullable=True,
        comment="이 경기 반영 후 핸디캡 (자동 재계산 결과, 기록 표시용)",
    )
    played_at = Column(DateTime, nullable=False, comment="경기 날짜")
    created_at = Column(DateTime, default=func.now())

    # 관계 설정
    user = relationship("User", backref="score_history")
    meeting = relationship("Meeting", backref="score_history")


class MeetingResult(Base):
    """직전 대회 성적 저장 (순위만 저장, 스코어 정보는 UserScoreHistory 참조)"""
    __tablename__ = "meeting_results"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="순번 ID (AUTO_INCREMENT)")
    meeting_id = Column(Integer, ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    rank = Column(Integer, comment="순위")
    completed_at = Column(DateTime, nullable=False, comment="경기 완료 시간")
    created_at = Column(DateTime, default=func.now())

    # 관계 설정
    meeting = relationship("Meeting", backref="results")
    user = relationship("User", backref="meeting_results")
