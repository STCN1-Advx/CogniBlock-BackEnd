"""OCR API endpoint - 单一端点处理图片上传和WebSocket通知
"""

import logging
import uuid
from typing import Dict, Any, Optional
from fastapi import APIRouter, UploadFile, File, HTTPException, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.orm import Session

from app.services.ocr_service import ocr_service
from app.api.v2.auth import get_current_user, get_optional_user
from app.db.session import get_db
from app.models.user import User
from app.models.content import Content
from app.models.user_content import UserContent
from app.crud.content import content

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/process", summary="OCR图片处理")
async def process_image(file: UploadFile = File(...)) -> Dict[str, Any]:
    """
    上传图片进行OCR处理
    
    Args:
        file: 上传的图片文件
        
    Returns:
        包含任务ID和WebSocket连接信息的响应
    """
    try:
        # 验证文件类型
        if not file.content_type or not file.content_type.startswith('image/'):
            raise HTTPException(status_code=400, detail="只支持图片文件")
        
        # 读取文件内容
        file_content = await file.read()
        
        # 提交任务
        task_id = await ocr_service.submit_task(
            image_data=file_content,
            filename=file.filename or "unknown.jpg",
            content_type=file.content_type
        )
        
        return {
            "task_id": task_id,
            "message": "图片上传成功，开始处理",
            "websocket_url": f"/api/v2/ocr/ws/{task_id}",
            "status": "processing"
        }
        
    except Exception as e:
        logger.error(f"OCR处理失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"处理失败: {str(e)}")

@router.post("/process-and-save", summary="OCR图片处理并保存到数据库")
async def process_and_save_image(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    上传图片进行OCR处理并保存到数据库
    
    Args:
        file: 上传的图片文件
        user: 当前用户
        db: 数据库会话
        
    Returns:
        包含任务ID、内容ID和WebSocket连接信息的响应
    """
    try:
        # 验证文件类型
        if not file.content_type or not file.content_type.startswith('image/'):
            raise HTTPException(status_code=400, detail="只支持图片文件")
        
        # 读取文件内容
        file_content = await file.read()
        
        # 创建内容记录
        content_obj = Content(
            content_type="ocr",
            text_data="",  # OCR结果完成后更新
            ocr_status="processing",
            filename=file.filename or "unknown.jpg"
        )
        
        db.add(content_obj)
        db.commit()
        db.refresh(content_obj)
        
        # 创建用户内容关联
        user_content_obj = UserContent(
            user_id=user.id,
            content_id=content_obj.id,
            permission="owner"
        )
        
        db.add(user_content_obj)
        db.commit()
        
        # 提交OCR任务，传递内容ID
        task_id = await ocr_service.submit_task(
            image_data=file_content,
            filename=file.filename or "unknown.jpg",
            content_type=file.content_type,
            content_id=str(content_obj.id),  # 传递内容ID
            user_id=str(user.id)  # 传递用户ID
        )
        
        return {
            "task_id": task_id,
            "content_id": str(content_obj.id),
            "message": "图片上传成功，开始处理并将保存到数据库",
            "websocket_url": f"/api/v2/ocr/ws/{task_id}",
            "status": "processing"
        }
        
    except Exception as e:
        logger.error(f"OCR处理失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"处理失败: {str(e)}")

@router.websocket("/ws/{task_id}")
async def ocr_websocket_endpoint(websocket: WebSocket, task_id: str):
    """
    OCR任务状态WebSocket接口 - 实时通知处理进度和最终结果
    
    Args:
        websocket: WebSocket连接
        task_id: 任务ID
    """
    await websocket.accept()
    
    try:
        # 检查任务是否存在
        task = await ocr_service.get_task(task_id)
        if not task:
            await websocket.send_json({
                "type": "error",
                "message": "任务不存在"
            })
            await websocket.close()
            return
        
        # 添加WebSocket连接
        await ocr_service.add_websocket_connection(task_id, websocket)
        
        # 发送当前状态
        await websocket.send_json({
            "type": "status",
            "task_id": task_id,
            "status": task.status,
            "description": task.description,
            "progress": getattr(task, 'progress', 0)
        })
        
        # 如果任务已完成，发送结果
        if task.status == "completed" and task.markdown_result:
            await websocket.send_json({
                "type": "completed",
                "task_id": task_id,
                "result": {
                    "markdown": task.markdown_result,
                    "html": task.html_result or ""
                }
            })
        elif task.status == "failed" and task.error_message:
            await websocket.send_json({
                "type": "failed",
                "task_id": task_id,
                "error": task.error_message
            })
        
        # 保持连接直到客户端断开或任务完成
        try:
            while True:
                message = await websocket.receive_text()
                # 可以处理客户端发送的消息，比如取消任务等
                if message == "cancel":
                    await ocr_service.cancel_task(task_id)
                    break
        except WebSocketDisconnect:
            pass
            
    except Exception as e:
        logger.error(f"WebSocket连接错误: {str(e)}")
        try:
            await websocket.send_json({
                "type": "error",
                "message": f"连接错误: {str(e)}"
            })
        except:
            pass
    finally:
        # 移除WebSocket连接
        await ocr_service.remove_websocket_connection(task_id, websocket)

@router.get("/health", summary="OCR服务健康检查")
async def ocr_health_check() -> Dict[str, Any]:
    """OCR服务健康检查"""
    try:
        status = await ocr_service.get_service_status()
        return {
            "status": "healthy",
            "service": "ocr",
            "details": status
        }
    except Exception as e:
        logger.error(f"健康检查失败: {str(e)}")
        return {
            "status": "unhealthy",
            "service": "ocr",
            "error": str(e)
        }