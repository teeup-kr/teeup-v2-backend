# Notice 모델 (일반 공지사항)
from sqlalchemy import Column, String, Text, DateTime, Boolean, Integer, Enum, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base
from .enums import NoticeType

class Notice(Base):
    __tablename__ = "notices"
    
    id = Column(Integer, primary_key=True, autoincrement=True, comment="순번 ID (AUTO_INCREMENT)")
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    type = Column(Enum(NoticeType), nullable=False)
    club_id = Column(Integer, ForeignKey("clubs.id", ondelete="CASCADE"))
    author_id = Column(Integer, ForeignKey("admins.id", ondelete="CASCADE"), nullable=False)
    is_important = Column(Boolean, default=False)
    is_published = Column(Boolean, default=False)
    view_count = Column(Integer, default=0, comment="조회수")
    published_at = Column(DateTime, nullable=True)
    attachment_file = Column(String(255), nullable=True, comment="첨부 파일명")
    web_view_link = Column(String(512), nullable=True, comment="Google Drive 웹 뷰 링크")
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # 관계 설정
    club = relationship("Club", backref="notices")
    author = relationship("Admin", backref="notices")

