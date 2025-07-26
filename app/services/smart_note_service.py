"""智能笔记处理服务

集成OCR识别、纠错校正和笔记总结的完整工作流
"""

import asyncio
import json
import logging
import time
import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime

from sqlalchemy.orm import Session
from app.models.content import Content
from app.utils.multi_model_ocr import MultiModelOCR

from app.core.config import settings

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)





class SmartNoteService:
    """智能笔记处理服务"""
    
    def __init__(self):
        """初始化服务"""
        self.tasks: Dict[str, Dict[str, Any]] = {}
        
        # 初始化客户端
        self._init_clients()
        
        # 处理步骤定义
        self.processing_steps = [
            {"step": "ocr_recognition", "name": "OCR识别", "description": "使用PPInfra Qwen2.5-VL进行图片文字识别"},
            {"step": "error_correction", "name": "纠错校正", "description": "使用DeepSeek-V3进行文本纠错"},
            {"step": "note_summary", "name": "笔记总结", "description": "使用Kimi-K2生成笔记总结"},
            {"step": "save_to_database", "name": "保存到数据库", "description": "将结果保存到数据库"}
        ]
    
    def _init_clients(self):
        """初始化AI客户端"""
        try:
            import os
            
            # 初始化OCR客户端
            self.ocr_client = MultiModelOCR(
                gemini_api_key=os.getenv("GEMINI_API_KEY"),
                qwen_api_key=os.getenv("QWEN_API_KEY"),
                qwen_base_url=os.getenv("QWEN_BASE_URL"),
                ppinfra_api_key=os.getenv("PPINFRA_API_KEY"),
                ppinfra_base_url=os.getenv("PPINFRA_BASE_URL")
            )
            
            # 初始化PPINFRA客户端（用于DeepSeek和Kimi）
            from openai import OpenAI
            ppinfra_api_key = os.getenv("PPINFRA_API_KEY")
            ppinfra_base_url = os.getenv("PPINFRA_BASE_URL", "https://api.ppinfra.com/v3/openai")
            
            if ppinfra_api_key:
                # DeepSeek和Kimi都使用PPINFRA
                self.deepseek_client = OpenAI(
                    api_key=ppinfra_api_key,
                    base_url=ppinfra_base_url
                )
                self.kimi_client = OpenAI(
                    api_key=ppinfra_api_key,
                    base_url=ppinfra_base_url
                )
            else:
                logger.warning("PPINFRA API密钥未配置，DeepSeek和Kimi功能将不可用")
                self.deepseek_client = None
                self.kimi_client = None
            
            logger.info("AI客户端初始化成功")
            
        except Exception as e:
            logger.error(f"AI客户端初始化失败: {e}")
            raise
    
    async def create_task(self, image_data: bytes, title: Optional[str] = None, filename: Optional[str] = None, user_id: Optional[str] = None) -> str:
        """创建智能笔记处理任务"""
        task_id = str(uuid.uuid4())
        
        # 创建任务记录
        self.tasks[task_id] = {
            "task_id": task_id,
            "status": "pending",
            "current_step": None,
            "progress": 0.0,
            "image_data": image_data,
            "title": title,
            "filename": filename,
            "user_id": user_id,  # 添加用户ID
            "result": None,
            "error_message": None,
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }
        
        # 启动异步处理
        asyncio.create_task(self._process_task(task_id))
        
        return task_id
    
    async def _process_task(self, task_id: str):
        """处理智能笔记任务"""
        try:
            await self._update_task_status(task_id, "processing", "ocr_recognition", 10.0)
            
            # 步骤1: OCR识别
            ocr_result = await self._perform_ocr(task_id)
            if not ocr_result:
                return
            
            await self._update_task_status(task_id, "processing", "error_correction", 40.0)
            
            # 步骤2: 纠错校正
            corrected_text = await self._perform_error_correction(task_id, ocr_result)
            if not corrected_text:
                return
            
            await self._update_task_status(task_id, "processing", "note_summary", 70.0)
            
            # 步骤3: 笔记总结
            summary_result = await self._perform_note_summary(task_id, corrected_text)
            if not summary_result:
                return
            
            await self._update_task_status(task_id, "processing", "save_to_database", 90.0)
            
            # 步骤4: 保存到数据库
            content_id = await self._save_to_database(task_id, ocr_result, corrected_text, summary_result)
            if not content_id:
                return
            
            # 完成任务
            self.tasks[task_id]["result"] = {
                "content_id": content_id,
                "ocr_text": ocr_result,
                "corrected_text": corrected_text,
                "summary": summary_result
            }
            
            await self._update_task_status(task_id, "completed", None, 100.0)
            
        except Exception as e:
            logger.error(f"任务处理失败 {task_id}: {e}")
            await self._update_task_status(task_id, "failed", None, 0.0, str(e))
    
    async def _perform_ocr(self, task_id: str) -> Optional[str]:
        """执行OCR识别"""
        try:
            task = self.tasks[task_id]
            image_data = task["image_data"]
            
            # 使用PPInfra的Qwen2.5-VL模型进行OCR
            result = self.ocr_client.extract_text(
                image_source=image_data,
                model="qwen/qwen2.5-vl-72b-instruct",
                prompt="请识别图片中的所有文字内容，包括数学公式、表格等。保持原有的格式和结构，对于数学公式请使用LaTeX格式表示。"
            )
            
            if result and result.strip():
                return result.strip()
            else:
                raise Exception("OCR识别失败，未获取到文本内容")
                
        except Exception as e:
            logger.error(f"OCR识别失败 {task_id}: {e}")
            await self._update_task_status(task_id, "failed", "ocr_recognition", 0.0, f"OCR识别失败: {e}")
            return None
    
    async def _perform_error_correction(self, task_id: str, ocr_text: str) -> Optional[str]:
        """执行纠错校正"""
        try:
            prompt = f"""请对以下OCR识别的文本进行纠错校正，修正可能的识别错误，但保持原有的格式和结构：

原始文本：
{ocr_text}

请返回纠错后的文本，要求：
1. 修正明显的OCR识别错误
2. 保持原有的段落结构和格式
3. 对于数学公式，确保LaTeX语法正确
4. 不要添加额外的内容，只进行纠错
"""
            
            response = self.deepseek_client.chat.completions.create(
                model="deepseek/deepseek-v3",
                messages=[
                    {"role": "system", "content": "你是一个专业的文本纠错专家，擅长修正OCR识别错误。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1
            )
            
            corrected_text = response.choices[0].message.content.strip()
            return corrected_text
            
        except Exception as e:
            logger.error(f"纠错校正失败 {task_id}: {e}")
            await self._update_task_status(task_id, "failed", "error_correction", 0.0, f"纠错校正失败: {e}")
            return None
    
    async def _perform_note_summary(self, task_id: str, corrected_text: str) -> Optional[Dict[str, Any]]:
        """执行笔记总结"""
        try:
            task = self.tasks[task_id]
            title = task.get("title", "智能笔记")
            
            prompt = f"""请对以下文本内容进行笔记总结，生成结构化的学习笔记：

原始内容：
{corrected_text}

请按照以下格式生成总结：
1. 提取主要主题和关键概念
2. 整理知识点结构
3. 生成Markdown格式的总结内容
4. 提取关键词

要求：
- 保持数学公式的LaTeX格式
- 使用清晰的Markdown结构
- 突出重点内容
- 适合学习和复习使用
"""
            
            response = self.kimi_client.chat.completions.create(
                model="moonshotai/kimi-k2-instruct",
                messages=[
                    {"role": "system", "content": "你是一个专业的学习笔记整理专家，擅长将复杂内容整理成结构化的学习材料。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3
            )
            
            summary_content = response.choices[0].message.content.strip()
            
            # 提取关键词
            keywords_prompt = f"请从以下内容中提取5-10个关键词，用逗号分隔：\n{corrected_text}"
            keywords_response = self.kimi_client.chat.completions.create(
                model="moonshotai/kimi-k2-instruct",
                messages=[
                    {"role": "system", "content": "你是一个关键词提取专家。"},
                    {"role": "user", "content": keywords_prompt}
                ],
                temperature=0.1
            )
            
            keywords = keywords_response.choices[0].message.content.strip()
            
            return {
                "title": title,
                "content": summary_content,
                "keywords": keywords
            }
            
        except Exception as e:
            logger.error(f"笔记总结失败 {task_id}: {e}")
            await self._update_task_status(task_id, "failed", "note_summary", 0.0, f"笔记总结失败: {e}")
            return None
    
    async def _save_to_database(self, task_id: str, ocr_text: str, corrected_text: str, summary_result: Dict[str, Any]) -> Optional[int]:
        """保存到数据库"""
        try:
            from app.db.session import get_db
            from app.models.content import Content
            from app.models.user_content import UserContent
            import uuid
            
            # 获取数据库会话
            db = next(get_db())
            
            task = self.tasks[task_id]
            user_id = task.get("user_id")
            
            if not user_id:
                raise Exception("缺少用户ID，无法保存到数据库")
            
            # 创建Content记录
            content = Content(
                content_type="image",
                image_data=task["image_data"],
                text_data=corrected_text,  # 存储纠错后的文本
                filename=task.get("filename"),
                summary_title=summary_result["title"],
                summary_content=summary_result["content"],
                summary_status="completed"
            )
            
            db.add(content)
            db.commit()
            db.refresh(content)
            
            # 创建UserContent记录，关联用户和内容
            user_content = UserContent(
                user_id=uuid.UUID(user_id),
                content_id=content.id,
                permission="owner"  # 创建者拥有所有权限
            )
            
            db.add(user_content)
            db.commit()
            
            logger.info(f"内容已保存到数据库，ID: {content.id}，用户: {user_id}")
            return content.id
            
        except Exception as e:
            logger.error(f"保存到数据库失败 {task_id}: {e}")
            await self._update_task_status(task_id, "failed", "save_to_database", 0.0, f"保存到数据库失败: {e}")
            return None
        finally:
            if 'db' in locals():
                db.close()
    
    async def _update_task_status(self, task_id: str, status: str, current_step: Optional[str] = None, 
                                progress: float = 0.0, error_message: Optional[str] = None):
        """更新任务状态"""
        if task_id in self.tasks:
            self.tasks[task_id].update({
                "status": status,
                "current_step": current_step,
                "progress": progress,
                "error_message": error_message,
                "updated_at": datetime.now()
            })
            
            if status == "completed":
                self.tasks[task_id]["completed_at"] = datetime.now()
            
            # 注意：WebSocket状态更新由WebSocket端点的轮询机制处理
            # 这里不需要主动发送WebSocket消息，因为连接是基于task_id的
            logger.info(f"任务 {task_id} 状态更新: {status} - {current_step} ({progress}%)")
    
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务状态"""
        return self.tasks.get(task_id)
    
    def get_task_result(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务结果"""
        task = self.tasks.get(task_id)
        if task and task["status"] == "completed":
            return task["result"]
        return None
    
    def delete_task(self, task_id: str) -> bool:
        """删除任务"""
        if task_id in self.tasks:
            del self.tasks[task_id]
            return True
        return False
    
    def get_processing_steps(self) -> List[Dict[str, str]]:
        """获取处理步骤说明"""
        return self.processing_steps


# 全局服务实例
smart_note_service = SmartNoteService()