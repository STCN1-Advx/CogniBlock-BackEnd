"""
OCR API 数据模式定义
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum


class OCRModel(str, Enum):
    """支持的OCR模型"""
    GEMINI_2_5_PRO = "gemini-2.5-pro"
    GEMINI_2_0_FLASH = "gemini-2.0-flash-exp"
    QWEN_VL_PLUS = "qwen-vl-plus"
    QWEN_VL_MAX = "qwen-vl-max-latest"
    QWEN_2_5_VL_72B = "qwen/qwen2.5-vl-72b-instruct"


class OCRTaskStatus(str, Enum):
    """OCR任务状态"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class OCRRequest(BaseModel):
    """OCR请求模型"""
    model: OCRModel = Field(default=OCRModel.GEMINI_2_0_FLASH, description="使用的OCR模型")
    prompt: str = Field(
        default="请提取这张图片中的所有文字内容，保持原有的格式和布局。",
        description="OCR提示词"
    )
    stream: bool = Field(default=False, description="是否使用流式输出")


class OCRTaskResponse(BaseModel):
    """OCR任务响应模型"""
    task_id: str = Field(description="任务ID")
    status: OCRTaskStatus = Field(description="任务状态")
    message: str = Field(description="响应消息")


class OCRTaskStatusResponse(BaseModel):
    """OCR任务状态响应模型"""
    task_id: str = Field(description="任务ID")
    status: OCRTaskStatus = Field(description="任务状态")
    progress: int = Field(description="处理进度 (0-100)")
    result: Optional[str] = Field(default=None, description="识别结果")
    error: Optional[str] = Field(default=None, description="错误信息")


class OCRResultResponse(BaseModel):
    """OCR结果响应模型"""
    task_id: str = Field(description="任务ID")
    result: str = Field(description="识别结果")
    model: str = Field(description="使用的模型")


class OCRStreamChunk(BaseModel):
    """OCR流式响应块"""
    chunk: str = Field(description="文本片段")
    finished: bool = Field(default=False, description="是否完成")


class ModelInfo(BaseModel):
    """模型信息"""
    name: str = Field(description="模型名称")
    provider: str = Field(description="提供商")
    supports_stream: bool = Field(description="是否支持流式输出")
    description: str = Field(description="模型描述")
    available: bool = Field(default=False, description="模型是否可用")


class ModelsResponse(BaseModel):
    """模型列表响应"""
    models: List[ModelInfo] = Field(..., description="可用模型列表")


class OCRWebSocketMessage(BaseModel):
    """WebSocket消息模型"""
    type: str = Field(description="消息类型: status, chunk, error, complete")
    task_id: str = Field(description="任务ID")
    data: Optional[Dict[str, Any]] = Field(default=None, description="消息数据")