from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID

from app.db.session import get_db
from app.crud.content import content as content_crud
from app.crud.content_tag import content_tag as content_tag_crud
from app.models.user import User
from app.api.v2.auth import get_current_user
from app.schemas.community import (
    PublishContentRequest, PublicContentResponse, ContentTagRequest, 
    ContentTagResponse, TagResponse
)

router = APIRouter()


@router.post("/{content_id}/publish")
async def publish_content(
    content_id: int,
    request: PublishContentRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    将内容设为公开
    
    用户可以将自己的内容设置为公开，供其他用户浏览
    """
    try:
        # 检查内容是否存在
        content = content_crud.get(db, content_id)
        if not content:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="内容不存在"
            )
        
        # 检查用户是否有权限
        if not content_crud.check_user_access(db, content_id, current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="您没有权限操作此内容"
            )
        
        # 发布内容
        published_content = content_crud.publish_content(
            db, content_id, request.public_title, request.public_description
        )
        
        if not published_content:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="发布内容失败"
            )
        
        return {
            "message": "内容发布成功",
            "content_id": content_id,
            "public_title": published_content.public_title,
            "published_at": published_content.published_at
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"发布内容失败: {str(e)}"
        )


@router.delete("/{content_id}/publish")
async def unpublish_content(
    content_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    取消内容公开
    
    用户可以取消自己内容的公开状态
    """
    try:
        # 检查内容是否存在
        content = content_crud.get(db, content_id)
        if not content:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="内容不存在"
            )
        
        # 检查用户是否有权限
        if not content_crud.check_user_access(db, content_id, current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="您没有权限操作此内容"
            )
        
        # 取消发布
        unpublished_content = content_crud.unpublish_content(db, content_id)
        
        if not unpublished_content:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="取消发布失败"
            )
        
        return {
            "message": "取消发布成功",
            "content_id": content_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"取消发布失败: {str(e)}"
        )


@router.get("/{content_id}/tags", response_model=List[ContentTagResponse])
async def get_content_tags(
    content_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取内容的标签
    
    返回指定内容的所有标签及置信度
    """
    try:
        # 检查内容是否存在
        content = content_crud.get(db, content_id)
        if not content:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="内容不存在"
            )
        
        # 检查用户是否有权限（公开内容或用户拥有的内容）
        has_access = (
            content_crud.check_public_access(db, content_id) or 
            content_crud.check_user_access(db, content_id, current_user.id)
        )
        
        if not has_access:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="您没有权限访问此内容"
            )
        
        # 获取标签及置信度
        tags_data = content_tag_crud.get_content_tags_with_confidence(db, content_id)
        
        return [
            ContentTagResponse(
                id=tag["id"],
                name=tag["name"],
                description=tag["description"],
                confidence=tag["confidence"]
            )
            for tag in tags_data
        ]
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取内容标签失败: {str(e)}"
        )


@router.post("/{content_id}/tags")
async def add_content_tags(
    content_id: int,
    request: ContentTagRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    为内容添加标签
    
    用户可以为自己的内容手动添加标签
    """
    try:
        # 检查内容是否存在
        content = content_crud.get(db, content_id)
        if not content:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="内容不存在"
            )
        
        # 检查用户是否有权限
        if not content_crud.check_user_access(db, content_id, current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="您没有权限操作此内容"
            )
        
        # 添加标签
        content_tags = content_tag_crud.update_content_tags(
            db, content_id, request.tag_ids, confidence=1.0
        )
        
        return {
            "message": "标签添加成功",
            "content_id": content_id,
            "tag_count": len(content_tags)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"添加标签失败: {str(e)}"
        )


@router.delete("/{content_id}/tags/{tag_id}")
async def remove_content_tag(
    content_id: int,
    tag_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    移除内容的标签
    
    用户可以移除自己内容的特定标签
    """
    try:
        # 检查内容是否存在
        content = content_crud.get(db, content_id)
        if not content:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="内容不存在"
            )
        
        # 检查用户是否有权限
        if not content_crud.check_user_access(db, content_id, current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="您没有权限操作此内容"
            )
        
        # 移除标签
        removed_tag = content_tag_crud.delete(db, content_id, tag_id)
        
        if not removed_tag:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="标签关联不存在"
            )
        
        return {
            "message": "标签移除成功",
            "content_id": content_id,
            "tag_id": tag_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"移除标签失败: {str(e)}"
        )


@router.get("/user/public", response_model=List[PublicContentResponse])
async def get_user_public_contents(
    skip: int = Query(0, ge=0, description="跳过的数量"),
    limit: int = Query(20, ge=1, le=100, description="返回的数量"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取当前用户的公开内容
    
    返回当前用户已发布的所有公开内容
    """
    try:
        contents = content_crud.get_user_public_contents(db, current_user.id, skip, limit)
        
        result = []
        for content in contents:
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
                author_name=current_user.name,
                published_at=content.published_at,
                tags=tags
            ))
        
        return result
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取用户公开内容失败: {str(e)}"
        )
