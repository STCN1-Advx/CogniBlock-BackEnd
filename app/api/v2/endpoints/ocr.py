"""
OCR API 端点
提供简洁的OCR服务接口，支持多并发和流式传输
"""

import asyncio
import json
import logging
from typing import Dict, Any
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from starlette.status import HTTP_400_BAD_REQUEST, HTTP_500_INTERNAL_SERVER_ERROR

from app.services.ocr_service import ocr_service, OCRTaskStatus
from app.schemas.ocr import (
    OCRRequest, OCRTaskResponse, OCRTaskStatusResponse, 
    OCRResultResponse, ModelsResponse, ModelInfo,
    OCRWebSocketMessage, OCRModel
)
from app.utils.websocket_manager import websocket_manager

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/models", response_model=ModelsResponse, summary="获取可用的OCR模型")
async def get_models():
    """获取可用的OCR模型列表"""
    try:
        models_dict = ocr_service.get_available_models()
        
        models = []
        for model_name, model_info in models_dict.items():
            models.append(ModelInfo(
                name=model_name,
                provider=model_info.get("provider", "unknown"),
                supports_stream=model_info.get("supports_stream", False),
                description=model_info.get("description", ""),
                available=model_info.get("available", False)
            ))
        
        return ModelsResponse(models=models)
        
    except Exception as e:
        logger.error(f"获取模型列表失败: {e}")
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取模型列表失败，请稍后重试"
        )


@router.post("/extract", response_model=OCRTaskResponse)
async def extract_text(
    file: UploadFile = File(..., description="要识别的图片文件"),
    model: OCRModel = Form(default=OCRModel.GEMINI_2_0_FLASH, description="使用的OCR模型"),
    prompt: str = Form(
        default="请提取这张图片中的所有文字内容，保持原有的格式和布局。",
        description="OCR提示词"
    )
):
    """
    创建OCR文字提取任务
    
    - **file**: 图片文件 (支持 JPEG, PNG, GIF, BMP, WEBP)
    - **model**: OCR模型选择
    - **prompt**: 自定义提示词
    
    返回任务ID，可通过WebSocket或轮询获取结果
    """
    try:
        # 验证文件类型
        if not file.content_type or not file.content_type.startswith('image/'):
            raise HTTPException(
                status_code=HTTP_400_BAD_REQUEST,
                detail="请上传有效的图片文件"
            )
        
        # 读取图片数据
        image_data = await file.read()
        if len(image_data) == 0:
            raise HTTPException(
                status_code=HTTP_400_BAD_REQUEST,
                detail="图片文件为空"
            )
        
        # 创建OCR任务
        task_id = await ocr_service.create_task(
            image_data=image_data,
            model=model.value,
            prompt=prompt
        )
        
        return OCRTaskResponse(
            task_id=task_id,
            status=OCRTaskStatus.PENDING.value,
            message="OCR任务已创建，正在处理中"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建OCR任务失败: {type(e).__name__}: {str(e)[:200]}")
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail="创建OCR任务失败，请稍后重试"
        )


@router.post("/extract/stream")
async def extract_text_stream(
    file: UploadFile = File(..., description="要识别的图片文件"),
    model: OCRModel = Form(default=OCRModel.GEMINI_2_0_FLASH, description="使用的OCR模型"),
    prompt: str = Form(
        default="请提取这张图片中的所有文字内容，保持原有的格式和布局。",
        description="OCR提示词"
    )
):
    """
    流式OCR文字提取
    
    - **file**: 图片文件
    - **model**: OCR模型选择  
    - **prompt**: 自定义提示词
    
    返回流式文本响应
    """
    try:
        # 验证文件类型
        if not file.content_type or not file.content_type.startswith('image/'):
            raise HTTPException(
                status_code=HTTP_400_BAD_REQUEST,
                detail="请上传有效的图片文件"
            )
        
        # 读取图片数据
        image_data = await file.read()
        if len(image_data) == 0:
            raise HTTPException(
                status_code=HTTP_400_BAD_REQUEST,
                detail="图片文件为空"
            )
        
        # 流式处理OCR
        async def generate_stream():
            try:
                async for chunk in ocr_service.process_ocr_stream(
                    image_data=image_data,
                    model=model.value,
                    prompt=prompt
                ):
                    yield f"data: {json.dumps({'chunk': chunk, 'finished': False})}\n\n"
                
                # 发送完成信号
                yield f"data: {json.dumps({'chunk': '', 'finished': True})}\n\n"
                
            except Exception as e:
                logger.error(f"流式OCR处理失败: {type(e).__name__}: {str(e)[:200]}")
                yield f"data: {json.dumps({'error': '流式OCR处理失败，请稍后重试'})}\n\n"
        
        return StreamingResponse(
            generate_stream(),
            media_type="text/plain",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Content-Type": "text/plain; charset=utf-8"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"流式OCR处理失败: {type(e).__name__}: {str(e)[:200]}")
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail="流式OCR处理失败，请稍后重试"
        )


