from sqlalchemy import Column, String, DateTime, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
from app.db.base import Base


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    oauth_id = Column(String(255), unique=True, index=True, nullable=False, comment="OAuth provider user ID")
    name = Column(String(255), nullable=False, comment="User display name")
    email = Column(String(255), unique=True, index=True, nullable=False, comment="User email address")
    avatar = Column(Text, nullable=True, comment="User avatar URL")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="Account creation timestamp")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="Last update timestamp")

    # Relationships
    canvases = relationship("Canvas", back_populates="owner")
    user_contents = relationship("UserContent", back_populates="user")

    def __repr__(self):
        return f"<User(id={self.id}, name='{self.name}', email='{self.email}')>"
