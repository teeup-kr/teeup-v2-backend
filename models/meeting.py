# Meeting 관련 모델
from sqlalchemy import Column, String, Text, DateTime, Boolean, Integer, Enum, ForeignKey, DECIMAL, JSON, CheckConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base
from .enums import Gender, ParticipantType

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
    meeting_participations = relationship("MeetingParticipant", backref="guest", foreign_keys="MeetingParticipant.guest_id")

class Meeting(Base):
    __tablename__ = "meetings"
    
    id = Column(Integer, primary_key=True, autoincrement=True, comment="순번 ID (AUTO_INCREMENT)")
    name = Column(String(255), nullable=False)
    description = Column(Text)
    location = Column(String(255))
    meeting_time = Column(DateTime)
    tee_times = Column(JSON)
    max_participants = Column(Integer)
    meeting_type = Column(String(50), nullable=False)
    meeting_subtype = Column(String(50))
    total_cost = Column(DECIMAL(10, 2))
    green_fee = Column(DECIMAL(10, 2))
    caddy_fee = Column(DECIMAL(10, 2))
    cart_fee = Column(DECIMAL(10, 2))
    settlement_method = Column(String(50))
    social_settlement_method = Column(String(50))
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
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, comment="일반 사용자 ID (게스트가 아닌 경우)")
    guest_id = Column(Integer, ForeignKey("guests.id", ondelete="CASCADE"), nullable=True, comment="게스트 ID (게스트인 경우)")
    participant_type = Column(Enum(ParticipantType), nullable=False, comment="참가자 타입: USER 또는 GUEST (user_id가 있으면 USER, guest_id가 있으면 GUEST)")
    handicap_index = Column(Integer)
    recent_avg_score = Column(Integer)
    pace_preference = Column(String(50))
    tee_preference = Column(String(50))
    is_newbie = Column(Boolean, default=False)
    prefer_with = Column(JSON)
    avoid_with = Column(JSON)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # 제약조건: user_id와 guest_id 중 하나만 있어야 함
    __table_args__ = (
        CheckConstraint('(user_id IS NOT NULL AND guest_id IS NULL) OR (user_id IS NULL AND guest_id IS NOT NULL)', name='check_user_or_guest'),
    )
    
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
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, comment="일반 사용자 ID (게스트가 아닌 경우)")
    guest_id = Column(Integer, ForeignKey("guests.id", ondelete="CASCADE"), nullable=True, comment="게스트 ID (게스트인 경우)")
    order = Column(Integer)
    created_at = Column(DateTime, default=func.now())
    
    # 제약조건: user_id와 guest_id 중 하나만 있어야 함
    __table_args__ = (
        CheckConstraint('(user_id IS NOT NULL AND guest_id IS NULL) OR (user_id IS NULL AND guest_id IS NOT NULL)', name='check_team_member_user_or_guest'),
    )
    
    # 관계 설정
    team = relationship("Team", backref="members")
    user = relationship("User", backref="team_memberships", foreign_keys=[user_id])
    guest = relationship("Guest", backref="team_memberships", foreign_keys=[guest_id])

class Expense(Base):
    __tablename__ = "expenses"
    
    id = Column(Integer, primary_key=True, autoincrement=True, comment="순번 ID (AUTO_INCREMENT)")
    title = Column(String(255), nullable=False)
    description = Column(Text)
    amount = Column(DECIMAL(10, 2), nullable=False)
    total_participants = Column(Integer, nullable=False)
    amount_per_person = Column(DECIMAL(10, 2), nullable=False)
    meeting_id = Column(Integer, ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False)
    club_id = Column(Integer, ForeignKey("clubs.id", ondelete="CASCADE"), nullable=False)
    created_by = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    notes = Column(Text)
    expense_items = Column(JSON, nullable=True)  # 소셜 정산의 비용 항목 배열
    exclude_remaining_amount = Column(Boolean, default=False, nullable=True)  # 나머지 금액 정산 제외 여부
    # 라운딩 정산 필드
    green_fee = Column(DECIMAL(10, 2), nullable=True, comment="그린피")
    caddy_fee = Column(DECIMAL(10, 2), nullable=True, comment="캐디피")
    cart_fee = Column(DECIMAL(10, 2), nullable=True, comment="카트비")
    other_fee = Column(DECIMAL(10, 2), nullable=True, comment="기타 비용")
    # 필드별 정산 대상자 (JSON 배열)
    total_cost_participants = Column(JSON, nullable=True, comment="총 비용 정산 대상자")
    total_cost_exempted = Column(JSON, nullable=True, comment="총 비용 면제자")
    green_fee_participants = Column(JSON, nullable=True, comment="그린피 정산 대상자")
    green_fee_exempted = Column(JSON, nullable=True, comment="그린피 면제자")
    cart_fee_participants = Column(JSON, nullable=True, comment="카트비 정산 대상자")
    cart_fee_exempted = Column(JSON, nullable=True, comment="카트비 면제자")
    caddy_fee_participants = Column(JSON, nullable=True, comment="캐디피 정산 대상자")
    caddy_fee_exempted = Column(JSON, nullable=True, comment="캐디피 면제자")
    other_expense_items = Column(JSON, nullable=True, comment="기타 비용 항목 배열")
    exempted_participants = Column(JSON, nullable=True, comment="전체 면제자 목록")
    # 회비 처리 필드
    all_covered_by_fee = Column(Boolean, default=False, nullable=True, comment="모두 회비에서 처리")
    green_fee_covered_by_fee = Column(Boolean, default=False, nullable=True, comment="그린피 회비에서 처리")
    caddy_fee_covered_by_fee = Column(Boolean, default=False, nullable=True, comment="캐디피 회비에서 처리")
    cart_fee_covered_by_fee = Column(Boolean, default=False, nullable=True, comment="카트비 회비에서 처리")
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # 관계 설정
    meeting = relationship("Meeting", backref="expenses")
    club = relationship("Club", backref="expenses")
    creator = relationship("User", backref="created_expenses")

class ExpenseParticipant(Base):
    __tablename__ = "expense_participants"
    
    id = Column(Integer, primary_key=True, autoincrement=True, comment="순번 ID (AUTO_INCREMENT)")
    expense_id = Column(Integer, ForeignKey("expenses.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, comment="사용자 ID (게스트가 아닌 경우)")
    guest_id = Column(Integer, ForeignKey("guests.id", ondelete="CASCADE"), nullable=True, comment="게스트 ID (게스트인 경우)")
    amount_paid = Column(DECIMAL(10, 2))
    is_paid = Column(Boolean, default=False)
    paid_at = Column(DateTime)
    created_at = Column(DateTime, default=func.now())
    
    # 제약조건: user_id와 guest_id 중 하나만 존재해야 함
    __table_args__ = (
        CheckConstraint(
            '(user_id IS NOT NULL AND guest_id IS NULL) OR (user_id IS NULL AND guest_id IS NOT NULL)',
            name='chk_expense_user_or_guest_id'
        ),
    )
    
    # 관계 설정
    expense = relationship("Expense", backref="participants")
    user = relationship("User", backref="expense_participations")
    guest = relationship("Guest", backref="expense_participations", foreign_keys=[guest_id])

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
    handicap_used = Column(DECIMAL(4, 1), nullable=False, comment="해당 경기에서 사용된 핸디캡")
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
