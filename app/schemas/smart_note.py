"""
智能笔记API数据模式定义
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum


class ProcessingStatus(str, Enum):
    """处理状态"""
    PENDING = "pending"
    OCR_PROCESSING = "ocr_processing"
    CORRECTION_PROCESSING = "correction_processing"
    SUMMARY_PROCESSING = "summary_processing"
    COMPLETED = "completed"
    FAILED = "failed"


class SmartNoteRequest(BaseModel):
    """智能笔记请求模型"""
    title: str = Field(default="", description="笔记标题（可选）")


class SmartNoteTextRequest(BaseModel):
    """智能笔记文字输入请求模型"""
    text: str = Field(description="要处理的文字内容")
    title: str = Field(default="", description="笔记标题（可选）")


class SmartNoteResponse(BaseModel):
    """智能笔记任务响应模型"""
    task_id: str = Field(description="任务ID")
    status: ProcessingStatus = Field(description="处理状态")
    message: str = Field(description="响应消息")


class SmartNoteStatusResponse(BaseModel):
    """智能笔记任务状态响应模型"""
    task_id: str = Field(description="任务ID")
    status: ProcessingStatus = Field(description="处理状态")
    progress: int = Field(description="处理进度 (0-100)")
    current_step: Optional[str] = Field(default=None, description="当前处理步骤")
    error: Optional[str] = Field(default=None, description="错误信息")
    content_id: Optional[int] = Field(default=None, description="内容ID（完成后可用）")


class SmartNoteResultResponse(BaseModel):
    """智能笔记结果响应模型"""
    task_id: str = Field(description="任务ID")
    ocr_result: Optional[str] = Field(description="OCR识别结果")
    corrected_result: Optional[str] = Field(description="纠错校正结果")
    summary_result: Optional[str] = Field(description="笔记总结结果")
    content_id: Optional[int] = Field(description="保存的内容ID")


class ProcessingStep(BaseModel):
    """处理步骤信息"""
    step: int = Field(description="步骤序号")
    name: str = Field(description="步骤名称")
    description: str = Field(description="步骤描述")


class ProcessingStepResponse(BaseModel):
    """处理步骤响应模型"""
    steps: List[ProcessingStep] = Field(description="处理步骤列表")


class SmartNoteWebSocketMessage(BaseModel):
    """WebSocket消息模型"""
    type: str = Field(description="消息类型: status, complete, error")
    task_id: str = Field(description="任务ID")
    data: Optional[Dict[str, Any]] = Field(default=None, description="消息数据")