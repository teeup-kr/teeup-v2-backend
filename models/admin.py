# Admin 관련 모델
from sqlalchemy import Column, String, DateTime, Boolean, Integer, Enum, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base
from .enums import Provider, UserStatus


class Admin(Base):
    __tablename__ = "admins"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="순번 ID (AUTO_INCREMENT)")
    email = Column(String(255), unique=True, nullable=False)
    password = Column(String(255), nullable=False)
    name = Column(String(255), nullable=False)  # 관리자 이름
    profile_image = Column(String(255))  # 프로필 이미지
    phone_number = Column(String(255), unique=True)
    provider = Column(Enum(Provider), default=Provider.LOCAL)
    provider_id = Column(String(255))  # OAuth 제공자 ID
    email_verified = Column(DateTime)  # 이메일 인증일시
    status = Column(Enum(UserStatus), default=UserStatus.ACTIVE)
    deactivated_at = Column(DateTime)  # 비활성화 일시
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    deleted_at = Column(DateTime)  # 삭제 일시 (soft delete)
