from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class TagBase(BaseModel):
    """标签基础模型"""
    name: str = Field(..., description="标签名称", min_length=1, max_length=100)
    description: Optional[str] = Field(None, description="标签描述")


class TagCreate(TagBase):
    """创建标签请求模型"""
    pass


class TagResponse(TagBase):
    """标签响应模型"""
    id: int = Field(..., description="标签ID")
    content_count: Optional[int] = Field(None, description="关联的公开内容数量")
    created_at: datetime = Field(..., description="创建时间")
    
    class Config:
        from_attributes = True


class PublishContentRequest(BaseModel):
    """发布内容请求模型"""
    public_title: str = Field(..., description="公开标题", min_length=1, max_length=255)
    public_description: Optional[str] = Field(None, description="公开描述")


class PublicContentResponse(BaseModel):
    """公开内容响应模型"""
    id: int = Field(..., description="内容ID")
    public_title: str = Field(..., description="公开标题")
    public_description: Optional[str] = Field(None, description="公开描述")
    preview: Optional[str] = Field(None, description="内容预览")
    author_name: Optional[str] = Field(None, description="作者名称")
    published_at: datetime = Field(..., description="发布时间")
    tags: List[TagResponse] = Field(default=[], description="标签列表")
    
    class Config:
        from_attributes = True


class ContentTagRequest(BaseModel):
    """内容标签请求模型"""
    tag_ids: List[int] = Field(..., description="标签ID列表")


class ContentTagResponse(BaseModel):
    """内容标签响应模型"""
    id: int = Field(..., description="标签ID")
    name: str = Field(..., description="标签名称")
    description: Optional[str] = Field(None, description="标签描述")
    confidence: float = Field(..., description="置信度")
    
    class Config:
        from_attributes = True


class TagGenerationRequest(BaseModel):
    """标签生成请求模型"""
    content: str = Field(..., description="文本内容", min_length=1)


class TagGenerationResponse(BaseModel):
    """标签生成响应模型"""
    success: bool = Field(..., description="是否成功")
    tag_ids: Optional[List[int]] = Field(None, description="生成的标签ID列表")
    existing_tags: Optional[List[str]] = Field(None, description="使用的现有标签")
    new_tags: Optional[List[str]] = Field(None, description="新创建的标签")
    error: Optional[str] = Field(None, description="错误信息")


class CommunityStatsResponse(BaseModel):
    """社群统计响应模型"""
    total_public_contents: int = Field(..., description="总公开内容数")
    total_tags: int = Field(..., description="总标签数")
    popular_tags: List[TagResponse] = Field(..., description="热门标签")
    recent_contents: List[PublicContentResponse] = Field(..., description="最新内容")


class PaginationResponse(BaseModel):
    """分页响应模型"""
    page: int = Field(..., description="当前页码")
    size: int = Field(..., description="每页大小")
    total: int = Field(..., description="总数量")
    has_next: bool = Field(..., description="是否有下一页")
    has_prev: bool = Field(..., description="是否有上一页")
