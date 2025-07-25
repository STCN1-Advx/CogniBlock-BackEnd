from sqlalchemy import Column, Integer, Float, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.base import Base


class Card(Base):
    __tablename__ = "cards"

    id = Column(Integer, primary_key=True, index=True)
    canvas_id = Column(Integer, ForeignKey("canvases.id"), nullable=False)
    content_id = Column(Integer, ForeignKey("contents.id"), nullable=False)
    position_x = Column(Float, nullable=False)
    position_y = Column(Float, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    canvas = relationship("Canvas", back_populates="cards")
    content = relationship("Content", back_populates="cards")

    def __repr__(self):
        return f"<Card(id={self.id}, canvas_id={self.canvas_id}, content_id={self.content_id}, position=({self.position_x}, {self.position_y}))>"