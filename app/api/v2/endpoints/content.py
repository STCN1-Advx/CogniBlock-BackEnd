from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional, List
from uuid import UUID

from app.db.session import get_db
from app.crud.content import content as content_crud
from app.models.user import User
from app.api.v2.auth import get_current_user
from app.schemas.canva import ContentCreate
from app.schemas.community import (
    PublishContentRequest, PublicContentResponse, ContentTagRequest, 
    ContentTagResponse, TagResponse
)
from app.crud.content_tag import content_tag as content_tag_crud

router = APIRouter()


@router.post("/")
async def create_content(
    content_data: ContentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    创建新的内容
    """
    try:
        # 创建内容并建立用户关联
        content = content_crud.create_with_user_relation(
            db, obj_in=content_data, user_id=current_user.id
        )
        
        return {
            "id": content.id,
            "content_type": content.content_type,
            "text_data": content.text_data,
            "image_data": content.image_data,
            "created_at": content.created_at,
            "message": "内容创建成功"
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建内容失败: {str(e)}"
        )


@router.get("/content/{content_id}")
async def get_content_by_id(
    content_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    通过 content_id 获取具体内容详情
    用于调试和检查数据是否正确保存
    """
    # 获取内容
    content = content_crud.get(db, id=content_id)
    if not content:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Content with id {content_id} not found"
        )
    
    # 检查用户是否有权限访问该内容
    if not content_crud.check_user_access(db, content_id, current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to access this content"
        )
    
    # 返回详细的内容信息
    return {
        "id": content.id,
        "content_type": content.content_type,
        "text_data": content.text_data,
        "text_data_length": len(content.text_data) if content.text_data else 0,
        "text_data_preview": content.text_data[:200] + "..." if content.text_data and len(content.text_data) > 200 else content.text_data,
        "image_data": content.image_data,
        "image_data_length": len(content.image_data) if content.image_data else 0,
        "image_data_has_data": bool(content.image_data),
        "summary_title": content.summary_title,
        "summary_topic": content.summary_topic,
        "summary_content": content.summary_content,
        "summary_status": content.summary_status,
        "content_hash": content.content_hash,
        
        
        "created_at": content.created_at,
        "updated_at": content.updated_at,
        # 调试信息
        "debug_info": {
            "has_text_data": bool(content.text_data and content.text_data.strip()),
            "has_image_data": bool(content.image_data),
            "effective_content": content.text_data or "",
            "effective_content_length": len(content.text_data or ""),
            "effective_content_preview": (content.text_data or "")[:100] + "..." if len(content.text_data or "") > 100 else (content.text_data or "")
        }
    }


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
        added_tags = []
        for tag_data in request.tags:
            tag = content_tag_crud.add_tag_to_content(
                db, content_id, tag_data.name, tag_data.confidence, tag_data.description
            )
            added_tags.append(tag)

        return {
            "message": "标签添加成功",
            "content_id": content_id,
            "added_tags_count": len(added_tags)
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"添加标签失败: {str(e)}"
        )


@router.get("/user/contents")
async def get_user_contents(
    skip: int = 0,
    limit: int = 20,
    content_type: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取当前用户的所有内容列表
    """
    if content_type:
        contents = content_crud.get_user_content_by_type(
            db, user_id=current_user.id, content_type=content_type, skip=skip, limit=limit
        )
    else:
        contents = content_crud.get_user_contents(
            db, user_id=current_user.id, skip=skip, limit=limit
        )
    
    # 返回简化的内容列表
    result = []
    for content in contents:
        result.append({
            "id": content.id,
            "content_type": content.content_type,
            "has_text_data": bool(content.text_data and content.text_data.strip()),
            "has_image_data": bool(content.image_data),
            "text_data_length": len(content.text_data) if content.text_data else 0,
            "summary_status": content.summary_status,

            "created_at": content.created_at,
            "effective_content_length": len(content.text_data or "")
        })
    
    return {
        "contents": result,
        "total": len(result),
        "skip": skip,
        "limit": limit
    }