@router.get("/task/{task_id}", response_model=OCRTaskStatusResponse)
async def get_task_status(task_id: str):
    """
    获取OCR任务状态
    
    - **task_id**: 任务ID
    
    返回任务状态和进度信息
    """
    try:
        task = ocr_service.get_task_status(task_id)
        if not task:
            raise HTTPException(
                status_code=404,
                detail="任务不存在"
            )
        
        return OCRTaskStatusResponse(
            task_id=task.task_id,
            status=task.status.value,
            progress=task.progress,
            result=task.result if task.status == OCRTaskStatus.COMPLETED else None,
            error=task.error if task.status == OCRTaskStatus.FAILED else None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取任务状态失败: {e}")
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取任务状态失败"
        )


@router.get("/task/{task_id}/result", response_model=OCRResultResponse)
async def get_task_result(task_id: str):
    """
    获取OCR任务结果
    
    - **task_id**: 任务ID
    
    返回识别结果
    """
    try:
        task = ocr_service.get_task_status(task_id)
        if not task:
            raise HTTPException(
                status_code=404,
                detail="任务不存在"
            )
        
        if task.status != OCRTaskStatus.COMPLETED:
            raise HTTPException(
                status_code=400,
                detail=f"任务尚未完成，当前状态: {task.status.value}"
            )
        
        return OCRResultResponse(
            task_id=task.task_id,
            result=task.result,
            model=task.model
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取任务结果失败: {e}")
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取任务结果失败"
        )


@router.delete("/task/{task_id}")
async def delete_task(task_id: str):
    """
    删除OCR任务
    
    - **task_id**: 任务ID
    """
    try:
        task = ocr_service.get_task_status(task_id)
        if not task:
            raise HTTPException(
                status_code=404,
                detail="任务不存在"
            )
        
        ocr_service.cleanup_task(task_id)
        
        return {"message": "任务已删除"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除任务失败: {e}")
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail="删除任务失败"
        )


@router.websocket("/ws/{task_id}")
async def websocket_task_status(websocket: WebSocket, task_id: str):
    """
    WebSocket连接，实时获取OCR任务状态
    
    - **task_id**: 任务ID
    
    实时推送任务状态更新
    """
    await websocket.accept()
    
    try:
        # 检查任务是否存在
        task = ocr_service.get_task_status(task_id)
        if not task:
            await websocket.send_json({
                "type": "error",
                "task_id": task_id,
                "data": {"error": "任务不存在"}
            })
            await websocket.close()
            return
        
        # 添加到WebSocket管理器
        await websocket_manager.connect(websocket, f"ocr_task_{task_id}")
        
        # 发送初始状态
        await websocket.send_json({
            "type": "status",
            "task_id": task_id,
            "data": {
                "status": task.status.value,
                "progress": task.progress
            }
        })
        
        # 监听任务状态变化
        while True:
            await asyncio.sleep(1)  # 每秒检查一次
            
            current_task = ocr_service.get_task_status(task_id)
            if not current_task:
                break
            
            # 发送状态更新
            await websocket.send_json({
                "type": "status",
                "task_id": task_id,
                "data": {
                    "status": current_task.status.value,
                    "progress": current_task.progress,
                    "result": current_task.result if current_task.status == OCRTaskStatus.COMPLETED else None,
                    "error": current_task.error if current_task.status == OCRTaskStatus.FAILED else None
                }
            })
            
            # 如果任务完成或失败，结束监听
            if current_task.status in [OCRTaskStatus.COMPLETED, OCRTaskStatus.FAILED]:
                await websocket.send_json({
                    "type": "complete",
                    "task_id": task_id,
                    "data": {"final_status": current_task.status.value}
                })
                break
    
    except WebSocketDisconnect:
        logger.info(f"WebSocket连接断开: task_id={task_id}")
    except Exception as e:
        logger.error(f"WebSocket错误: {e}")
        try:
            await websocket.send_json({
                "type": "error",
                "task_id": task_id,
                "data": {"error": str(e)}
            })
        except:
            pass
    finally:
        await websocket_manager.disconnect(websocket, f"ocr_task_{task_id}")