from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc, case
from uuid import UUID
from app.models.content import Content
from app.models.user_content import UserContent


class CRUDArticle:
    """文章CRUD操作类"""
    
    def get_user_articles_with_permission(self, db: Session, user_id: UUID, skip: int = 0, limit: int = 100) -> List[dict]:
        """
        获取用户有权限的所有文档，按权限等级排序
        
        Args:
            db: 数据库会话
            user_id: 用户ID
            skip: 跳过的记录数
            limit: 限制返回的记录数
            
        Returns:
            包含文档和权限信息的字典列表
        """
        # 权限映射：将字符串权限转换为数字进行排序
        # '2' = 管理, '1' = 编辑, '0' = 查看
        permission_order = case(
            (UserContent.permission == '2', 2),
            (UserContent.permission == '1', 1),
            (UserContent.permission == '0', 0),
            else_=0
        )
        
        # 查询用户有权限的所有内容，按权限等级降序排序
        query = (
            db.query(Content, UserContent.permission)
            .join(UserContent, Content.id == UserContent.content_id)
            .filter(UserContent.user_id == user_id)
            .order_by(desc(permission_order), desc(Content.created_at))
            .offset(skip)
            .limit(limit)
        )
        
        results = query.all()
        
        # 转换为字典格式
        articles = []
        for content, permission in results:
            article_dict = {
                'id': content.id,
                'content_type': content.content_type,
                'text_data': content.text_data,
                'image_data': content.image_data,
                'summary_title': content.summary_title,
                'summary_topic': content.summary_topic,
                'summary_content': content.summary_content,
                'summary_status': content.summary_status,
                'filename': content.filename,
                'file_size': content.file_size,
                'created_at': content.created_at,
                'updated_at': content.updated_at,
                'permission': permission
            }
            articles.append(article_dict)
        
        return articles
    
    def count_user_articles(self, db: Session, user_id: UUID) -> int:
        """
        统计用户有权限的文档总数
        
        Args:
            db: 数据库会话
            user_id: 用户ID
            
        Returns:
            文档总数
        """
        return (
            db.query(Content)
            .join(UserContent, Content.id == UserContent.content_id)
            .filter(UserContent.user_id == user_id)
            .count()
        )
    
    def get_user_articles_by_permission(self, db: Session, user_id: UUID, permission: str, 
                                      skip: int = 0, limit: int = 100) -> List[dict]:
        """
        根据权限等级获取用户文档
        
        Args:
            db: 数据库会话
            user_id: 用户ID
            permission: 权限等级 ('0', '1', '2')
            skip: 跳过的记录数
            limit: 限制返回的记录数
            
        Returns:
            包含文档和权限信息的字典列表
        """
        query = (
            db.query(Content, UserContent.permission)
            .join(UserContent, Content.id == UserContent.content_id)
            .filter(
                UserContent.user_id == user_id,
                UserContent.permission == permission
            )
            .order_by(desc(Content.created_at))
            .offset(skip)
            .limit(limit)
        )
        
        results = query.all()
        
        # 转换为字典格式
        articles = []
        for content, permission in results:
            article_dict = {
                'id': content.id,
                'content_type': content.content_type,
                'text_data': content.text_data,
                'image_data': content.image_data,
                'summary_title': content.summary_title,
                'summary_topic': content.summary_topic,
                'summary_content': content.summary_content,
                'summary_status': content.summary_status,
                'filename': content.filename,
                'file_size': content.file_size,
                'created_at': content.created_at,
                'updated_at': content.updated_at,
                'permission': permission
            }
            articles.append(article_dict)
        
        return articles


article = CRUDArticle()