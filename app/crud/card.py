from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_
from app.models.card import Card
from app.schemas.canva import CardUpdateRequest


class CRUDCard:
    def get(self, db: Session, id: int) -> Optional[Card]:
        """根据ID获取卡片"""
        return db.query(Card).filter(Card.id == id).first()

    def get_by_canvas(self, db: Session, canvas_id: int) -> List[Card]:
        """获取画布中的所有卡片"""
        return db.query(Card).filter(Card.canvas_id == canvas_id).all()

    def get_by_canvas_and_id(self, db: Session, canvas_id: int, card_id: int) -> Optional[Card]:
        """获取画布中的特定卡片"""
        return db.query(Card).filter(
            and_(Card.id == card_id, Card.canvas_id == canvas_id)
        ).first()

    def create(self, db: Session, canvas_id: int, content_id: int, position_x: float, position_y: float) -> Card:
        """创建新卡片"""
        db_obj = Card(
            canvas_id=canvas_id,
            content_id=content_id,
            position_x=position_x,
            position_y=position_y
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update_position(self, db: Session, db_obj: Card, position_x: float, position_y: float) -> Card:
        """更新卡片位置"""
        db_obj.position_x = position_x
        db_obj.position_y = position_y
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update(self, db: Session, db_obj: Card, obj_in: CardUpdateRequest) -> Card:
        """更新卡片"""
        if obj_in.position:
            db_obj.position_x = obj_in.position.x
            db_obj.position_y = obj_in.position.y
        
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def delete(self, db: Session, id: int) -> Optional[Card]:
        """删除卡片"""
        obj = db.query(Card).get(id)
        if obj:
            db.delete(obj)
            db.commit()
        return obj

    def delete_by_canvas(self, db: Session, canvas_id: int) -> int:
        """删除画布中的所有卡片"""
        count = db.query(Card).filter(Card.canvas_id == canvas_id).count()
        db.query(Card).filter(Card.canvas_id == canvas_id).delete()
        db.commit()
        return count

    def bulk_create(self, db: Session, cards_data: List[dict]) -> List[Card]:
        """批量创建卡片"""
        db_objs = []
        for card_data in cards_data:
            db_obj = Card(**card_data)
            db_objs.append(db_obj)
        
        db.add_all(db_objs)
        db.commit()
        for db_obj in db_objs:
            db.refresh(db_obj)
        return db_objs

    def bulk_update_positions(self, db: Session, updates: List[dict]) -> List[Card]:
        """批量更新卡片位置"""
        updated_cards = []
        for update in updates:
            card = db.query(Card).filter(Card.id == update['card_id']).first()
            if card:
                card.position_x = update['position_x']
                card.position_y = update['position_y']
                updated_cards.append(card)
        
        db.commit()
        for card in updated_cards:
            db.refresh(card)
        return updated_cards

    def check_canvas_ownership(self, db: Session, card_id: int, canvas_id: int) -> bool:
        """检查卡片是否属于指定画布"""
        card = db.query(Card).filter(
            and_(Card.id == card_id, Card.canvas_id == canvas_id)
        ).first()
        return card is not None

    def get_cards_by_content(self, db: Session, content_id: int) -> List[Card]:
        """获取使用特定内容的所有卡片"""
        return db.query(Card).filter(Card.content_id == content_id).all()


card = CRUDCard()