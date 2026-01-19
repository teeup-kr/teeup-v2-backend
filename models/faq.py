# FAQ 관련 모델
from sqlalchemy import Column, String, Text, DateTime, Boolean, Integer, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base

class FAQCategory(Base):
    """FAQ 카테고리 모델"""
    __tablename__ = "faq_categories"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    title = Column(String(50), nullable=False, unique=True, comment="카테고리명")
    order = Column(Integer, nullable=False, default=0, comment="정렬 순서")
    is_active = Column(Boolean, default=True, comment="활성 상태")
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # 관계 설정
    faqs = relationship("FAQ", back_populates="category")

    def __repr__(self):
        return f"<FAQCategory(id={self.id}, title='{self.title}', order={self.order})>"


class FAQ(Base):
    """FAQ 모델"""
    __tablename__ = "faqs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    category_id = Column(Integer, ForeignKey('faq_categories.id'), nullable=True, comment="카테고리 ID")
    question = Column(String(300), nullable=False, comment="질문")
    answer = Column(Text, nullable=False, comment="답변")
    order = Column(Integer, nullable=False, default=0, comment="정렬 순서")
    is_active = Column(Boolean, default=True, comment="공개 여부")
    view_count = Column(Integer, default=0, comment="조회수")
    is_deleted = Column(Boolean, default=False, comment="삭제 여부")
    created_by = Column(Integer, ForeignKey("admins.id", ondelete="SET NULL"), nullable=True, comment="작성자 admin_id")
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    deleted_at = Column(DateTime, nullable=True, comment="삭제일시")
    
    # 관계 설정
    category = relationship("FAQCategory", back_populates="faqs")
    creator = relationship("Admin", backref="faqs")

    def __repr__(self):
        return f"<FAQ(id={self.id}, question='{self.question}', category_id={self.category_id})>"

