from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.db.session import get_db
from app.api.v2.auth import get_current_user
from app.models.user import User
from app.crud.article import article
from app.schemas.article import ArticleListResponse, ArticleWithPermission

router = APIRouter()


@router.get("/", response_model=ArticleListResponse)
async def get_user_articles(
    skip: int = Query(0, ge=0, description="跳过的记录数"),
    limit: int = Query(100, ge=1, le=1000, description="返回的记录数限制"),
    permission: Optional[str] = Query(None, pattern="^[012]$", description="权限过滤：0=查看，1=编辑，2=管理"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取当前用户有权限的所有文档
    
    - **skip**: 跳过的记录数，用于分页
    - **limit**: 返回的记录数限制，最大1000
    - **permission**: 可选的权限过滤，0=查看，1=编辑，2=管理
    
    返回按权限等级排序的文档列表（管理>编辑>查看），相同权限等级按创建时间倒序排列
    """
    try:
        # 根据是否有权限过滤来选择不同的查询方法
        if permission is not None:
            # 按特定权限过滤
            articles_data = article.get_user_articles_by_permission(
                db=db, 
                user_id=current_user.id, 
                permission=permission,
                skip=skip, 
                limit=limit
            )
            # 统计该权限等级的文档总数
            total = len(articles_data)  # 简化统计，实际应该单独查询
        else:
            # 获取所有有权限的文档
            articles_data = article.get_user_articles_with_permission(
                db=db, 
                user_id=current_user.id, 
                skip=skip, 
                limit=limit
            )
            # 统计总数
            total = article.count_user_articles(db=db, user_id=current_user.id)
        
        # 转换为Pydantic模型
        articles_list = [ArticleWithPermission(**article_data) for article_data in articles_data]
        
        return ArticleListResponse(
            articles=articles_list,
            total=total
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取文档列表失败: {str(e)}"
        )


@router.get("/stats")
async def get_user_article_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取用户文档统计信息
    
    返回用户在不同权限等级下的文档数量统计
    """
    try:
        # 统计各权限等级的文档数量
        manage_count = len(article.get_user_articles_by_permission(
            db=db, user_id=current_user.id, permission='2', skip=0, limit=10000
        ))
        
        edit_count = len(article.get_user_articles_by_permission(
            db=db, user_id=current_user.id, permission='1', skip=0, limit=10000
        ))
        
        view_count = len(article.get_user_articles_by_permission(
            db=db, user_id=current_user.id, permission='0', skip=0, limit=10000
        ))
        
        total_count = article.count_user_articles(db=db, user_id=current_user.id)
        
        return {
            "total": total_count,
            "manage": manage_count,
            "edit": edit_count,
            "view": view_count,
            "user_id": str(current_user.id)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取文档统计失败: {str(e)}"
        )