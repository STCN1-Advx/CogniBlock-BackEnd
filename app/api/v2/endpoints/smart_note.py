"""
智能笔记API端点
提供OCR识别→纠错校正→笔记总结的完整工作流API
"""

import asyncio
import json
import logging
from typing import Optional
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends, Request
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.middleware.auth_middleware import require_session_auth
from app.models.user import User
from app.services.smart_note_service import smart_note_service
from app.schemas.smart_note import (
    SmartNoteRequest, SmartNoteResponse, SmartNoteStatusResponse,
    SmartNoteResultResponse, ProcessingStepResponse, SmartNoteWebSocketMessage,
    ProcessingStatus
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/process", response_model=SmartNoteResponse)
async def create_smart_note_task(
    file: UploadFile = File(..., description="要处理的图片文件"),
    title: str = Form("", description="笔记标题（可选）"),
    current_user: User = Depends(require_session_auth),
    db: Session = Depends(get_db)
):
    """
    创建智能笔记处理任务
    
    上传图片，自动执行：OCR识别 → 纠错校正 → 笔记总结 → 保存数据库
    """
    try:
        # 验证文件类型
        if not file.content_type or not file.content_type.startswith('image/'):
            raise HTTPException(status_code=400, detail="请上传图片文件")
        
        # 读取图片数据
        image_data = await file.read()
        
        if len(image_data) == 0:
            raise HTTPException(status_code=400, detail="图片文件为空")
        
        # 创建处理任务，传递用户信息
        task_id = await smart_note_service.create_task(
            image_data=image_data,
            title=title,
            filename=file.filename,
            user_id=str(current_user.id)  # 传递用户ID
        )
        
        return SmartNoteResponse(
            task_id=task_id,
            status=ProcessingStatus.PENDING.value,
            message="智能笔记处理任务已创建，正在处理中..."
        )
        
    except Exception as e:
        logger.error(f"创建智能笔记任务失败: {e}")
        raise HTTPException(status_code=500, detail=f"创建任务失败: {str(e)}")


@router.get("/task/{task_id}", response_model=SmartNoteStatusResponse)
async def get_task_status(task_id: str):
    """获取任务处理状态"""
    try:
        task = smart_note_service.get_task_status(task_id)
        
        if not task:
            raise HTTPException(status_code=404, detail="任务不存在")
        
        return SmartNoteStatusResponse(
            task_id=task["task_id"],
            status=task["status"],
            progress=task["progress"],
            current_step=task["current_step"],
            error=task.get("error_message"),
            content_id=task.get("result", {}).get("content_id") if task["status"] == "completed" else None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取任务状态失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取任务状态失败: {str(e)}")


@router.get("/task/{task_id}/result", response_model=SmartNoteResultResponse)
async def get_task_result(task_id: str):
    """获取任务处理结果"""
    try:
        task = smart_note_service.get_task_status(task_id)
        
        if not task:
            raise HTTPException(status_code=404, detail="任务不存在")
        
        if task["status"] != "completed":
            raise HTTPException(status_code=400, detail="任务尚未完成")
        
        result = task.get("result", {})
        
        return SmartNoteResultResponse(
            task_id=task["task_id"],
            ocr_result=result.get("ocr_text"),
            corrected_result=result.get("corrected_text"),
            summary_result=result.get("summary"),
            content_id=result.get("content_id")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取任务结果失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取任务结果失败: {str(e)}")


@router.delete("/task/{task_id}")
async def delete_task(task_id: str):
    """删除任务"""
    try:
        success = smart_note_service.delete_task(task_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="任务不存在")
        
        return {"message": "任务已删除"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除任务失败: {e}")
        raise HTTPException(status_code=500, detail=f"删除任务失败: {str(e)}")


@router.get("/steps", response_model=ProcessingStepResponse)
async def get_processing_steps():
    """获取处理步骤说明"""
    return ProcessingStepResponse(
        steps=[
            {
                "step": 1,
                "name": "OCR识别",
                "description": "使用PPInfra的Qwen2.5-VL模型识别图片中的文字，支持Markdown和LaTeX格式"
            },
            {
                "step": 2,
                "name": "纠错校正",
                "description": "使用DeepSeek-V3模型对OCR结果进行纠错和校正"
            },
            {
                "step": 3,
                "name": "笔记总结",
                "description": "使用Kimi-K2模型生成结构化的笔记总结"
            },
            {
                "step": 4,
                "name": "保存数据库",
                "description": "将处理结果保存到数据库中"
            }
        ]
    )


@router.get("/task/{task_id}/stream")
async def stream_task_progress(task_id: str):
    """流式获取任务处理进度和结果"""
    
    def serialize_task_data(task_data):
        """安全地序列化任务数据，过滤掉不能JSON序列化的字段"""
        if not task_data:
            return None
        
        # 创建一个新的字典，只包含可序列化的字段
        serializable_data = {}
        for key, value in task_data.items():
            # 跳过bytes类型的数据和其他不可序列化的数据
            if key in ['image_data']:  # 跳过图片数据
                continue
            elif isinstance(value, (str, int, float, bool, type(None))):
                serializable_data[key] = value
            elif isinstance(value, dict):
                # 递归处理字典
                serializable_data[key] = {k: v for k, v in value.items() 
                                        if isinstance(v, (str, int, float, bool, type(None), dict, list))}
            elif isinstance(value, list):
                # 处理列表
                serializable_data[key] = [item for item in value 
                                        if isinstance(item, (str, int, float, bool, type(None), dict))]
            else:
                # 对于其他类型，尝试转换为字符串
                try:
                    serializable_data[key] = str(value)
                except:
                    continue
        
        return serializable_data
    
    async def generate_stream():
        """生成SSE流数据"""
        try:
            # 检查任务是否存在
            task = smart_note_service.get_task_status(task_id)
            if not task:
                yield f"data: {json.dumps({'error': '任务不存在'})}\n\n"
                return
            
            # 发送初始状态（过滤掉不可序列化的数据）
            safe_task_data = serialize_task_data(task)
            yield f"data: {json.dumps({'type': 'status', 'data': safe_task_data})}\n\n"
            
            # 持续监控任务状态
            last_status = None
            last_progress = None
            last_step = None
            
            while True:
                try:
                    current_task = smart_note_service.get_task_status(task_id)
                    if not current_task:
                        yield f"data: {json.dumps({'error': '任务已被删除'})}\n\n"
                        break
                    
                    # 检查状态是否有变化
                    status_changed = (
                        current_task["status"] != last_status or
                        current_task["progress"] != last_progress or
                        current_task["current_step"] != last_step
                    )
                    
                    if status_changed:
                        # 发送状态更新
                        status_data = {
                            "task_id": current_task["task_id"],
                            "status": current_task["status"],
                            "progress": current_task["progress"],
                            "current_step": current_task["current_step"],
                            "error": current_task.get("error_message")
                        }
                        
                        yield f"data: {json.dumps({'type': 'status', 'data': status_data})}\n\n"
                        
                        last_status = current_task["status"]
                        last_progress = current_task["progress"]
                        last_step = current_task["current_step"]
                    
                    # 如果任务完成或失败，发送最终结果
                    if current_task["status"] in ["completed", "failed"]:
                        if current_task["status"] == "completed":
                            result = current_task.get("result", {})
                            result_data = {
                                "task_id": current_task["task_id"],
                                "ocr_result": result.get("ocr_text"),
                                "corrected_result": result.get("corrected_text"),
                                "summary_result": result.get("summary"),
                                "content_id": result.get("content_id")
                            }
                            yield f"data: {json.dumps({'type': 'complete', 'data': result_data})}\n\n"
                        else:
                            yield f"data: {json.dumps({'type': 'error', 'data': {'error': current_task.get('error_message', '处理失败')}})}\n\n"
                        
                        break
                    
                    # 等待0.5秒后继续检查
                    await asyncio.sleep(0.5)
                    
                except Exception as e:
                    logger.error(f"流式传输过程中出错: {e}")
                    yield f"data: {json.dumps({'error': f'流式传输错误: {str(e)}'})}\n\n"
                    break
                    
        except Exception as e:
            logger.error(f"流式传输初始化失败: {e}")
            yield f"data: {json.dumps({'error': f'流式传输失败: {str(e)}'})}\n\n"
    
    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "*",
        }
    )