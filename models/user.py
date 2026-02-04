# User 관련 모델
from sqlalchemy import Column, String, Text, DateTime, Boolean, Integer, Enum, ForeignKey, DECIMAL
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base
from .enums import (UserStatus, Provider, Gender, HandicapUpdateMethod, TokenRevokeReason)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="순번 ID (AUTO_INCREMENT)")
    email = Column(String(255), unique=True)
    nickname = Column(String(255), unique=True)
    password = Column(String(255))
    profile_image = Column(String(255))

    realname = Column(String(255))
    phone_number = Column(String(255), unique=True)
    gender = Column(Enum(Gender))
    birthdate = Column(DateTime)

    # 핸디캡 시스템 개선 필드
    average_score_init = Column(Integer)
    average_score = Column(Integer)
    handicap_init = Column(DECIMAL(4, 1), comment="가입 시 수동 입력한 핸디캡")
    handicap = Column(DECIMAL(4, 1), comment="자동 계산된 핸디캡 (최근 N경기 평균 기반)")

    handicap_update_method = Column(Enum(HandicapUpdateMethod),
                                    default=HandicapUpdateMethod.MANUAL,
                                    comment="핸디캡 업데이트 방식")
    handicap_calculation_count = Column(Integer, default=0, comment="핸디캡 계산에 사용된 경기 수")
    provider = Column(Enum(Provider), default=Provider.LOCAL)
    provider_id = Column(String(255))
    email_verified = Column(DateTime)
    password_reset_token = Column(String(255), unique=True)
    password_reset_expires = Column(DateTime)
    status = Column(Enum(UserStatus), default=UserStatus.ACTIVE)
    deactivated_at = Column(DateTime)
    needs_terms_agreement = Column(Boolean, default=True)
    original_nickname = Column(String(255))  # 탈퇴 시 원래 닉네임 저장
    nickname_locked_until = Column(DateTime)  # 닉네임 사용 금지 기간 (7일)
    # 약관 동의 필드들 (필수: False, 선택: False)
    terms_agreement = Column(Boolean, default=False)  # 서비스이용약관 (필수)
    privacy_policy = Column(Boolean, default=False)  # 개인정보처리방침 (필수)
    privacy_collection = Column(Boolean, default=False)  # 개인정보 수집 및 이용동의 (필수)
    marketing_consent = Column(Boolean, default=False)  # 마케팅정보 수신동의 (선택)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    deleted_at = Column(DateTime)


class RefreshTokenBlacklist(Base):
    __tablename__ = "refresh_token_blacklist"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="순번 ID (AUTO_INCREMENT)")
    token_jti = Column(String(255), nullable=False, unique=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    reason = Column(Enum(TokenRevokeReason), nullable=False)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=func.now())

    # 관계 설정
    user = relationship("User", backref="blacklisted_tokens")
