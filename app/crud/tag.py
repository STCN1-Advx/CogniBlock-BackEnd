from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.tag import Tag
from app.models.content_tag import ContentTag
from app.models.content import Content


class CRUDTag:
    def get(self, db: Session, id: int) -> Optional[Tag]:
        """根据ID获取标签"""
        return db.query(Tag).filter(Tag.id == id).first()

    def get_by_name(self, db: Session, name: str) -> Optional[Tag]:
        """根据名称获取标签"""
        return db.query(Tag).filter(Tag.name == name).first()

    def get_multi(self, db: Session, skip: int = 0, limit: int = 100) -> List[Tag]:
        """获取多个标签"""
        return db.query(Tag).offset(skip).limit(limit).all()

    def create(self, db: Session, name: str, description: str = None) -> Tag:
        """创建新标签"""
        db_obj = Tag(
            name=name,
            description=description
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def get_or_create(self, db: Session, name: str, description: str = None) -> Tag:
        """获取或创建标签"""
        tag = self.get_by_name(db, name)
        if not tag:
            tag = self.create(db, name, description)
        return tag

    def update(self, db: Session, db_obj: Tag, name: str = None, description: str = None) -> Tag:
        """更新标签"""
        if name is not None:
            db_obj.name = name
        if description is not None:
            db_obj.description = description
        
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def delete(self, db: Session, id: int) -> Optional[Tag]:
        """删除标签"""
        obj = db.query(Tag).get(id)
        if obj:
            db.delete(obj)
            db.commit()
        return obj

    def get_tags_with_content_count(self, db: Session, skip: int = 0, limit: int = 100) -> List[dict]:
        """获取标签及其公开内容数量"""
        result = db.query(
            Tag.id,
            Tag.name,
            Tag.description,
            func.count(ContentTag.content_id).label('content_count')
        ).outerjoin(ContentTag).outerjoin(Content).filter(
            Content.is_public == True
        ).group_by(Tag.id, Tag.name, Tag.description).offset(skip).limit(limit).all()
        
        return [
            {
                "id": row.id,
                "name": row.name,
                "description": row.description,
                "content_count": row.content_count
            }
            for row in result
        ]

    def search_tags(self, db: Session, query: str, skip: int = 0, limit: int = 100) -> List[Tag]:
        """搜索标签"""
        return db.query(Tag).filter(
            Tag.name.ilike(f"%{query}%")
        ).offset(skip).limit(limit).all()

    def get_popular_tags(self, db: Session, limit: int = 20) -> List[dict]:
        """获取热门标签（按公开内容数量排序）"""
        result = db.query(
            Tag.id,
            Tag.name,
            Tag.description,
            func.count(ContentTag.content_id).label('content_count')
        ).join(ContentTag).join(Content).filter(
            Content.is_public == True
        ).group_by(Tag.id, Tag.name, Tag.description).order_by(
            func.count(ContentTag.content_id).desc()
        ).limit(limit).all()
        
        return [
            {
                "id": row.id,
                "name": row.name,
                "description": row.description,
                "content_count": row.content_count
            }
            for row in result
        ]


# 创建全局实例
tag = CRUDTag()
