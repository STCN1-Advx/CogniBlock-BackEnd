from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from uuid import UUID
from app.models.content import Content
from app.models.user_content import UserContent
from datetime import datetime


class CRUDKnowledgeBase:
    """
    知识库统计CRUD操作类
    """
    
    def get_user_knowledge_base_stats(self, db: Session, user_id: UUID) -> dict:
        """
        获取用户知识库统计信息
        
        Args:
            db: 数据库会话
            user_id: 用户ID
            
        Returns:
            包含统计信息的字典
        """
        # 统计用户有权限的知识库数量（有knowledge_title的内容）
        knowledge_base_count = (
            db.query(Content)
            .join(UserContent, Content.id == UserContent.content_id)
            .filter(
                UserContent.user_id == user_id,
                Content.knowledge_title.isnot(None),
                Content.knowledge_title != ''
            )
            .count()
        )
        
        # 统计用户有权限的总内容数
        total_content_count = (
            db.query(Content)
            .join(UserContent, Content.id == UserContent.content_id)
            .filter(UserContent.user_id == user_id)
            .count()
        )
        
        # 获取最近一次更新任何资产的时间
        last_updated_result = (
            db.query(func.max(Content.updated_at))
            .join(UserContent, Content.id == UserContent.content_id)
            .filter(UserContent.user_id == user_id)
            .scalar()
        )
        
        return {
            'knowledge_base_count': knowledge_base_count,
            'total_content_count': total_content_count,
            'last_updated_at': last_updated_result,
            'user_id': str(user_id)
        }
    
    def get_user_knowledge_base_count_by_permission(self, db: Session, user_id: UUID, permission: str) -> int:
        """
        根据权限等级统计用户知识库数量
        
        Args:
            db: 数据库会话
            user_id: 用户ID
            permission: 权限等级 ('0', '1', '2')
            
        Returns:
            知识库数量
        """
        return (
            db.query(Content)
            .join(UserContent, Content.id == UserContent.content_id)
            .filter(
                UserContent.user_id == user_id,
                UserContent.permission == permission,
                Content.knowledge_title.isnot(None),
                Content.knowledge_title != ''
            )
            .count()
        )
    
    def get_user_recent_knowledge_bases(self, db: Session, user_id: UUID, limit: int = 5) -> list:
        """
        获取用户最近更新的知识库记录
        
        Args:
            db: 数据库会话
            user_id: 用户ID
            limit: 返回记录数限制
            
        Returns:
            最近更新的知识库记录列表
        """
        results = (
            db.query(Content)
            .join(UserContent, Content.id == UserContent.content_id)
            .filter(
                UserContent.user_id == user_id,
                Content.knowledge_title.isnot(None),
                Content.knowledge_title != ''
            )
            .order_by(desc(Content.updated_at))
            .limit(limit)
            .all()
        )
        
        return [
            {
                'id': content.id,
                'knowledge_title': content.knowledge_title,
                'knowledge_date': content.knowledge_date,
                'knowledge_preview': content.knowledge_preview,
                'updated_at': content.updated_at,
                'created_at': content.created_at
            }
            for content in results
        ]


# 创建实例
knowledge_base = CRUDKnowledgeBase()