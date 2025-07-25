from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.models.content import Content
from app.models.user_content import UserContent
from app.schemas.canva import ContentCreate, ContentUpdate
from uuid import UUID


class CRUDContent:
    def get(self, db: Session, id: int) -> Optional[Content]:
        """根据ID获取内容"""
        return db.query(Content).filter(Content.id == id).first()

    def get_multi(self, db: Session, skip: int = 0, limit: int = 100) -> List[Content]:
        """获取多个内容"""
        return db.query(Content).offset(skip).limit(limit).all()

    def get_by_type(self, db: Session, content_type: str, skip: int = 0, limit: int = 100) -> List[Content]:
        """根据类型获取内容"""
        return db.query(Content).filter(Content.content_type == content_type).offset(skip).limit(limit).all()

    def create(self, db: Session, obj_in: ContentCreate) -> Content:
        """创建新内容"""
        db_obj = Content(
            content_type=obj_in.content_type,
            image_data=obj_in.image_data,
            text_data=obj_in.text_data
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update(self, db: Session, db_obj: Content, obj_in: ContentUpdate) -> Content:
        """更新内容"""
        if hasattr(obj_in, 'dict'):
            update_data = obj_in.dict(exclude_unset=True)
        else:
            update_data = obj_in

        for field, value in update_data.items():
            if hasattr(db_obj, field) and value is not None:
                setattr(db_obj, field, value)
        
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def delete(self, db: Session, id: int) -> Optional[Content]:
        """删除内容"""
        obj = db.query(Content).get(id)
        if obj:
            db.delete(obj)
            db.commit()
        return obj

    def search_text_content(self, db: Session, query: str, skip: int = 0, limit: int = 100) -> List[Content]:
        """搜索文本内容"""
        return db.query(Content).filter(
            Content.content_type == "text",
            Content.text_data.ilike(f"%{query}%")
        ).offset(skip).limit(limit).all()

    def get_user_contents(self, db: Session, user_id: UUID, skip: int = 0, limit: int = 100) -> List[Content]:
        """获取用户的内容"""
        return db.query(Content).join(UserContent).filter(
            UserContent.user_id == user_id
        ).offset(skip).limit(limit).all()

    def get_user_content_by_type(self, db: Session, user_id: UUID, content_type: str, skip: int = 0, limit: int = 100) -> List[Content]:
        """获取用户特定类型的内容"""
        return db.query(Content).join(UserContent).filter(
            UserContent.user_id == user_id,
            Content.content_type == content_type
        ).offset(skip).limit(limit).all()

    def create_with_user_relation(self, db: Session, obj_in: ContentCreate, user_id: UUID) -> Content:
        """创建内容并建立用户关联"""
        # 创建内容
        content = self.create(db, obj_in)
        
        # 创建用户内容关联
        user_content = UserContent(
            user_id=user_id,
            content_id=content.id
        )
        db.add(user_content)
        db.commit()
        db.refresh(content)
        return content

    def check_user_access(self, db: Session, content_id: int, user_id: UUID) -> bool:
        """检查用户是否有权访问该内容"""
        user_content = db.query(UserContent).filter(
            UserContent.content_id == content_id,
            UserContent.user_id == user_id
        ).first()
        return user_content is not None

    def get_content_usage_count(self, db: Session, content_id: int) -> int:
        """获取内容被使用的次数（在多少个卡片中）"""
        from app.models.card import Card
        return db.query(Card).filter(Card.content_id == content_id).count()

    def get_unused_contents(self, db: Session, user_id: UUID) -> List[Content]:
        """获取用户未使用的内容"""
        from app.models.card import Card
        
        # 获取用户的所有内容ID
        user_content_ids = db.query(UserContent.content_id).filter(
            UserContent.user_id == user_id
        ).subquery()
        
        # 获取被使用的内容ID
        used_content_ids = db.query(Card.content_id).distinct().subquery()
        
        # 获取未使用的内容
        return db.query(Content).filter(
            Content.id.in_(user_content_ids),
            ~Content.id.in_(used_content_ids)
        ).all()

    def bulk_create(self, db: Session, contents_data: List[ContentCreate], user_id: UUID) -> List[Content]:
        """批量创建内容"""
        created_contents = []
        for content_data in contents_data:
            content = self.create_with_user_relation(db, content_data, user_id)
            created_contents.append(content)
        return created_contents


content = CRUDContent()