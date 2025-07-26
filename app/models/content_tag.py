from sqlalchemy import Column, Integer, ForeignKey, Float, DateTime, UniqueConstraint
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.base import Base


class ContentTag(Base):
    __tablename__ = "content_tags"

    id = Column(Integer, primary_key=True, index=True)
    content_id = Column(Integer, ForeignKey("contents.id"), nullable=False)
    tag_id = Column(Integer, ForeignKey("tags.id"), nullable=False)
    confidence = Column(Float, default=1.0, nullable=False)  # AI标签的置信度
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    content = relationship("Content", back_populates="content_tags")
    tag = relationship("Tag", back_populates="content_tags")

    # Unique constraint to prevent duplicate content-tag relationships
    __table_args__ = (
        UniqueConstraint('content_id', 'tag_id', name='uq_content_tag'),
    )

    def __repr__(self):
        return f"<ContentTag(content_id={self.content_id}, tag_id={self.tag_id}, confidence={self.confidence})>"
