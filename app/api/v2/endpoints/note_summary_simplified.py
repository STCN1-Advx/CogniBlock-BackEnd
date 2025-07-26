from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, BackgroundTasks
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
import logging
from datetime import datetime

from app.api.v2.auth import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.crud.content import content
from app.utils.task_manager import task_manager
from app.utils.websocket_manager import websocket_manager
from app.core.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)


@router.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    """WebSocket端点，用于实时通知"""
    await websocket_manager.connect(websocket, user_id)
    
    try:
        while True:
            # 接收消息
            message = await websocket.receive_text()
            
            # 处理心跳
            if message == "ping":
                await websocket.send_text("pong")
            else:
                # 处理其他消息类型
                try:
                    data = json.loads(message)
                    # 这里可以添加其他消息处理逻辑
                    await websocket_manager.send_to_user(user_id, {
                        "type": "message_received",
                        "data": data,
                        "timestamp": time.time()
                    })
                except json.JSONDecodeError:
                    await websocket_manager.send_to_user(user_id, {
                        "type": "error",
                        "message": "Invalid JSON format",
                        "timestamp": time.time()
                    })
                    
    except WebSocketDisconnect:
        websocket_manager.disconnect(websocket, user_id)


@router.post("/summarize")
async def create_summary_task(
    content_ids: List[str],
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    创建笔记总结任务
    
    支持单个或多个内容ID的总结：
    - 检查缓存，如果已有总结则直接返回
    - 异步处理总结任务
    - 通过WebSocket实时通知进度
    """
    try:
        if not content_ids:
            raise HTTPException(status_code=400, detail="内容ID列表不能为空")
        
        # 验证内容存在性和用户权限
        contents = []
        for content_id in content_ids:
            content_obj = content.get(db, id=content_id)
            if not content_obj:
                raise HTTPException(status_code=404, detail=f"内容 {content_id} 不存在")
            
            # 检查用户权限
            if content_obj.user_id != current_user.id:
                raise HTTPException(status_code=403, detail=f"无权访问内容 {content_id}")
            
            contents.append(content_obj)
        
        # 检查是否所有内容都已有总结
        all_cached = True
        cached_results = []
        
        for content_obj in contents:
            if content_obj.summary_content:
                # 验证内容是否已更改
                current_hash = task_manager._generate_content_hash(content_obj.text_data or "")
                if content_obj.content_hash == current_hash:
                    cached_results.append({
                        "content_id": str(content_obj.id),
                        "summary_title": content_obj.summary_title,
                        "summary_topic": content_obj.summary_topic,
                        "summary_content": content_obj.summary_content,
                        "cached": True
                    })
                else:
                    all_cached = False
                    break
            else:
                all_cached = False
                break
        
        # 如果所有内容都有缓存，直接返回
        if all_cached:
            logger.info(f"用户 {current_user.id} 的所有内容都有缓存总结")
            return {
                "status": "completed",
                "message": "所有内容都已有总结",
                "results": cached_results,
                "cached": True,
                "timestamp": datetime.now().isoformat()
            }
        
        # 创建异步总结任务
        task_id = await task_manager.create_task(
            user_id=str(current_user.id),
            content_ids=content_ids,
            websocket_manager=websocket_manager
        )
        
        logger.info(f"为用户 {current_user.id} 创建总结任务: {task_id}")
        
        return {
            "status": "processing",
            "message": "总结任务已创建，正在处理中",
            "task_id": task_id,
            "content_count": len(content_ids),
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建总结任务失败: {e}")
        raise HTTPException(status_code=500, detail="创建总结任务失败")

@router.get("/task/{task_id}")
async def get_task_status(
    task_id: str,
    current_user: User = Depends(get_current_user)
):
    """获取总结任务状态"""
    try:
        task_info = await task_manager.get_task_status(task_id)
        
        if not task_info:
            raise HTTPException(status_code=404, detail="任务不存在")
        
        # 验证用户权限
        if task_info.user_id != str(current_user.id):
            raise HTTPException(status_code=403, detail="无权访问此任务")
        
        return {
            "task_id": task_id,
            "status": task_info.status.value,
            "progress": task_info.progress,
            "created_at": task_info.created_at.isoformat(),
            "updated_at": task_info.updated_at.isoformat(),
            "completed_at": task_info.completed_at.isoformat() if task_info.completed_at else None,
            "result": task_info.result,
            "error_message": task_info.error_message,
            "content_count": len(task_info.content_ids)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取任务状态失败: {e}")
        raise HTTPException(status_code=500, detail="获取任务状态失败")


@router.get("/content/{content_id}")
async def get_content_summary(
    content_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取单个内容的总结"""
    try:
        # 获取内容对象
        content_obj = content.get(db, id=content_id)
        if not content_obj:
            raise HTTPException(status_code=404, detail="内容不存在")
        
        # 检查用户权限
        if content_obj.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="无权访问此内容")
        
        # 检查是否有总结
        if not content_obj.summary_content:
            return {
                "content_id": content_id,
                "has_summary": False,
                "message": "此内容尚未生成总结",
                "timestamp": datetime.now().isoformat()
            }
        
        return {
            "content_id": content_id,
            "has_summary": True,
            "summary_title": content_obj.summary_title,
            "summary_topic": content_obj.summary_topic,
            "summary_content": content_obj.summary_content,
            "created_at": content_obj.created_at.isoformat(),
            "updated_at": content_obj.updated_at.isoformat(),
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取内容总结失败: {e}")
        raise HTTPException(status_code=500, detail="获取内容总结失败")

@router.get("/user/tasks")
async def get_user_tasks(
    current_user: User = Depends(get_current_user),
    limit: int = 10,
    offset: int = 0
):
    """获取用户的总结任务列表"""
    try:
        user_tasks = await task_manager.get_user_tasks(str(current_user.id))
        
        # 分页
        total = len(user_tasks)
        tasks = user_tasks[offset:offset + limit]
        
        # 格式化任务信息
        formatted_tasks = []
        for task in tasks:
            formatted_tasks.append({
                "task_id": task.id,
                "status": task.status.value,
                "progress": task.progress,
                "created_at": task.created_at.isoformat(),
                "updated_at": task.updated_at.isoformat(),
                "completed_at": task.completed_at.isoformat() if task.completed_at else None,
                "content_count": len(task.content_ids),
                "error_message": task.error_message
            })
        
        return {
            "tasks": formatted_tasks,
            "total": total,
            "limit": limit,
            "offset": offset,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"获取用户任务失败: {e}")
        raise HTTPException(status_code=500, detail="获取用户任务失败")

@router.delete("/task/{task_id}")
async def cancel_task(
    task_id: str,
    current_user: User = Depends(get_current_user)
):
    """取消总结任务"""
    try:
        success = await task_manager.cancel_task(task_id, str(current_user.id))
        
        if not success:
            raise HTTPException(status_code=404, detail="任务不存在或无法取消")
        
        return {
            "message": "任务已取消",
            "task_id": task_id,
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"取消任务失败: {e}")
        raise HTTPException(status_code=500, detail="取消任务失败")


@router.get("/health")
async def health_check():
    """健康检查端点"""
    try:
        # 检查任务管理器状态
        active_tasks = len(task_manager.tasks)
        running_tasks = len(task_manager.running_tasks)
        
        # 检查WebSocket连接状态
        total_connections = websocket_manager.get_total_connections()
        active_users = len(websocket_manager.get_active_users())
        
        return {
            "status": "healthy",
            "service": "note_summary",
            "version": "2.0",
            "tasks": {
                "active": active_tasks,
                "running": running_tasks,
                "max_concurrent": settings.NOTE_MAX_CONCURRENT_TASKS
            },
            "websocket": {
                "total_connections": total_connections,
                "active_users": active_users
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"健康检查失败: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
        )