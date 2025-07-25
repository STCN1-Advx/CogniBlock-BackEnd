from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_
from uuid import UUID
from app.models.canvas import Canvas
from app.models.card import Card
from app.schemas.canva import CanvasCreate, CanvasUpdate


class CRUDCanvas:
    def get(self, db: Session, id: int) -> Optional[Canvas]:
        """根据ID获取画布"""
        return db.query(Canvas).filter(Canvas.id == id).first()

    def get_by_owner(self, db: Session, owner_id: UUID, skip: int = 0, limit: int = 100) -> List[Canvas]:
        """获取用户的所有画布"""
        return db.query(Canvas).filter(Canvas.owner_id == owner_id).offset(skip).limit(limit).all()

    def get_by_owner_and_id(self, db: Session, owner_id: UUID, canvas_id: int) -> Optional[Canvas]:
        """获取用户的特定画布"""
        return db.query(Canvas).filter(
            and_(Canvas.id == canvas_id, Canvas.owner_id == owner_id)
        ).first()

    def create(self, db: Session, obj_in: CanvasCreate, owner_id: UUID) -> Canvas:
        """创建新画布"""
        db_obj = Canvas(
            owner_id=owner_id,
            name=obj_in.name
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update(self, db: Session, db_obj: Canvas, obj_in: CanvasUpdate) -> Canvas:
        """更新画布"""
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

    def delete(self, db: Session, id: int) -> Optional[Canvas]:
        """删除画布"""
        obj = db.query(Canvas).get(id)
        if obj:
            db.delete(obj)
            db.commit()
        return obj

    def get_with_cards(self, db: Session, canvas_id: int, owner_id: UUID) -> Optional[Canvas]:
        """获取画布及其所有卡片"""
        return db.query(Canvas).filter(
            and_(Canvas.id == canvas_id, Canvas.owner_id == owner_id)
        ).first()

    def get_cards_count(self, db: Session, canvas_id: int) -> int:
        """获取画布中的卡片数量"""
        return db.query(Card).filter(Card.canvas_id == canvas_id).count()

    def check_ownership(self, db: Session, canvas_id: int, owner_id: UUID) -> bool:
        """检查用户是否拥有该画布"""
        canvas = db.query(Canvas).filter(
            and_(Canvas.id == canvas_id, Canvas.owner_id == owner_id)
        ).first()
        return canvas is not None


canvas = CRUDCanvas()