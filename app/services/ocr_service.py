"""
OCR服务
集成多模型OCR功能，支持并发处理和流式输出
"""

import asyncio
import logging
import os
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, AsyncIterator
from dataclasses import dataclass, field
from enum import Enum

from app.utils.multi_model_ocr import MultiModelOCR, ModelConfig

logger = logging.getLogger(__name__)


class OCRTaskStatus(Enum):
    """OCR任务状态"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class OCRTask:
    """OCR任务数据类"""
    task_id: str
    status: OCRTaskStatus
    model: str
    prompt: str
    created_at: datetime
    updated_at: datetime
    progress: int = 0
    result: Optional[str] = None
    error: Optional[str] = None
    image_data: Optional[bytes] = field(default=None, repr=False)


class OCRService:
    """OCR服务类"""
    
    def __init__(self):
        """初始化OCR服务"""
        self.tasks: Dict[str, OCRTask] = {}
        self.running_tasks: Dict[str, asyncio.Task] = {}
        self.ocr_client = None
        self._init_clients()
        
        # 启动清理任务
        asyncio.create_task(self._cleanup_expired_tasks())
    
    def _init_clients(self):
        """初始化OCR客户端"""
        try:
            # 从环境变量获取配置
            gemini_api_key = os.getenv("GEMINI_API_KEY")
            qwen_api_key = os.getenv("QWEN_API_KEY")
            qwen_base_url = os.getenv("QWEN_BASE_URL")
            ppinfra_api_key = os.getenv("PPINFRA_API_KEY")
            ppinfra_base_url = os.getenv("PPINFRA_BASE_URL")
            
            self.ocr_client = MultiModelOCR(
                gemini_api_key=gemini_api_key,
                qwen_api_key=qwen_api_key,
                qwen_base_url=qwen_base_url,
                ppinfra_api_key=ppinfra_api_key,
                ppinfra_base_url=ppinfra_base_url
            )
            logger.info("OCR客户端初始化成功")
        except Exception as e:
            logger.error(f"OCR客户端初始化失败: {e}")
            self.ocr_client = None
    
    def get_available_models(self) -> Dict[str, Dict[str, Any]]:
        """获取可用的OCR模型"""
        if not self.ocr_client:
            return {}
        
        try:
            return self.ocr_client.get_available_models()
        except Exception as e:
            logger.error(f"获取可用模型失败: {e}")
            return {}
    
    def _validate_model(self, model: str) -> bool:
        """验证模型是否可用"""
        available_models = self.get_available_models()
        return model in available_models and available_models[model].get("available", False)
    
    async def create_task(self, 
                         image_data: bytes, 
                         model: str, 
                         prompt: str) -> str:
        """
        创建OCR任务
        
        Args:
            image_data: 图片数据
            model: 使用的模型
            prompt: 提示词
            
        Returns:
            任务ID
        """
        if not self.ocr_client:
            raise Exception("OCR服务未初始化")
        
        if not self._validate_model(model):
            raise Exception(f"模型 {model} 不可用")
        
        # 生成任务ID
        task_id = str(uuid.uuid4())
        
        # 创建任务
        task = OCRTask(
            task_id=task_id,
            status=OCRTaskStatus.PENDING,
            model=model,
            prompt=prompt,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            image_data=image_data
        )
        
        self.tasks[task_id] = task
        
        # 异步执行任务
        async_task = asyncio.create_task(self._process_task(task_id))
        self.running_tasks[task_id] = async_task
        
        logger.info(f"OCR任务已创建: {task_id}, 模型: {model}")
        return task_id
    
    async def _process_task(self, task_id: str):
        """处理OCR任务"""
        task = self.tasks.get(task_id)
        if not task:
            return
        
        try:
            # 更新任务状态
            task.status = OCRTaskStatus.PROCESSING
            task.progress = 10
            task.updated_at = datetime.now()
            
            logger.info(f"开始处理OCR任务: {task_id}")
            
            # 执行OCR识别
            task.progress = 50
            result = self.ocr_client.extract_text(
                image_source=task.image_data,
                prompt=task.prompt,
                model=task.model
            )
            
            # 任务完成
            task.status = OCRTaskStatus.COMPLETED
            task.progress = 100
            task.result = result
            task.updated_at = datetime.now()
            
            logger.info(f"OCR任务完成: {task_id}")
            
        except Exception as e:
            # 任务失败
            task.status = OCRTaskStatus.FAILED
            task.error = str(e)
            task.updated_at = datetime.now()
            
            logger.error(f"OCR任务失败: {task_id}, 错误: {e}")
        
        finally:
            # 清理运行中的任务记录
            if task_id in self.running_tasks:
                del self.running_tasks[task_id]
            
            # 清理图片数据以节省内存
            if task.image_data:
                task.image_data = None
    
    async def process_ocr_stream(self, 
                                image_data: bytes, 
                                model: str, 
                                prompt: str) -> AsyncIterator[str]:
        """
        流式处理OCR
        
        Args:
            image_data: 图片数据
            model: 使用的模型
            prompt: 提示词
            
        Yields:
            文字内容片段
        """
        if not self.ocr_client:
            raise Exception("OCR服务未初始化")
        
        if not self._validate_model(model):
            raise Exception(f"模型 {model} 不可用")
        
        try:
            logger.info(f"开始流式OCR处理，模型: {model}")
            
            # 使用同步生成器，在异步环境中逐个yield
            for chunk in self.ocr_client.extract_text_stream(
                image_source=image_data,
                prompt=prompt,
                model=model
            ):
                yield chunk
                # 让出控制权，避免阻塞事件循环
                await asyncio.sleep(0)
            
            logger.info("流式OCR处理完成")
            
        except Exception as e:
            logger.error(f"流式OCR处理失败: {e}")
            raise Exception(f"流式OCR处理失败: {str(e)}")
    
    def get_task_status(self, task_id: str) -> Optional[OCRTask]:
        """获取任务状态"""
        return self.tasks.get(task_id)
    
    def cleanup_task(self, task_id: str):
        """清理任务"""
        if task_id in self.tasks:
            del self.tasks[task_id]
        
        if task_id in self.running_tasks:
            # 取消正在运行的任务
            self.running_tasks[task_id].cancel()
            del self.running_tasks[task_id]
        
        logger.info(f"任务已清理: {task_id}")
    
    async def _cleanup_expired_tasks(self):
        """清理过期任务"""
        while True:
            try:
                current_time = datetime.now()
                expired_tasks = []
                
                for task_id, task in self.tasks.items():
                    # 清理1小时前的已完成或失败任务
                    if (task.status in [OCRTaskStatus.COMPLETED, OCRTaskStatus.FAILED] and
                        current_time - task.updated_at > timedelta(hours=1)):
                        expired_tasks.append(task_id)
                    
                    # 清理24小时前的所有任务
                    elif current_time - task.created_at > timedelta(hours=24):
                        expired_tasks.append(task_id)
                
                # 清理过期任务
                for task_id in expired_tasks:
                    self.cleanup_task(task_id)
                
                if expired_tasks:
                    logger.info(f"清理了 {len(expired_tasks)} 个过期任务")
                
            except Exception as e:
                logger.error(f"清理过期任务失败: {e}")
            
            # 每10分钟清理一次
            await asyncio.sleep(600)


# 全局OCR服务实例
ocr_service = OCRService()