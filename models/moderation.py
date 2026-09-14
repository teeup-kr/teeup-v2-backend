# 신고 / 차단 모델 (App Store Guideline 1.2 — 사용자 생성 콘텐츠 관리)
from sqlalchemy import Column, String, Text, DateTime, Integer, Enum, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base
from .enums import ReportTargetType, ReportReason, ReportStatus


class ContentReport(Base):
    """사용자가 제출한 콘텐츠·사용자 신고"""
    __tablename__ = "content_reports"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="순번 ID (AUTO_INCREMENT)")
    reporter_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, comment="신고자")
    target_type = Column(Enum(ReportTargetType), nullable=False, comment="신고 대상 종류")
    target_id = Column(Integer, nullable=False, comment="신고 대상 ID (target_type 기준)")
    reason = Column(Enum(ReportReason), nullable=False, comment="신고 사유")
    description = Column(Text, nullable=True, comment="상세 설명")
    status = Column(Enum(ReportStatus), default=ReportStatus.PENDING, nullable=False)
    admin_note = Column(Text, nullable=True, comment="운영자 처리 메모")
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    reporter = relationship("User", backref="content_reports")


class UserBlock(Base):
    """사용자 간 차단. blocker 는 blocked 의 콘텐츠를 더 이상 보지 않는다."""
    __tablename__ = "user_blocks"
    __table_args__ = (UniqueConstraint("blocker_id", "blocked_id", name="uq_user_block"),)

    id = Column(Integer, primary_key=True, autoincrement=True, comment="순번 ID (AUTO_INCREMENT)")
    blocker_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, comment="차단한 사용자")
    blocked_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, comment="차단당한 사용자")
    created_at = Column(DateTime, default=func.now())

    blocker = relationship("User", foreign_keys=[blocker_id], backref="blocks_made")
    blocked = relationship("User", foreign_keys=[blocked_id], backref="blocks_received")
