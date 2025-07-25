from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.base import Base


class Content(Base):
    __tablename__ = "contents"

    id = Column(Integer, primary_key=True, index=True)
    content_type = Column(String(50), nullable=False)  # 'image', 'text'
    image_data = Column(Text, nullable=True)  # Base64 编码的图片
    text_data = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    cards = relationship("Card", back_populates="content")
    user_contents = relationship("UserContent", back_populates="content", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Content(id={self.id}, content_type='{self.content_type}')>"