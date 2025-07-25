from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.base import Base


class UserContent(Base):
    __tablename__ = "user_contents"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    content_id = Column(Integer, ForeignKey("contents.id"), nullable=False)
    permission = Column(String(20), default="read", nullable=False)  # 'read', 'write', 'owner'
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user = relationship("User", back_populates="user_contents")
    content = relationship("Content", back_populates="user_contents")

    # Unique constraint to prevent duplicate user-content relationships
    __table_args__ = (
        UniqueConstraint('user_id', 'content_id', name='uq_user_content'),
    )

    def __repr__(self):
        return f"<UserContent(id={self.id}, user_id={self.user_id}, content_id={self.content_id}, permission='{self.permission}')>"