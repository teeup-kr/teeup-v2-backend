# Terms 관련 모델
from sqlalchemy import Column, String, Text, DateTime, Boolean, Integer, ForeignKey, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base
from .enums import TermsType

class Terms(Base):
    __tablename__ = "terms"
    
    id = Column(Integer, primary_key=True, autoincrement=True, comment="순번 ID (AUTO_INCREMENT)")
    type = Column(Enum(TermsType), nullable=False)
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    is_active = Column(Boolean, default=True)
    is_required = Column(Boolean, default=False)
    published_at = Column(DateTime)
    created_by = Column(Integer, ForeignKey("admins.id", ondelete="SET NULL"), nullable=True, comment="작성자 admin_id")
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # 관계 설정
    creator = relationship("Admin", backref="terms")

class TermsAgreement(Base):
    __tablename__ = "terms_agreements"
    
    id = Column(Integer, primary_key=True, autoincrement=True, comment="순번 ID (AUTO_INCREMENT)")
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    terms_id = Column(Integer, ForeignKey("terms.id", ondelete="CASCADE"), nullable=False)
    agreed_at = Column(DateTime, nullable=False)
    ip_address = Column(String(45))
    user_agent = Column(Text)
    created_at = Column(DateTime, default=func.now())
    
    # 관계 설정
    user = relationship("User", backref="terms_agreements")
    terms = relationship("Terms", backref="agreements")

