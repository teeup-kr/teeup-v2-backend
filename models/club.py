# Club 관련 모델
from sqlalchemy import Column, String, Text, DateTime, Boolean, Integer, Enum, ForeignKey, DECIMAL, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base
from .enums import ClubType, ClubStatus, ClubRole, MembershipStatus, BillingCycle


class Club(Base):
    __tablename__ = "clubs"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="순번 ID (AUTO_INCREMENT)")
    display_id = Column(String(25), unique=True, nullable=True)
    name = Column(String(255), nullable=False)
    sido_code = Column(String(2), ForeignKey("sido.code"), nullable=False, comment="시도 코드")
    type = Column(Enum(ClubType), default=ClubType.REGULAR)
    description = Column(Text)
    member_count = Column(Integer)
    representative_name = Column(String(255))
    location = Column(String(255))
    contact_info = Column(String(255))
    additional_info = Column(Text)
    profile_image = Column(String(255))
    status = Column(Enum(ClubStatus), default=ClubStatus.ACTIVE)
    # 모임 정산 기능 (클럽 단위). False면 정산 탭/API 비활성, 기존 DB 행은 True로 간주
    settlement_enabled = Column(Boolean, nullable=False, default=True, server_default="1")

    # 타임스탬프 필드
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    deleted_at = Column(DateTime)


class ClubMembership(Base):
    __tablename__ = "club_memberships"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="순번 ID (AUTO_INCREMENT)")
    club_id = Column(Integer, ForeignKey("clubs.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    role = Column(Enum(ClubRole), default=ClubRole.MEMBER)
    status = Column(Enum(MembershipStatus), default=MembershipStatus.ACTIVE)
    note = Column(Text, nullable=True)  # 구성원 메모 (리더/매니저만 작성/조회 가능)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # 관계 설정
    club = relationship("Club", backref="memberships")
    user = relationship("User", backref="club_memberships")


class ClubNotice(Base):
    __tablename__ = "club_notices"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="순번 ID (AUTO_INCREMENT)")
    club_id = Column(Integer, ForeignKey("clubs.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    is_important = Column(Boolean, default=False)
    is_private = Column(Boolean, default=False)  # 비공개 공지사항 여부
    author_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    view_count = Column(Integer, default=0, comment="조회수")
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # 관계 설정
    club = relationship("Club", backref="club_notices")
    author = relationship("User", backref="club_notices")


class ClubFee(Base):
    __tablename__ = "club_fees"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="순번 ID (AUTO_INCREMENT)")
    club_id = Column(Integer, ForeignKey("clubs.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)  # 회비 항목명
    amount = Column(DECIMAL(10, 2), nullable=False)  # 회비 금액
    cycle = Column(Enum(BillingCycle))  # 회비 주기 (MONTHLY, QUARTERLY, YEARLY, ONE_TIME)
    description = Column(Text)  # 회비 설명
    is_active = Column(Boolean, default=True)  # 활성 여부
    created_by = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # 관계 설정
    club = relationship("Club", backref="club_fees")
    creator = relationship("User", backref="club_fees")


class ClubRegion(Base):
    __tablename__ = "club_regions"
    __table_args__ = (UniqueConstraint("club_id", "gungu_code", name="uq_club_region"), )

    id = Column(Integer, primary_key=True, autoincrement=True, comment="순번 ID (AUTO_INCREMENT)")
    club_id = Column(Integer, ForeignKey("clubs.id", ondelete="CASCADE"), nullable=False)
    gungu_code = Column(String(5), ForeignKey("gungu.code"), nullable=False, comment="군구 코드")
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    club = relationship("Club", backref="club_regions")


class RegulationCategory(Base):
    __tablename__ = "regulation_categories"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="순번 ID (AUTO_INCREMENT)")
    club_id = Column(Integer, ForeignKey("clubs.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    order = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # 관계 설정
    club = relationship("Club", backref="regulation_categories")
    regulations = relationship("Regulation", back_populates="category", cascade="all, delete-orphan")


class Regulation(Base):
    __tablename__ = "regulations"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="순번 ID (AUTO_INCREMENT)")
    club_id = Column(Integer, ForeignKey("clubs.id", ondelete="CASCADE"), nullable=False)
    category_id = Column(Integer, ForeignKey("regulation_categories.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    status = Column(String(50), default="ACTIVE")
    created_by = Column(Integer, nullable=False, comment="작성자 user_id")
    created_by_name = Column(String(255), nullable=True, comment="작성자 이름 스냅샷")
    published_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # 관계 설정
    club = relationship("Club", backref="regulations")
    category = relationship("RegulationCategory", back_populates="regulations")
