from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel
from uuid import UUID


class ArticleBase(BaseModel):
    """文章基础模型"""
    id: int
    content_type: str
    text_data: Optional[str] = None
    image_data: Optional[str] = None
    summary_title: Optional[str] = None
    summary_topic: Optional[str] = None
    summary_content: Optional[str] = None
    summary_status: Optional[str] = None

    created_at: datetime
    updated_at: datetime


class ArticleWithPermission(ArticleBase):
    """带权限信息的文章模型"""
    permission: str  # '0' = 查看, '1' = 编辑, '2' = 管理
    
    class Config:
        from_attributes = True


class ArticleListResponse(BaseModel):
    """文章列表响应模型"""
    articles: List[ArticleWithPermission]
    total: int
    
    class Config:
        from_attributes = True