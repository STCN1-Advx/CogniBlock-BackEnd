from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID

from app.db.session import get_db
from app.crud.tag import tag as tag_crud
from app.crud.content_tag import content_tag as content_tag_crud
from app.crud.content import content as content_crud
from app.models.user import User
from app.api.v2.auth import get_current_user, get_current_user_optional
from app.schemas.community import (
    TagResponse, PublicContentResponse, CommunityStatsResponse,
    PaginationResponse, TagGenerationRequest, TagGenerationResponse
)
from app.services.tag_generation_service import tag_generation_service

router = APIRouter()


@router.get("/tags", response_model=List[TagResponse])
async def get_tags(
    skip: int = Query(0, ge=0, description="跳过的数量"),
    limit: int = Query(20, ge=1, le=100, description="返回的数量"),
    search: Optional[str] = Query(None, description="搜索关键词"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取标签列表
    
    返回所有标签及其关联的公开内容数量
    """
    try:
        if search:
            # 搜索标签
            tags = tag_crud.search_tags(db, search, skip, limit)
            # 为搜索结果添加内容数量
            result = []
            for tag in tags:
                tag_data = tag_crud.get_tags_with_content_count(db, 0, 1000)
                content_count = next((t["content_count"] for t in tag_data if t["id"] == tag.id), 0)
                result.append(TagResponse(
                    id=tag.id,
                    name=tag.name,
                    description=tag.description,
                    content_count=content_count,
                    created_at=tag.created_at
                ))
            return result
        else:
            # 获取标签及内容数量
            tags_data = tag_crud.get_tags_with_content_count(db, skip, limit)
            return [
                TagResponse(
                    id=tag["id"],
                    name=tag["name"],
                    description=tag["description"],
                    content_count=tag["content_count"],
                    created_at=tag_crud.get(db, tag["id"]).created_at
                )
                for tag in tags_data
            ]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取标签列表失败: {str(e)}"
        )


@router.get("/tags/popular", response_model=List[TagResponse])
async def get_popular_tags(
    limit: int = Query(10, ge=1, le=50, description="返回的数量"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取热门标签
    
    按公开内容数量排序返回热门标签
    """
    try:
        tags_data = tag_crud.get_popular_tags(db, limit)
        return [
            TagResponse(
                id=tag["id"],
                name=tag["name"],
                description=tag["description"],
                content_count=tag["content_count"],
                created_at=tag_crud.get(db, tag["id"]).created_at
            )
            for tag in tags_data
        ]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取热门标签失败: {str(e)}"
        )


@router.get("/tags/{tag_id}/contents", response_model=List[PublicContentResponse])
async def get_tag_contents(
    tag_id: int,
    skip: int = Query(0, ge=0, description="跳过的数量"),
    limit: int = Query(20, ge=1, le=100, description="返回的数量"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    根据标签获取公开内容
    
    返回指定标签下的所有公开内容
    """
    try:
        # 检查标签是否存在
        tag = tag_crud.get(db, tag_id)
        if not tag:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="标签不存在"
            )
        
        # 获取标签下的公开内容
        contents = content_tag_crud.get_tag_contents(db, tag_id, public_only=True, skip=skip, limit=limit)
        
        result = []
        for content in contents:
            # 获取作者信息
            author_name = None
            if content.user_contents:
                author_name = content.user_contents[0].user.name
            
            # 获取内容标签
            content_tags = content_tag_crud.get_content_tags(db, content.id)
            tags = [
                TagResponse(
                    id=tag.id,
                    name=tag.name,
                    description=tag.description,
                    created_at=tag.created_at
                )
                for tag in content_tags
            ]
            
            # 生成预览内容
            preview = None
            if content.summary_content:
                preview = content.summary_content[:200] + "..." if len(content.summary_content) > 200 else content.summary_content
            elif content.knowledge_preview:
                preview = content.knowledge_preview[:200] + "..." if len(content.knowledge_preview) > 200 else content.knowledge_preview
            
            result.append(PublicContentResponse(
                id=content.id,
                public_title=content.public_title,
                public_description=content.public_description,
                preview=preview,
                author_name=author_name,
                published_at=content.published_at,
                tags=tags
            ))
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取标签内容失败: {str(e)}"
        )


@router.get("/contents", response_model=List[PublicContentResponse])
async def get_public_contents(
    skip: int = Query(0, ge=0, description="跳过的数量"),
    limit: int = Query(20, ge=1, le=100, description="返回的数量"),
    search: Optional[str] = Query(None, description="搜索关键词"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取公开内容列表
    
    返回所有公开的内容，支持搜索
    """
    try:
        if search:
            contents = content_crud.search_public_contents(db, search, skip, limit)
        else:
            contents = content_crud.get_public_contents(db, skip, limit)
        
        result = []
        for content in contents:
            # 获取作者信息
            author_name = None
            if content.user_contents:
                author_name = content.user_contents[0].user.name
            
            # 获取内容标签
            content_tags = content_tag_crud.get_content_tags(db, content.id)
            tags = [
                TagResponse(
                    id=tag.id,
                    name=tag.name,
                    description=tag.description,
                    created_at=tag.created_at
                )
                for tag in content_tags
            ]
            
            # 生成预览内容
            preview = None
            if content.summary_content:
                preview = content.summary_content[:200] + "..." if len(content.summary_content) > 200 else content.summary_content
            elif content.knowledge_preview:
                preview = content.knowledge_preview[:200] + "..." if len(content.knowledge_preview) > 200 else content.knowledge_preview
            
            result.append(PublicContentResponse(
                id=content.id,
                public_title=content.public_title,
                public_description=content.public_description,
                preview=preview,
                author_name=author_name,
                published_at=content.published_at,
                tags=tags
            ))
        
        return result
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取公开内容失败: {str(e)}"
        )


@router.get("/contents/{content_id}")
async def get_public_content_detail(
    content_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    获取公开内容详情
    
    无需登录即可访问公开内容的详细信息
    """
    try:
        # 检查内容是否公开
        if not content_crud.check_public_access(db, content_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="内容不存在或未公开"
            )
        
        content = content_crud.get(db, content_id)
        if not content:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="内容不存在"
            )
        
        # 获取作者信息
        author_name = None
        if content.user_contents:
            author_name = content.user_contents[0].user.name
        
        # 获取内容标签
        content_tags = content_tag_crud.get_content_tags(db, content.id)
        tags = [
            TagResponse(
                id=tag.id,
                name=tag.name,
                description=tag.description,
                created_at=tag.created_at
            )
            for tag in content_tags
        ]
        
        return {
            "id": content.id,
            "public_title": content.public_title,
            "public_description": content.public_description,
            "summary_content": content.summary_content,
            "knowledge_preview": content.knowledge_preview,
            "author_name": author_name,
            "published_at": content.published_at,
            "tags": tags,
            "created_at": content.created_at
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取内容详情失败: {str(e)}"
        )


@router.post("/generate-tags", response_model=TagGenerationResponse)
async def generate_tags(
    request: TagGenerationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    为文本内容生成标签
    
    使用AI为给定的文本内容生成相关标签
    """
    try:
        result = tag_generation_service.generate_tags_for_text(db, request.content)
        return TagGenerationResponse(**result)
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"标签生成失败: {str(e)}"
        )


@router.get("/stats", response_model=CommunityStatsResponse)
async def get_community_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取社群统计信息
    
    返回社群的基本统计数据
    """
    try:
        # 获取统计数据
        total_public_contents = len(content_crud.get_public_contents(db, 0, 10000))
        total_tags = len(tag_crud.get_multi(db, 0, 10000))
        
        # 获取热门标签
        popular_tags_data = tag_crud.get_popular_tags(db, 5)
        popular_tags = [
            TagResponse(
                id=tag["id"],
                name=tag["name"],
                description=tag["description"],
                content_count=tag["content_count"],
                created_at=tag_crud.get(db, tag["id"]).created_at
            )
            for tag in popular_tags_data
        ]
        
        # 获取最新内容
        recent_contents_data = content_crud.get_public_contents(db, 0, 5)
        recent_contents = []
        for content in recent_contents_data:
            author_name = None
            if content.user_contents:
                author_name = content.user_contents[0].user.name
            
            content_tags = content_tag_crud.get_content_tags(db, content.id)
            tags = [
                TagResponse(
                    id=tag.id,
                    name=tag.name,
                    description=tag.description,
                    created_at=tag.created_at
                )
                for tag in content_tags
            ]
            
            preview = None
            if content.summary_content:
                preview = content.summary_content[:100] + "..." if len(content.summary_content) > 100 else content.summary_content
            
            recent_contents.append(PublicContentResponse(
                id=content.id,
                public_title=content.public_title,
                public_description=content.public_description,
                preview=preview,
                author_name=author_name,
                published_at=content.published_at,
                tags=tags
            ))
        
        return CommunityStatsResponse(
            total_public_contents=total_public_contents,
            total_tags=total_tags,
            popular_tags=popular_tags,
            recent_contents=recent_contents
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取统计信息失败: {str(e)}"
        )
