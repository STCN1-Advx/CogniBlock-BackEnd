from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional
from uuid import UUID

from app.db.session import get_db
from app.crud.content import content as content_crud
from app.models.user import User
from app.api.v2.auth import get_current_user
from app.schemas.canva import ContentCreate

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
        "ocr_result": content.ocr_result,
        "ocr_result_length": len(content.ocr_result) if content.ocr_result else 0,
        "ocr_result_preview": content.ocr_result[:200] + "..." if content.ocr_result and len(content.ocr_result) > 200 else content.ocr_result,
        "ocr_status": content.ocr_status,
        "summary_title": content.summary_title,
        "summary_topic": content.summary_topic,
        "summary_content": content.summary_content,
        "summary_status": content.summary_status,
        "content_hash": content.content_hash,
        "filename": content.filename,
        "file_size": content.file_size,
        "created_at": content.created_at,
        "updated_at": content.updated_at,
        # 调试信息
        "debug_info": {
            "has_text_data": bool(content.text_data and content.text_data.strip()),
            "has_ocr_result": bool(content.ocr_result and content.ocr_result.strip()),
            "has_image_data": bool(content.image_data),
            "effective_content": content.text_data or content.ocr_result or "",
            "effective_content_length": len(content.text_data or content.ocr_result or ""),
            "effective_content_preview": (content.text_data or content.ocr_result or "")[:100] + "..." if len(content.text_data or content.ocr_result or "") > 100 else (content.text_data or content.ocr_result or "")
        }
    }


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
            "has_ocr_result": bool(content.ocr_result and content.ocr_result.strip()),
            "has_image_data": bool(content.image_data),
            "text_data_length": len(content.text_data) if content.text_data else 0,
            "ocr_result_length": len(content.ocr_result) if content.ocr_result else 0,
            "ocr_status": content.ocr_status,
            "summary_status": content.summary_status,
            "filename": content.filename,
            "created_at": content.created_at,
            "effective_content_length": len(content.text_data or content.ocr_result or "")
        })
    
    return {
        "contents": result,
        "total": len(result),
        "skip": skip,
        "limit": limit
    }