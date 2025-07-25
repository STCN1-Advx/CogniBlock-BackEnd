from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.base import Base


class Canvas(Base):
    __tablename__ = "canvases"

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    name = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    owner = relationship("User", back_populates="canvases")
    cards = relationship("Card", back_populates="canvas", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Canvas(id={self.id}, name='{self.name}', owner_id={self.owner_id})>"