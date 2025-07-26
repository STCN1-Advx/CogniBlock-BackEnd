from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, func
from app.models.content import Content
from app.models.user_content import UserContent
from app.models.content_tag import ContentTag
from app.models.tag import Tag
from app.schemas.canva import ContentCreate, ContentUpdate
from uuid import UUID
import hashlib
from datetime import datetime


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
        
        # 检查是否已存在用户内容关联，避免重复插入
        existing_relation = db.query(UserContent).filter(
            UserContent.user_id == user_id,
            UserContent.content_id == content.id
        ).first()
        
        if not existing_relation:
            # 创建用户内容关联，显式设置 permission 字段
            user_content = UserContent(
                user_id=user_id,
                content_id=content.id,
                permission="owner"  # 创建者默认为所有者
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

    # 笔记总结相关方法
    def generate_content_hash(self, content_text: str) -> str:
        """生成内容哈希值"""
        return hashlib.sha256(content_text.encode('utf-8')).hexdigest()

    def get_by_content_hash(self, db: Session, content_hash: str) -> Optional[Content]:
        """根据内容哈希获取内容（用于缓存查询）"""
        return db.query(Content).filter(Content.content_hash == content_hash).first()

    def update_summary(self, db: Session, content_id: int, summary_title: str, 
                      summary_topic: str, summary_content: str, content_hash: str = None) -> Optional[Content]:
        """更新内容的总结信息"""
        content = self.get(db, content_id)
        if not content:
            return None
        
        content.summary_title = summary_title
        content.summary_topic = summary_topic
        content.summary_content = summary_content
        if content_hash:
            content.content_hash = content_hash
        
        db.add(content)
        db.commit()
        db.refresh(content)
        return content

    def get_contents_with_summary(self, db: Session, user_id: UUID, skip: int = 0, limit: int = 100) -> List[Content]:
        """获取用户有总结的内容"""
        return db.query(Content).join(UserContent).filter(
            UserContent.user_id == user_id,
            Content.summary_content.isnot(None)
        ).offset(skip).limit(limit).all()

    def search_summary_content(self, db: Session, user_id: UUID, query: str, skip: int = 0, limit: int = 100) -> List[Content]:
        """搜索用户的总结内容"""
        return db.query(Content).join(UserContent).filter(
            UserContent.user_id == user_id,
            or_(
                Content.summary_title.ilike(f"%{query}%"),
                Content.summary_topic.ilike(f"%{query}%"),
                Content.summary_content.ilike(f"%{query}%")
            )
        ).offset(skip).limit(limit).all()

    def get_similar_contents_by_hash(self, db: Session, content_hashes: List[str], user_id: UUID = None) -> List[Content]:
        """根据内容哈希列表获取相似内容（用于批量缓存查询）"""
        query = db.query(Content).filter(Content.content_hash.in_(content_hashes))
        
        if user_id:
            query = query.join(UserContent).filter(UserContent.user_id == user_id)
        
        return query.all()

    def publish_content(self, db: Session, content_id: int, public_title: str,
                       public_description: str = None) -> Optional[Content]:
        """将内容设为公开"""
        content_obj = self.get(db, content_id)
        if not content_obj:
            return None

        content_obj.is_public = True
        content_obj.public_title = public_title
        content_obj.public_description = public_description
        content_obj.published_at = datetime.now()

        db.add(content_obj)
        db.commit()
        db.refresh(content_obj)
        return content_obj

    def unpublish_content(self, db: Session, content_id: int) -> Optional[Content]:
        """取消内容公开"""
        content_obj = self.get(db, content_id)
        if not content_obj:
            return None

        content_obj.is_public = False
        content_obj.published_at = None

        db.add(content_obj)
        db.commit()
        db.refresh(content_obj)
        return content_obj

    def get_public_contents(self, db: Session, skip: int = 0, limit: int = 100) -> List[Content]:
        """获取所有公开内容"""
        return db.query(Content).filter(
            Content.is_public == True
        ).order_by(Content.published_at.desc()).offset(skip).limit(limit).all()

    def get_user_public_contents(self, db: Session, user_id: UUID, skip: int = 0, limit: int = 100) -> List[Content]:
        """获取用户的公开内容"""
        return db.query(Content).join(UserContent).filter(
            UserContent.user_id == user_id,
            Content.is_public == True
        ).order_by(Content.published_at.desc()).offset(skip).limit(limit).all()

    def search_public_contents(self, db: Session, query: str, skip: int = 0, limit: int = 100) -> List[Content]:
        """搜索公开内容"""
        return db.query(Content).filter(
            Content.is_public == True,
            or_(
                Content.public_title.ilike(f"%{query}%"),
                Content.public_description.ilike(f"%{query}%"),
                Content.summary_content.ilike(f"%{query}%")
            )
        ).order_by(Content.published_at.desc()).offset(skip).limit(limit).all()

    def check_public_access(self, db: Session, content_id: int) -> bool:
        """检查内容是否公开可访问"""
        content_obj = self.get(db, content_id)
        return content_obj and content_obj.is_public

    def get_content_with_tags(self, db: Session, content_id: int) -> Optional[dict]:
        """获取内容及其标签信息"""
        content_obj = self.get(db, content_id)
        if not content_obj:
            return None

        # 获取标签
        tags = db.query(Tag).join(ContentTag).filter(
            ContentTag.content_id == content_id
        ).all()

        return {
            "content": content_obj,
            "tags": [{"id": tag.id, "name": tag.name, "description": tag.description} for tag in tags]
        }


content = CRUDContent()