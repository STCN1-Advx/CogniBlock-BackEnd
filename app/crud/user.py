from typing import Optional
from sqlalchemy.orm import Session
from uuid import UUID
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate


class CRUDUser:
    def get(self, db: Session, id: UUID) -> Optional[User]:
        """Get user by ID"""
        return db.query(User).filter(User.id == id).first()

    def get_by_email(self, db: Session, email: str) -> Optional[User]:
        """Get user by email"""
        return db.query(User).filter(User.email == email).first()

    def get_by_oauth_id(self, db: Session, oauth_id: str) -> Optional[User]:
        """Get user by OAuth ID"""
        return db.query(User).filter(User.oauth_id == oauth_id).first()

    def create(self, db: Session, obj_in: UserCreate) -> User:
        """Create new user"""
        db_obj = User(
            oauth_id=obj_in.oauth_id,
            name=obj_in.name,
            email=obj_in.email,
            avatar=obj_in.avatar
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update(self, db: Session, db_obj: User, obj_in) -> User:
        """Update user"""
        if hasattr(obj_in, 'dict'):
            update_data = obj_in.dict(exclude_unset=True)
        else:
            update_data = obj_in

        for field, value in update_data.items():
            if hasattr(db_obj, field):
                setattr(db_obj, field, value)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def delete(self, db: Session, id: UUID) -> Optional[User]:
        """Delete user"""
        obj = db.query(User).get(id)
        if obj:
            db.delete(obj)
            db.commit()
        return obj


user = CRUDUser()
