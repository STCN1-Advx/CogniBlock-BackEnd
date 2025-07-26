from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.db.session import get_db
from app.api.v2.auth import get_current_user
from app.models.user import User
from app.crud.knowledge_base import knowledge_base
from app.schemas.knowledge_base import KnowledgeBaseStats

router = APIRouter()


@router.get("/stats", response_model=KnowledgeBaseStats)
async def get_knowledge_base_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取用户知识库统计信息
    
    返回用户的知识库统计数据：
    - **knowledge_base_count**: 用户有权限的知识库数量
    - **total_content_count**: 用户有权限的总内容数
    - **last_updated_at**: 最近一次更新任何资产的时间
    - **user_id**: 用户ID
    """
    try:
        stats_data = knowledge_base.get_user_knowledge_base_stats(
            db=db, 
            user_id=current_user.id
        )
        
        return KnowledgeBaseStats(**stats_data)
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取知识库统计失败: {str(e)}"
        )


@router.get("/stats/detailed")
async def get_detailed_knowledge_base_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取详细的知识库统计信息
    
    返回按权限等级分组的知识库统计数据
    """
    try:
        # 获取基础统计
        basic_stats = knowledge_base.get_user_knowledge_base_stats(
            db=db, 
            user_id=current_user.id
        )
        
        # 按权限等级统计知识库数量
        manage_kb_count = knowledge_base.get_user_knowledge_base_count_by_permission(
            db=db, user_id=current_user.id, permission='2'
        )
        
        edit_kb_count = knowledge_base.get_user_knowledge_base_count_by_permission(
            db=db, user_id=current_user.id, permission='1'
        )
        
        view_kb_count = knowledge_base.get_user_knowledge_base_count_by_permission(
            db=db, user_id=current_user.id, permission='0'
        )
        
        # 获取最近更新的知识库记录
        recent_knowledge_bases = knowledge_base.get_user_recent_knowledge_bases(
            db=db, user_id=current_user.id, limit=5
        )
        
        return {
            "basic_stats": basic_stats,
            "permission_breakdown": {
                "manage": manage_kb_count,
                "edit": edit_kb_count,
                "view": view_kb_count
            },
            "recent_knowledge_bases": recent_knowledge_bases
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取详细知识库统计失败: {str(e)}"
        )


@router.get("/recent")
async def get_recent_knowledge_bases(
    limit: int = 5,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取用户最近更新的知识库记录
    
    - **limit**: 返回记录数限制，默认5条
    """
    try:
        recent_knowledge_bases = knowledge_base.get_user_recent_knowledge_bases(
            db=db, 
            user_id=current_user.id, 
            limit=limit
        )
        
        return {
            "recent_knowledge_bases": recent_knowledge_bases,
            "total_count": len(recent_knowledge_bases),
            "user_id": str(current_user.id)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取最近知识库记录失败: {str(e)}"
        )