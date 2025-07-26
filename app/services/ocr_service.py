"""
OCR服务模块
提供图片OCR识别功能，支持多并发处理和WebSocket通知
"""

import asyncio
import base64
import io
import logging
import os
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Optional, Sequence
from PIL import Image
import json
from datetime import datetime

from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential_jitter
from app.core.config import settings
from app.utils.image_processing import (
    preprocess_image_color,
    preprocess_image_to_grayscale,
    auto_crop_document,
    enhance_text_clarity
)
from app.utils.markdown_utils import extract_codeblock, clean_markdown_text
from app.db.session import get_db
from app.models.content import Content

logger = logging.getLogger(__name__)

class OCRTaskItem:
    """OCR任务项"""
    def __init__(self, task_id: str, image_data: bytes, filename: str, content_type: str):
        self.task_id = task_id
        self.image_data = image_data
        self.filename = filename
        self.content_type = content_type
        self.status = "pending"  # pending, processing, completed, failed, cancelled
        self.description = "等待处理"
        self.markdown_result = ""
        self.html_result = ""
        self.error_message = ""
        self.progress = 0
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
        self.content_id = None  # 数据库内容ID
        self.user_id = None  # 用户ID

class OCRProcessor:
    """OCR处理器"""
    
    def __init__(self):
        # 从环境变量读取配置
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.base_url = os.getenv("OPENAI_BASE_URL")
        self.models = {
            "grayscale": os.getenv("OCR_AI_MODEL_GRAYSCALE", "gemini-2.0-flash"),
            "color": os.getenv("OCR_AI_MODEL_COLOR", "gpt-4o"),
            "merge": os.getenv("OCR_AI_MODEL_MERGE", "gpt-4o"),
            "final": os.getenv("OCR_AI_MODEL_FINAL", "gpt-4o")
        }
        
        # 读取提示词
        prompt_file = os.getenv("OCR_PROMPT_FILE", "./prompts/ocr_prompt.txt")
        try:
            with open(prompt_file, "r", encoding="utf-8") as f:
                self.prompt = f.read()
        except FileNotFoundError:
            # 默认提示词
            self.prompt = """你是一个专业的OCR助手。请将图片中的文字内容转换为markdown格式。
要求：
1. 保持原有的格式和结构
2. 识别标题、列表、表格等元素
3. 输出纯净的markdown格式
4. 如果有数学公式，使用LaTeX格式"""
        
        self.client = OpenAI(base_url=self.base_url, api_key=self.api_key)
    
    def compress_image(self, image_data: bytes, max_area: int = None) -> bytes:
        """压缩图片"""
        if max_area is None:
            max_area = int(os.getenv("OCR_MAX_IMAGE_AREA", "2073600"))  # 默认2MP
        
        try:
            image = Image.open(io.BytesIO(image_data))
            
            # 计算当前面积
            current_area = image.width * image.height
            
            if current_area <= max_area:
                return image_data
            
            # 计算缩放比例
            scale = (max_area / current_area) ** 0.5
            new_width = int(image.width * scale)
            new_height = int(image.height * scale)
            
            # 缩放图片
            resized_image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            # 保存为字节
            output = io.BytesIO()
            format_name = image.format or 'JPEG'
            resized_image.save(output, format=format_name, quality=85)
            
            return output.getvalue()
        except Exception as e:
            logger.error(f"图片压缩失败: {e}")
            return image_data
    
    def preprocess_image(self, image_data: bytes) -> tuple[bytes, bytes]:
        """预处理图片，返回彩色和灰度版本"""
        try:
            # 自动裁剪文档边界
            cropped_data = auto_crop_document(image_data)
            
            # 彩色版本预处理
            color_data = preprocess_image_color(cropped_data, "image/jpeg")
            
            # 灰度版本预处理
            grayscale_data = preprocess_image_to_grayscale(color_data, "image/jpeg")
            
            # 增强文字清晰度
            enhanced_grayscale = enhance_text_clarity(grayscale_data)
            
            return color_data, enhanced_grayscale
        except Exception as e:
            logger.error(f"图片预处理失败: {e}")
            return image_data, image_data
    
    def encode_image(self, image_data: bytes) -> str:
        """编码图片为base64"""
        return base64.b64encode(image_data).decode()
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential_jitter(initial=1, max=8))
    def call_ai(self, messages: Sequence[Dict], model: str) -> str:
        """调用AI接口"""
        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=list(messages)
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"AI调用失败: {e}")
            raise
    
    def process_image_with_ai(self, image_data: bytes, mimetype: str, model: str, prompt_suffix: str = "") -> str:
        """使用AI处理单张图片"""
        messages = [
            {"role": "system", "content": self.prompt + prompt_suffix},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "请将这张图片中的内容转换为markdown格式。"},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:{mimetype};base64,{self.encode_image(image_data)}"}
                    }
                ]
            }
        ]
        return self.call_ai(messages, model)
    
    def merge_texts(self, text1: str, text2: str, model: str) -> str:
        """合并两个文本"""
        messages = [
            {"role": "system", "content": self.prompt},
            {
                "role": "user", 
                "content": f"请合并以下两个OCR识别结果，生成最准确的markdown内容：\n\n结果1：\n{text1}\n\n结果2：\n{text2}"
            }
        ]
        return self.call_ai(messages, model)
    
    def final_correction(self, text: str, image_data: bytes, mimetype: str, model: str) -> str:
        """最终校正"""
        messages = [
            {"role": "system", "content": self.prompt},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": f"请根据图片校正以下markdown内容：\n\n{text}"},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:{mimetype};base64,{self.encode_image(image_data)}"}
                    }
                ]
            }
        ]
        return self.call_ai(messages, model)
    
    def extract_markdown(self, text: str) -> str:
        """提取markdown内容"""
        # 使用工具函数提取代码块内容
        markdown_content = extract_codeblock(text)
        
        # 清理markdown文本
        cleaned_content = clean_markdown_text(markdown_content)
        
        return cleaned_content

