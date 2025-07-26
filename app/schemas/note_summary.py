"""
笔记总结相关的数据模型和验证
"""

from typing import List, Optional
from pydantic import BaseModel, Field, validator
from datetime import datetime
from uuid import UUID


class NoteInput(BaseModel):
    """笔记输入模型"""
    title: str = Field(..., description="笔记标题", max_length=500)
    content: str = Field(..., description="笔记内容", min_length=1)
    
    @validator('content')
    def validate_content(cls, v):
        """验证笔记内容不能为空"""
        if not v or not v.strip():
            raise ValueError('笔记内容不能为空')
        return v.strip()
    
    class Config:
        json_schema_extra = {
            "example": {
                "title": "机器学习基础概念",
                "content": "机器学习是人工智能的一个分支，它使计算机能够在没有明确编程的情况下学习..."
            }
        }


class SummaryRequest(BaseModel):
    """笔记总结请求模型"""
    notes: List[NoteInput] = Field(..., description="笔记列表", min_items=1)
    min_notes_threshold: Optional[int] = Field(3, description="启用多笔记工作流的最小笔记数量", ge=1, le=10)
    
    @validator('notes')
    def validate_notes(cls, v):
        """验证笔记列表"""
        if not v:
            raise ValueError('笔记列表不能为空')
        
        # 过滤掉空内容的笔记
        valid_notes = [note for note in v if note.content and note.content.strip()]
        if not valid_notes:
            raise ValueError('至少需要一份有效的笔记内容')
        
        return valid_notes
    
    class Config:
        json_schema_extra = {
            "example": {
                "notes": [
                    {
                        "title": "机器学习基础",
                        "content": "机器学习是人工智能的一个分支..."
                    },
                    {
                        "title": "深度学习概念",
                        "content": "深度学习是机器学习的一个子集..."
                    }
                ],
                "min_notes_threshold": 3
            }
        }


class SummaryResult(BaseModel):
    """总结结果模型"""
    title: str = Field(..., description="总结标题")
    topic: str = Field(..., description="主要主题")
    content: str = Field(..., description="总结内容（Markdown格式）")
    confidence_scores: List[float] = Field(..., description="置信度分数列表")
    processing_method: str = Field(..., description="处理方法", pattern="^(single_summary|multi_note_workflow)$")
    
    class Config:
        json_schema_extra = {
            "example": {
                "title": "机器学习与深度学习综合总结",
                "topic": "人工智能基础概念",
                "content": "# 机器学习与深度学习\n\n## 核心概念\n\n机器学习是人工智能的重要分支...",
                "confidence_scores": [85.2, 72.1, 91.3],
                "processing_method": "multi_note_workflow"
            }
        }


class SummaryTask(BaseModel):
    """总结任务模型"""
    task_id: str = Field(..., description="任务ID")
    status: str = Field(..., description="任务状态", pattern="^(pending|processing|completed|failed)$")
    notes: List[NoteInput] = Field(..., description="输入的笔记列表")
    result: Optional[SummaryResult] = Field(None, description="总结结果")
    error_message: Optional[str] = Field(None, description="错误信息")
    created_at: datetime = Field(..., description="创建时间")
    completed_at: Optional[datetime] = Field(None, description="完成时间")
    
    class Config:
        json_schema_extra = {
            "example": {
                "task_id": "550e8400-e29b-41d4-a716-446655440000",
                "status": "completed",
                "notes": [
                    {
                        "title": "机器学习基础",
                        "content": "机器学习是人工智能的一个分支..."
                    }
                ],
                "result": {
                    "title": "机器学习基础总结",
                    "topic": "人工智能",
                    "content": "# 机器学习基础\n\n机器学习是人工智能的重要组成部分...",
                    "confidence_scores": [88.5],
                    "processing_method": "single_summary"
                },
                "error_message": None,
                "created_at": "2025-01-26T10:00:00Z",
                "completed_at": "2025-01-26T10:00:30Z"
            }
        }


class SummaryTaskResponse(BaseModel):
    """总结任务响应模型"""
    task_id: str = Field(..., description="任务ID")
    status: str = Field(..., description="任务状态")
    result: Optional[SummaryResult] = Field(None, description="总结结果")
    error_message: Optional[str] = Field(None, description="错误信息")
    created_at: datetime = Field(..., description="创建时间")
    completed_at: Optional[datetime] = Field(None, description="完成时间")
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "task_id": "550e8400-e29b-41d4-a716-446655440000",
                "status": "completed",
                "result": {
                    "title": "机器学习基础总结",
                    "topic": "人工智能",
                    "content": "# 机器学习基础\n\n机器学习是人工智能的重要组成部分...",
                    "confidence_scores": [88.5],
                    "processing_method": "single_summary"
                },
                "error_message": None,
                "created_at": "2025-01-26T10:00:00Z",
                "completed_at": "2025-01-26T10:00:30Z"
            }
        }


class SummaryTaskCreate(BaseModel):
    """创建总结任务响应模型"""
    task_id: str = Field(..., description="任务ID")
    status: str = Field(..., description="任务状态")
    message: str = Field(..., description="创建消息")
    
    class Config:
        json_schema_extra = {
            "example": {
                "task_id": "550e8400-e29b-41d4-a716-446655440000",
                "status": "pending",
                "message": "笔记总结任务已创建，正在处理中..."
            }
        }


class SummaryErrorResponse(BaseModel):
    """总结错误响应模型"""
    error: dict = Field(..., description="错误信息")
    task_id: Optional[str] = Field(None, description="任务ID")
    timestamp: datetime = Field(..., description="错误时间戳")
    
    class Config:
        json_schema_extra = {
            "example": {
                "error": {
                    "code": "PROCESSING_FAILED",
                    "message": "笔记处理失败",
                    "details": "AI服务暂时不可用，请稍后重试"
                },
                "task_id": "550e8400-e29b-41d4-a716-446655440000",
                "timestamp": "2025-01-26T10:00:00Z"
            }
        }