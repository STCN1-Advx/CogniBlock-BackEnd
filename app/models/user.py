from sqlalchemy import Column, Integer, String, DateTime, Text
from sqlalchemy.sql import func
from app.db.base import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    oauth_id = Column(String(255), unique=True, index=True, nullable=False, comment="OAuth provider user ID")
    name = Column(String(255), nullable=False, comment="User display name")
    email = Column(String(255), unique=True, index=True, nullable=False, comment="User email address")
    avatar = Column(Text, nullable=True, comment="User avatar URL")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="Account creation timestamp")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="Last update timestamp")

    def __repr__(self):
        return f"<User(id={self.id}, name='{self.name}', email='{self.email}')>"