class OCRService:
    """OCR服务"""
    
    def __init__(self):
        self.tasks: Dict[str, OCRTaskItem] = {}
        self.processor = OCRProcessor()
        
        # 配置线程池
        max_workers = int(os.getenv("OCR_WORKER_THREADS", "2"))
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        
        # WebSocket连接管理
        self.websocket_connections: Dict[str, set] = {}  # task_id -> set of websockets
        
        # 启用模拟模式检查
        self.enable_mock = os.getenv("OCR_ENABLE_MOCK", "false").lower() == "true"
    
    def generate_task_id(self) -> str:
        """生成任务ID"""
        return str(uuid.uuid4())
    
    async def add_websocket_connection(self, task_id: str, websocket):
        """添加WebSocket连接"""
        if task_id not in self.websocket_connections:
            self.websocket_connections[task_id] = set()
        self.websocket_connections[task_id].add(websocket)
    
    async def remove_websocket_connection(self, task_id: str, websocket):
        """移除WebSocket连接"""
        if task_id in self.websocket_connections:
            self.websocket_connections[task_id].discard(websocket)
            if not self.websocket_connections[task_id]:
                del self.websocket_connections[task_id]
    
    async def notify_websockets(self, task_id: str, message: dict):
        """通知WebSocket客户端"""
        if task_id in self.websocket_connections:
            disconnected = set()
            for websocket in self.websocket_connections[task_id]:
                try:
                    await websocket.send_text(json.dumps(message, ensure_ascii=False))
                except Exception as e:
                    logger.error(f"WebSocket发送失败: {e}")
                    disconnected.add(websocket)
            
            # 移除断开的连接
            for websocket in disconnected:
                self.websocket_connections[task_id].discard(websocket)
    
    async def update_task_status(self, task_id: str, status: str, description: str, progress: int = 0, result: str = ""):
        """更新任务状态并通知客户端"""
        if task_id in self.tasks:
            task = self.tasks[task_id]
            task.status = status
            task.description = description
            task.progress = progress
            task.updated_at = datetime.now()
            
            if result:
                task.markdown_result = result
                # 简单转换为HTML（可以后续改进）
                task.html_result = f"<pre>{result}</pre>"
            
            # 通知WebSocket客户端
            message = {
                "type": "status",
                "task_id": task_id,
                "status": status,
                "description": description,
                "progress": progress
            }
            
            if status == "completed" and result:
                message.update({
                    "type": "completed",
                    "result": {
                        "markdown": task.markdown_result,
                        "html": task.html_result
                    }
                })
            elif status == "failed":
                message.update({
                    "type": "failed",
                    "error": task.error_message
                })
            
            await self.notify_websockets(task_id, message)
    
    def process_task_sync(self, task_id: str):
        """同步处理任务（在线程池中运行）"""
        try:
            task = self.tasks[task_id]
            task.status = "processing"
            
            if self.enable_mock:
                # 模拟模式
                import time
                asyncio.run(self.update_task_status(task_id, "processing", "模拟处理中...", 10))
                time.sleep(2)
                asyncio.run(self.update_task_status(task_id, "processing", "模拟处理中...", 50))
                time.sleep(2)
                markdown_result = "# 模拟OCR结果\n\n这是一个模拟的OCR识别结果。"
                asyncio.run(self.update_task_status(task_id, "completed", "处理完成", 100, markdown_result))
                
                # 更新数据库
                if task.content_id and task.user_id:
                    asyncio.run(self.update_database(task.content_id, markdown_result))
                return
            
            # 1. 压缩图片
            asyncio.run(self.update_task_status(task_id, "processing", "压缩图片中...", 10))
            compressed_data = self.processor.compress_image(task.image_data)
            
            # 2. 预处理图片
            asyncio.run(self.update_task_status(task_id, "processing", "预处理图片中...", 20))
            color_data, grayscale_data = self.processor.preprocess_image(compressed_data)
            
            # 3. AI处理 - 并行处理彩色和灰度图片
            asyncio.run(self.update_task_status(task_id, "processing", "AI识别中...", 30))
            
            # 并行处理
            future_color = self.executor.submit(
                self.processor.process_image_with_ai,
                color_data, task.content_type, self.processor.models["color"]
            )
            future_grayscale = self.executor.submit(
                self.processor.process_image_with_ai,
                grayscale_data, task.content_type, self.processor.models["grayscale"]
            )
            
            color_result = future_color.result()
            grayscale_result = future_grayscale.result()
            
            # 4. 合并结果
            asyncio.run(self.update_task_status(task_id, "processing", "合并识别结果...", 60))
            merged_result = self.processor.merge_texts(
                color_result, grayscale_result, self.processor.models["merge"]
            )
            
            # 5. 最终校正
            asyncio.run(self.update_task_status(task_id, "processing", "最终校正中...", 80))
            final_result = self.processor.final_correction(
                merged_result, color_data, task.content_type, self.processor.models["final"]
            )
            
            # 6. 提取markdown
            asyncio.run(self.update_task_status(task_id, "processing", "提取markdown...", 90))
            markdown_result = self.processor.extract_markdown(final_result)
            
            # 7. 更新数据库
            if task.content_id and task.user_id:
                asyncio.run(self.update_task_status(task_id, "processing", "保存到数据库...", 95))
                asyncio.run(self.update_database(task.content_id, markdown_result))
            
            # 8. 完成
            asyncio.run(self.update_task_status(task_id, "completed", "处理完成", 100, markdown_result))
            
        except Exception as e:
            logger.error(f"任务处理失败 {task_id}: {e}")
            task = self.tasks[task_id]
            task.status = "failed"
            task.error_message = str(e)
            
            # 如果有content_id，更新数据库中的OCR状态为失败
            if task.content_id:
                try:
                    db = next(get_db())
                    try:
                        content = db.query(Content).filter(Content.id == task.content_id).first()
                        if content:
                            content.ocr_status = "failed"
                            content.updated_at = datetime.now()
                            db.commit()
                            logger.info(f"已将内容 {task.content_id} 的OCR状态设置为失败")
                    finally:
                        db.close()
                except Exception as db_e:
                    logger.error(f"更新数据库OCR状态失败: {db_e}")
            
            asyncio.run(self.update_task_status(task_id, "failed", f"处理失败: {str(e)}", 0))
    
    async def update_database(self, content_id: str, markdown_result: str):
        """更新数据库中的内容"""
        try:
            # 获取数据库会话
            db = next(get_db())
            try:
                # 查找内容
                content = db.query(Content).filter(Content.id == content_id).first()
                if content:
                    # 更新内容 - 使用正确的字段名
                    content.ocr_result = markdown_result
                    content.ocr_status = "completed"  # 更新OCR状态
                    content.updated_at = datetime.now()
                    db.commit()
                    logger.info(f"已更新数据库内容 {content_id}，OCR结果长度: {len(markdown_result)}")
                else:
                    logger.warning(f"未找到内容 {content_id}")
            finally:
                db.close()
        except Exception as e:
            logger.error(f"更新数据库失败: {e}")
            # 如果数据库更新失败，也要更新OCR状态为失败
            try:
                db = next(get_db())
                try:
                    content = db.query(Content).filter(Content.id == content_id).first()
                    if content:
                        content.ocr_status = "failed"
                        content.updated_at = datetime.now()
                        db.commit()
                        logger.info(f"已将内容 {content_id} 的OCR状态设置为失败")
                finally:
                    db.close()
            except Exception as inner_e:
                logger.error(f"更新OCR状态为失败时出错: {inner_e}")

    async def submit_task(self, image_data: bytes, filename: str, content_type: str, content_id: str = None, user_id: str = None) -> str:
        """提交OCR任务"""
        task_id = self.generate_task_id()
        
        # 创建任务
        task = OCRTaskItem(task_id, image_data, filename, content_type)
        task.content_id = content_id  # 添加content_id
        task.user_id = user_id  # 添加user_id
        self.tasks[task_id] = task
        
        # 提交到线程池处理
        self.executor.submit(self.process_task_sync, task_id)
        
        return task_id
    
    async def get_task(self, task_id: str) -> Optional[OCRTaskItem]:
        """获取任务"""
        return self.tasks.get(task_id)
    
    async def remove_task(self, task_id: str) -> bool:
        """删除任务"""
        if task_id in self.tasks:
            del self.tasks[task_id]
            # 清理WebSocket连接
            if task_id in self.websocket_connections:
                del self.websocket_connections[task_id]
            return True
        return False
    
    async def get_service_status(self) -> Dict:
        """获取服务状态"""
        return {
            "total_tasks": len(self.tasks),
            "active_connections": sum(len(conns) for conns in self.websocket_connections.values()),
            "mock_mode": self.enable_mock
        }
    
    async def cancel_task(self, task_id: str) -> bool:
        """取消OCR任务"""
        if task_id in self.tasks:
            task = self.tasks[task_id]
            if task.status in ["pending", "processing"]:
                task.status = "cancelled"
                task.description = "任务已取消"
                task.updated_at = datetime.now()
                
                # 通知WebSocket连接
                await self.notify_websockets(task_id, {
                    "type": "cancelled",
                    "task_id": task_id,
                    "message": "任务已取消"
                })
                
                return True
        return False

    def delete_task(self, task_id: str) -> bool:
        """删除任务"""
        if task_id in self.tasks:
            del self.tasks[task_id]
            # 清理WebSocket连接
            if task_id in self.websocket_connections:
                del self.websocket_connections[task_id]
            return True
        return False

# 全局OCR服务实例
ocr_service = OCRService()