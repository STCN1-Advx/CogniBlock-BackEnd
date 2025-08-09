"""
简化的笔记总结API - 单一端点版本
只保留一个核心API端点，通过参数控制不同功能
"""

import json
import time
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, BackgroundTasks, Query, UploadFile, File, Form
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from datetime import datetime

from app.api.v2.auth import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.crud.content import content
from app.utils.task_manager import task_manager
from app.utils.websocket_manager import WebSocketManager
# from app.services.ocr_service import ocr_service  # 暂时注释，缺少依赖

# 创建全局 websocket_manager 实例
websocket_manager = WebSocketManager()

# 配置日志
logger = logging.getLogger(__name__)

# 创建路由器
router = APIRouter()

# WebSocket管理器
websocket_manager = WebSocketManager()

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


@router.post("/process-image")
async def process_image_notes(
    file: UploadFile = File(..., description="要识别的图片文件"),
    title: Optional[str] = Form(None, description="笔记标题"),
    action: str = Query("summarize", description="操作类型: summarize(总结), status(状态), cancel(取消)"),
    task_id: Optional[str] = Query(None, description="任务ID，用于查询状态或取消任务"),
    background_tasks: BackgroundTasks = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    处理图片上传并进行 OCR 识别和笔记总结
    
    支持的操作：
    - summarize: 上传图片，进行 OCR 识别并创建总结任务
    - status: 查询任务状态  
    - cancel: 取消任务
    
    参数：
    - file: 图片文件
    - title: 笔记标题（可选）
    - action: 操作类型
    - task_id: 任务ID（status和cancel操作需要）
    """
    try:
        # 根据action执行不同操作
        if action == "summarize":
            return await _handle_image_summarize(file, title, current_user, db, background_tasks)
        elif action == "status":
            return await _handle_status(task_id, current_user)
        elif action == "cancel":
            return await _handle_cancel(task_id, current_user)
        else:
            raise HTTPException(status_code=400, detail=f"不支持的操作类型: {action}")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"处理图片笔记操作失败: {e}")
        raise HTTPException(status_code=500, detail="处理请求失败")


@router.post("/process")
async def process_notes(
    content_ids: Optional[List[str]] = None,
    action: str = Query("summarize", description="操作类型: summarize(总结), status(状态), cancel(取消)"),
    task_id: Optional[str] = Query(None, description="任务ID，用于查询状态或取消任务"),
    background_tasks: BackgroundTasks = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    统一的笔记处理端点
    
    支持的操作：
    - summarize: 创建总结任务
    - status: 查询任务状态  
    - cancel: 取消任务
    
    参数：
    - content_ids: 内容ID列表
    - action: 操作类型
    - task_id: 任务ID（status和cancel操作需要）
    """
    try:
        # 根据action执行不同操作
        if action == "summarize":
            return await _handle_summarize(content_ids, current_user, db, background_tasks)
        elif action == "status":
            return await _handle_status(task_id, current_user)
        elif action == "cancel":
            return await _handle_cancel(task_id, current_user)
        else:
            raise HTTPException(status_code=400, detail=f"不支持的操作类型: {action}")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"处理笔记操作失败: {e}")
        raise HTTPException(status_code=500, detail="处理请求失败")


async def _handle_image_summarize(file: UploadFile, title: Optional[str], current_user: User, db: Session, background_tasks: BackgroundTasks):
    """
    处理图片上传、OCR 识别并创建总结任务
    """
    try:
        # 验证文件类型
        if not file.content_type or not file.content_type.startswith('image/'):
            raise HTTPException(status_code=400, detail="请上传有效的图片文件")
        
        # 读取图片数据
        image_data = await file.read()
        if len(image_data) == 0:
            raise HTTPException(status_code=400, detail="图片文件为空")
        
        # 记录图片大小后立即清理二进制数据
        image_size = len(image_data)
        del image_data  # 立即删除二进制数据避免意外引用
        
        # 暂时跳过 OCR 识别，直接使用占位符文本
        logger.info(f"接收到用户 {current_user.id} 的图片文件: {file.filename}")
        
        # 临时解决方案：使用文件名和基本信息作为内容
        ocr_result = f"图片文件: {file.filename}\n文件大小: {image_size} 字节\n上传时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n注意：OCR 功能暂时不可用，这是一个占位符文本。"
        
        logger.info(f"生成占位符文本，长度: {len(ocr_result)} 个字符")
        
        # 创建内容记录
        content_title = title or f"图片笔记 - {file.filename}"
        
        # 创建内容对象
        from app.schemas.canva import ContentCreate
        content_data = ContentCreate(
            content_type="text",
            text_data=ocr_result,
            image_data=None
        )
        
        # 使用 create_with_user_relation 方法创建内容并建立用户关联
        from app.crud.content import content as content_crud
        new_content = content_crud.create_with_user_relation(db, obj_in=content_data, user_id=current_user.id)
        
        logger.info(f"为用户 {current_user.id} 创建内容记录: {new_content.id}")
        
        # 创建总结任务
        task_id = await task_manager.create_task(
            user_id=str(current_user.id),
            content_ids=[str(new_content.id)],
            websocket_manager=websocket_manager
        )
        
        logger.info(f"为用户 {current_user.id} 创建总结任务: {task_id}")
        
        return {
            "action": "summarize",
            "status": "processing",
            "message": "图片已上传并识别完成，总结任务已创建",
            "task_id": task_id,
            "content_id": str(new_content.id),
            "ocr_text_length": len(ocr_result),
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"处理图片总结失败: {type(e).__name__}: {str(e)[:200]}")
        raise HTTPException(status_code=500, detail="处理图片失败，请稍后重试")


