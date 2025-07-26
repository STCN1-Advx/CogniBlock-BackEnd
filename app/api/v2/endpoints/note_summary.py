"""
笔记总结API路由

提供笔记总结相关的REST API接口
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.db.session import get_db
from app.api.v2.auth import get_current_user
from app.schemas.note_summary import (
    SummaryRequest, SummaryTaskResponse, SummaryTaskCreate,
    SummaryResult, SummaryErrorResponse
)
from app.utils.task_manager import task_manager
from app.crud.content import content
from app.schemas.user import User

router = APIRouter()


@router.post("/create", response_model=SummaryTaskCreate)
async def create_summary_task(
    request: SummaryRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    创建笔记总结任务
    
    - **content_ids**: 要总结的内容ID列表
    - 返回任务ID和状态信息
    """
    try:
        # 验证内容权限
        for content_id in request.content_ids:
            if not crud_content.check_user_access(db, content_id, current_user.id):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"没有访问内容 {content_id} 的权限"
                )
        
        # 创建任务
        task_id = await task_manager.create_task(
            user_id=current_user.id,
            content_ids=request.content_ids
        )
        
        return SummaryTaskCreate(
            task_id=task_id,
            message="总结任务已创建，正在处理中...",
            content_count=len(request.content_ids)
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建任务失败: {str(e)}"
        )


@router.get("/task/{task_id}", response_model=SummaryTaskResponse)
async def get_task_status(
    task_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    获取总结任务状态
    
    - **task_id**: 任务ID
    - 返回任务的详细状态信息
    """
    task_info = await task_manager.get_task_status(task_id)
    
    if not task_info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="任务不存在"
        )
    
    # 验证任务所有权
    if task_info["user_id"] != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="没有访问此任务的权限"
        )
    
    return SummaryTaskResponse(**task_info)


@router.get("/tasks", response_model=List[SummaryTaskResponse])
async def get_user_tasks(
    limit: int = 10,
    current_user: User = Depends(get_current_user)
):
    """
    获取用户的总结任务列表
    
    - **limit**: 返回任务数量限制（默认10个）
    - 返回用户的任务列表，按创建时间倒序
    """
    if limit > 50:
        limit = 50  # 限制最大返回数量
    
    tasks = await task_manager.get_user_tasks(current_user.id, limit)
    return [SummaryTaskResponse(**task) for task in tasks]


@router.delete("/task/{task_id}")
async def cancel_task(
    task_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    取消总结任务
    
    - **task_id**: 任务ID
    - 只能取消自己的未完成任务
    """
    success = await task_manager.cancel_task(task_id, current_user.id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="无法取消任务（任务不存在、无权限或已完成）"
        )
    
    return {"message": "任务已取消"}


@router.get("/task/{task_id}/result", response_model=SummaryResult)
async def get_task_result(
    task_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    获取总结任务结果
    
    - **task_id**: 任务ID
    - 只返回已完成任务的结果
    """
    task_info = await task_manager.get_task_status(task_id)
    
    if not task_info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="任务不存在"
        )
    
    # 验证任务所有权
    if task_info["user_id"] != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="没有访问此任务的权限"
        )
    
    # 检查任务状态
    if task_info["status"] != "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"任务尚未完成，当前状态: {task_info['status']}"
        )
    
    if not task_info["result"]:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="任务结果不可用"
        )
    
    return SummaryResult(**task_info["result"])


@router.get("/content/{content_id}/summary")
async def get_content_summary(
    content_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取单个内容的总结
    
    - **content_id**: 内容ID
    - 返回该内容的总结信息（如果存在）
    """
    content_obj = content.get(db, content_id)
    if not content_obj:
        raise HTTPException(status_code=404, detail="内容不存在")
    
    # 检查用户权限
    if not content.check_user_access(db, content_id, current_user.id):
        raise HTTPException(status_code=403, detail="无权访问该内容")
    
    if not content_obj.summary_content:
        raise HTTPException(status_code=404, detail="该内容暂无总结")
    
    return {
        "content_id": content_id,
        "title": content_obj.summary_title or "无标题",
        "topic": content_obj.summary_topic or "未分类",
        "content": content_obj.summary_content,
        "created_at": content_obj.created_at,
        "updated_at": content_obj.updated_at
    }


@router.get("/search")
async def search_summaries(
    query: str,
    limit: int = 20,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    搜索用户的总结内容
    
    - **query**: 搜索关键词
    - **limit**: 返回结果数量限制（默认20个）
    - 在用户的总结标题、主题和内容中搜索
    """
    if not query.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="搜索关键词不能为空"
        )
    
    if limit > 100:
        limit = 100  # 限制最大返回数量
    
    # 搜索总结内容
    results = content.search_summary_content(db, current_user.id, query, limit)
    
    return {
        "query": query,
        "total": len(results),
        "results": [
            {
                "content_id": content.id,
                "summary_title": content.summary_title,
                "summary_topic": content.summary_topic,
                "summary_content": content.summary_content,
                "updated_at": content.updated_at.isoformat()
            }
            for content in results
        ]
    }


@router.get("/stats")
async def get_summary_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取用户的总结统计信息
    
    - 返回用户的总结数量、最近活动等统计数据
    """
    # 获取有总结的内容
    summarized_contents = content.get_contents_with_summary(db, current_user.id)
    
    # 获取用户的任务历史
    recent_tasks = await task_manager.get_user_tasks(current_user.id, 5)
    
    return {
        "total_summaries": len(summarized_contents),
        "recent_tasks_count": len(recent_tasks),
        "last_summary_date": (
            max(content.updated_at for content in summarized_contents).isoformat()
            if summarized_contents else None
        ),
        "recent_tasks": recent_tasks
    }