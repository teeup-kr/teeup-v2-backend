# Notification 모델
from sqlalchemy import Column, String, Text, DateTime, Integer, ForeignKey, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base
from .enums import NotificationType, NotificationStatus

class Notification(Base):
    __tablename__ = "notifications"
    
    id = Column(Integer, primary_key=True, autoincrement=True, comment="순번 ID (AUTO_INCREMENT)")
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    type = Column(Enum(NotificationType), nullable=False)
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    status = Column(Enum(NotificationStatus), default=NotificationStatus.UNREAD)
    read_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=func.now())
    
    # 관계 설정
    user = relationship("User", backref="notifications")