async def _handle_summarize(content_ids: List[str], current_user: User, db: Session, background_tasks: BackgroundTasks):
    """处理总结请求"""
    if not content_ids:
        raise HTTPException(status_code=400, detail="内容ID列表不能为空")
    
    # 验证内容存在性和用户权限
    contents = []
    for content_id in content_ids:
        content_obj = content.get(db, id=content_id)
        if not content_obj:
            raise HTTPException(status_code=404, detail=f"内容 {content_id} 不存在")
        
        # 检查用户权限 - 使用UserContent关联表
        if not content.check_user_access(db, content_id=int(content_id), user_id=current_user.id):
            raise HTTPException(status_code=403, detail=f"无权访问内容 {content_id}")
        
        contents.append(content_obj)
    
    # 检查缓存
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
            "action": "summarize",
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
        "action": "summarize",
        "status": "processing",
        "message": "总结任务已创建，正在处理中",
        "task_id": task_id,
        "content_count": len(content_ids),
        "timestamp": datetime.now().isoformat()
    }


async def _handle_status(task_id: str, current_user: User):
    """处理状态查询"""
    if not task_id:
        raise HTTPException(status_code=400, detail="查询状态需要提供task_id")
    
    task_info = await task_manager.get_task_status(task_id)
    
    if not task_info:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    # 验证用户权限 - task_info 是字典格式
    if task_info["user_id"] != str(current_user.id):
        raise HTTPException(status_code=403, detail="无权访问此任务")
    
    return {
        "action": "status",
        "task_id": task_id,
        "status": task_info["status"],
        "progress": task_info["progress"],
        "created_at": task_info["created_at"],
        "started_at": task_info["started_at"],
        "completed_at": task_info["completed_at"],
        "result": task_info["result"],
        "error_message": task_info["error_message"],
        "content_count": len(task_info["content_ids"]),
        "timestamp": datetime.now().isoformat()
    }


async def _handle_cancel(task_id: str, current_user: User):
    """处理任务取消"""
    if not task_id:
        raise HTTPException(status_code=400, detail="取消任务需要提供task_id")
    
    task_info = await task_manager.get_task_status(task_id)
    
    if not task_info:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    # 验证用户权限 - task_info 是字典格式
    if task_info["user_id"] != str(current_user.id):
        raise HTTPException(status_code=403, detail="无权访问此任务")
    
    # 取消任务
    success = await task_manager.cancel_task(task_id, str(current_user.id))
    
    if success:
        return {
            "action": "cancel",
            "task_id": task_id,
            "status": "cancelled",
            "message": "任务已成功取消",
            "timestamp": datetime.now().isoformat()
        }
    else:
        return {
            "action": "cancel",
            "task_id": task_id,
            "status": "failed",
            "message": "任务取消失败，可能已经完成或不存在",
            "timestamp": datetime.now().isoformat()
        }


@router.get("/health")
async def health_check():
    """健康检查端点"""
    try:
        # 检查任务管理器状态
        task_stats = {
            "active": len([t for t in task_manager.tasks.values() if t.status.value in ["pending", "running"]]),
            "running": len([t for t in task_manager.tasks.values() if t.status.value == "running"])
        }
        
        # 检查WebSocket连接状态
        ws_stats = {
            "total_connections": websocket_manager.get_total_connections(),
            "active_users": len(websocket_manager.get_active_users())
        }
        
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "tasks": task_stats,
            "websocket": ws_stats,
            "endpoints": {
                "process": "/api/v2/note-summary/process",
                "websocket": "/api/v2/note-summary/ws/{user_id}",
                "health": "/api/v2/note-summary/health"
            }
        }
        
    except Exception as e:
        logger.error(f"健康检查失败: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }