from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_
from app.models.content_tag import ContentTag
from app.models.tag import Tag
from app.models.content import Content


class CRUDContentTag:
    def get(self, db: Session, content_id: int, tag_id: int) -> Optional[ContentTag]:
        """根据content_id和tag_id获取关联"""
        return db.query(ContentTag).filter(
            and_(ContentTag.content_id == content_id, ContentTag.tag_id == tag_id)
        ).first()

    def create(self, db: Session, content_id: int, tag_id: int, confidence: float = 1.0) -> ContentTag:
        """创建内容标签关联"""
        db_obj = ContentTag(
            content_id=content_id,
            tag_id=tag_id,
            confidence=confidence
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def get_or_create(self, db: Session, content_id: int, tag_id: int, confidence: float = 1.0) -> ContentTag:
        """获取或创建内容标签关联"""
        content_tag = self.get(db, content_id, tag_id)
        if not content_tag:
            content_tag = self.create(db, content_id, tag_id, confidence)
        return content_tag

    def delete(self, db: Session, content_id: int, tag_id: int) -> Optional[ContentTag]:
        """删除内容标签关联"""
        obj = self.get(db, content_id, tag_id)
        if obj:
            db.delete(obj)
            db.commit()
        return obj

    def get_content_tags(self, db: Session, content_id: int) -> List[Tag]:
        """获取内容的所有标签"""
        return db.query(Tag).join(ContentTag).filter(
            ContentTag.content_id == content_id
        ).all()

    def get_tag_contents(self, db: Session, tag_id: int, public_only: bool = True, 
                        skip: int = 0, limit: int = 100) -> List[Content]:
        """获取标签下的所有内容"""
        query = db.query(Content).join(ContentTag).filter(
            ContentTag.tag_id == tag_id
        )
        
        if public_only:
            query = query.filter(Content.is_public == True)
        
        return query.offset(skip).limit(limit).all()

    def bulk_create_tags_for_content(self, db: Session, content_id: int, 
                                   tag_ids: List[int], confidence: float = 1.0) -> List[ContentTag]:
        """为内容批量创建标签关联"""
        content_tags = []
        for tag_id in tag_ids:
            content_tag = self.get_or_create(db, content_id, tag_id, confidence)
            content_tags.append(content_tag)
        return content_tags

    def remove_all_content_tags(self, db: Session, content_id: int) -> int:
        """移除内容的所有标签"""
        count = db.query(ContentTag).filter(ContentTag.content_id == content_id).count()
        db.query(ContentTag).filter(ContentTag.content_id == content_id).delete()
        db.commit()
        return count

    def update_content_tags(self, db: Session, content_id: int, tag_ids: List[int], 
                           confidence: float = 1.0) -> List[ContentTag]:
        """更新内容的标签（先删除所有，再添加新的）"""
        # 删除现有标签
        self.remove_all_content_tags(db, content_id)
        
        # 添加新标签
        return self.bulk_create_tags_for_content(db, content_id, tag_ids, confidence)

    def get_content_tags_with_confidence(self, db: Session, content_id: int) -> List[dict]:
        """获取内容的标签及置信度"""
        result = db.query(Tag, ContentTag.confidence).join(ContentTag).filter(
            ContentTag.content_id == content_id
        ).all()
        
        return [
            {
                "id": tag.id,
                "name": tag.name,
                "description": tag.description,
                "confidence": confidence
            }
            for tag, confidence in result
        ]


# 创建全局实例
content_tag = CRUDContentTag()
