from typing import Optional
from datetime import datetime
from pydantic import BaseModel


class UserBase(BaseModel):
    name: str
    email: str
    avatar: Optional[str] = None


class UserCreate(UserBase):
    oauth_id: str


class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    avatar: Optional[str] = None


class User(BaseModel):
    id: int
    oauth_id: str
    name: str
    email: str
    avatar: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
