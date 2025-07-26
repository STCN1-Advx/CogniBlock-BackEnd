"""智能笔记处理服务

集成OCR识别、纠错校正和笔记总结的完整工作流
"""

import asyncio
import json
import logging
import time
import uuid
import os
import re
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
        
        # 加载提示词
        self._load_prompts()
        
        # 处理步骤定义
        self.processing_steps = [
            {"step": "ocr_recognition", "name": "OCR识别", "description": "使用PPInfra Qwen2.5-VL进行图片文字识别"},
            {"step": "error_correction", "name": "纠错校正", "description": "使用DeepSeek-V3进行文本纠错"},
            {"step": "note_summary", "name": "笔记总结", "description": "使用Kimi-K2生成笔记总结"},
            {"step": "knowledge_base_record", "name": "知识库记录", "description": "生成结构化的知识库记录"},
            {"step": "save_to_database", "name": "保存到数据库", "description": "将结果保存到数据库"},
            {"step": "tag_generation", "name": "标签生成", "description": "使用AI为内容生成相关标签"}
        ]
    
    def _load_prompts(self):
        """加载提示词文件"""
        try:
            # 获取项目根目录下的prompts文件夹路径
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(os.path.dirname(current_dir))
            prompts_dir = os.path.join(project_root, "prompts")
            
            # 读取各个提示词文件
            self.prompts = {}
            
            # OCR识别提示词
            ocr_prompt_path = os.path.join(prompts_dir, "ocr_recognition.txt")
            if os.path.exists(ocr_prompt_path):
                with open(ocr_prompt_path, 'r', encoding='utf-8') as f:
                    self.prompts['ocr_recognition'] = f.read().strip()
            else:
                self.prompts['ocr_recognition'] = "请识别图片中的所有文字内容，包括数学公式、表格等。保持原有的格式和结构，对于数学公式请使用LaTeX格式表示。"
            
            # 纠错校正提示词
            error_correction_path = os.path.join(prompts_dir, "error_correction.txt")
            if os.path.exists(error_correction_path):
                with open(error_correction_path, 'r', encoding='utf-8') as f:
                    self.prompts['error_correction'] = f.read().strip()
            else:
                self.prompts['error_correction'] = "请对以下OCR识别的文本进行纠错校正，修正可能的识别错误，但保持原有的格式和结构。"
            
            # 笔记总结提示词
            note_summary_path = os.path.join(prompts_dir, "note_summary.txt")
            if os.path.exists(note_summary_path):
                with open(note_summary_path, 'r', encoding='utf-8') as f:
                    self.prompts['note_summary'] = f.read().strip()
            else:
                self.prompts['note_summary'] = "请对以下文本内容进行笔记总结，生成结构化的学习笔记。"
            
            # 关键词提取提示词
            keyword_extraction_path = os.path.join(prompts_dir, "keyword_extraction.txt")
            if os.path.exists(keyword_extraction_path):
                with open(keyword_extraction_path, 'r', encoding='utf-8') as f:
                    self.prompts['keyword_extraction'] = f.read().strip()
            else:
                self.prompts['keyword_extraction'] = "请从以下内容中提取5-10个关键词，用逗号分隔。"
            
            # 知识库记录生成提示词
            knowledge_base_record_path = os.path.join(prompts_dir, "knowledge_base_record.txt")
            if os.path.exists(knowledge_base_record_path):
                with open(knowledge_base_record_path, 'r', encoding='utf-8') as f:
                    self.prompts['knowledge_base_record'] = f.read().strip()
            else:
                self.prompts['knowledge_base_record'] = "请根据笔记总结内容生成结构化的知识库记录。"
            
            logger.info("提示词文件加载成功")
            
        except Exception as e:
            logger.error(f"提示词文件加载失败: {e}")
            # 使用默认提示词
            self.prompts = {
                'ocr_recognition': "请识别图片中的所有文字内容，包括数学公式、表格等。保持原有的格式和结构，对于数学公式请使用LaTeX格式表示。",
                'error_correction': "请对以下OCR识别的文本进行纠错校正，修正可能的识别错误，但保持原有的格式和结构。",
                'note_summary': "请对以下文本内容进行笔记总结，生成结构化的学习笔记。",
                'keyword_extraction': "请从以下内容中提取5-10个关键词，用逗号分隔。",
                'knowledge_base_record': "请根据笔记总结内容生成结构化的知识库记录。"
            }
    
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
    
    async def create_text_task(self, text: str, title: Optional[str] = None, user_id: Optional[str] = None) -> str:
        """创建智能笔记文字处理任务（跳过OCR步骤）"""
        task_id = str(uuid.uuid4())
        
        # 创建任务记录
        self.tasks[task_id] = {
            "task_id": task_id,
            "status": "pending",
            "current_step": None,
            "progress": 0.0,
            "text_input": text,  # 直接存储文字输入
            "title": title,
            "user_id": user_id,
            "result": None,
            "error_message": None,
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
            "is_text_mode": True  # 标记为文字模式
        }
        
        # 启动异步处理
        asyncio.create_task(self._process_text_task(task_id))
        
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
            
            await self._update_task_status(task_id, "processing", "knowledge_base_record", 80.0)
            
            # 步骤4: 生成知识库记录
            knowledge_record = await self._generate_knowledge_base_record(task_id, summary_result)
            if not knowledge_record:
                return
            
            await self._update_task_status(task_id, "processing", "save_to_database", 90.0)
            
            # 步骤5: 保存到数据库
            content_id = await self._save_to_database(task_id, ocr_result, corrected_text, summary_result, knowledge_record)
            if not content_id:
                return

            await self._update_task_status(task_id, "processing", "tag_generation", 95.0)

            # 步骤6: 生成标签
            await self._generate_tags_for_content(task_id, content_id, summary_result, knowledge_record)

            # 完成任务
            self.tasks[task_id]["result"] = {
                "content_id": content_id,
                "ocr_text": ocr_result,
                "corrected_text": corrected_text,
                "summary": summary_result,
                "knowledge_record": knowledge_record
            }

            await self._update_task_status(task_id, "completed", None, 100.0)
            
        except Exception as e:
            logger.error(f"任务处理失败 {task_id}: {e}")
            await self._update_task_status(task_id, "failed", None, 0.0, str(e))
    
    async def _process_text_task(self, task_id: str):
        """处理智能笔记文字任务（跳过OCR步骤）"""
        try:
            task = self.tasks[task_id]
            text_input = task["text_input"]
            
            await self._update_task_status(task_id, "processing", "error_correction", 20.0)
            
            # 步骤1: 纠错校正（从文字输入开始）
            corrected_text = await self._perform_error_correction(task_id, text_input)
            if not corrected_text:
                return
            
            await self._update_task_status(task_id, "processing", "note_summary", 50.0)
            
            # 步骤2: 笔记总结
            summary_result = await self._perform_note_summary(task_id, corrected_text)
            if not summary_result:
                return
            
            await self._update_task_status(task_id, "processing", "knowledge_base_record", 70.0)
            
            # 步骤3: 生成知识库记录
            knowledge_record = await self._generate_knowledge_base_record(task_id, summary_result)
            if not knowledge_record:
                return
            
            await self._update_task_status(task_id, "processing", "save_to_database", 85.0)
            
            # 步骤4: 保存到数据库
            content_id = await self._save_to_database_text(task_id, text_input, corrected_text, summary_result, knowledge_record)
            if not content_id:
                return

            await self._update_task_status(task_id, "processing", "tag_generation", 95.0)

            # 步骤5: 生成标签
            await self._generate_tags_for_content(task_id, content_id, summary_result, knowledge_record)

            # 完成任务
            self.tasks[task_id]["result"] = {
                "content_id": content_id,
                "ocr_text": text_input,  # 原始文字输入
                "corrected_text": corrected_text,
                "summary": summary_result,
                "knowledge_record": knowledge_record
            }

            await self._update_task_status(task_id, "completed", None, 100.0)
            
        except Exception as e:
            logger.error(f"文字任务处理失败 {task_id}: {e}")
            await self._update_task_status(task_id, "failed", None, 0.0, str(e))
    
    async def _perform_ocr(self, task_id: str) -> Optional[str]:
        """执行OCR识别"""
        try:
            task = self.tasks[task_id]
            image_data = task["image_data"]
            
            # 推送控制台输出
            await self._push_console_output(task_id, "开始OCR识别...")
            
            # 使用从文件加载的OCR提示词
            ocr_prompt = self.prompts.get('ocr_recognition', "请识别图片中的所有文字内容")
            
            await self._push_console_output(task_id, "正在调用Qwen2.5-VL模型进行OCR识别...")
            
            # 使用PPInfra的Qwen2.5-VL模型进行OCR
            result = self.ocr_client.extract_text(
                image_source=image_data,
                model="qwen/qwen2.5-vl-72b-instruct",
                prompt=ocr_prompt
            )
            
            if result and result.strip():
                await self._push_console_output(task_id, f"OCR识别完成，识别到 {len(result.strip())} 个字符")
                
                # 实时推送OCR结果
                await self._push_intermediate_result(task_id, "ocr_completed", {
                    "ocr_text": result.strip(),
                    "step": "OCR识别完成",
                    "progress": 25.0
                })
                return result.strip()
            else:
                await self._push_console_output(task_id, "OCR识别失败，未获取到文本内容")
                raise Exception("OCR识别失败，未获取到文本内容")
                
        except Exception as e:
            await self._push_console_output(task_id, f"OCR识别失败: {e}")
            logger.error(f"OCR识别失败 {task_id}: {e}")
            await self._update_task_status(task_id, "failed", "ocr_recognition", 0.0, f"OCR识别失败: {e}")
            return None
    
    async def _perform_error_correction(self, task_id: str, ocr_text: str) -> Optional[str]:
        """执行纠错校正"""
        try:
            await self._push_console_output(task_id, "开始纠错校正...")
            
            # 使用从文件加载的纠错提示词模板
            error_correction_template = self.prompts.get('error_correction', 
                "请对以下OCR识别的文本进行纠错校正，修正可能的识别错误，但保持原有的格式和结构：\n\n原始文本：\n{ocr_text}")
            
            # 格式化提示词，插入OCR文本
            prompt = error_correction_template.format(ocr_text=ocr_text)
            
            await self._push_console_output(task_id, "正在调用DeepSeek-V3模型进行纠错校正...")
            
            response = self.deepseek_client.chat.completions.create(
                model="deepseek/deepseek-v3",
                messages=[
                    {"role": "system", "content": "你是一个专业的文本纠错专家，擅长修正OCR识别错误。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1
            )
            
            corrected_text = response.choices[0].message.content.strip()
            
            await self._push_console_output(task_id, f"纠错校正完成，处理了 {len(corrected_text)} 个字符")
            
            # 实时推送纠错结果
            await self._push_intermediate_result(task_id, "correction_completed", {
                "corrected_text": corrected_text,
                "step": "纠错校正完成",
                "progress": 55.0
            })
            
            return corrected_text
            
        except Exception as e:
            await self._push_console_output(task_id, f"纠错校正失败: {e}")
            logger.error(f"纠错校正失败 {task_id}: {e}")
            await self._update_task_status(task_id, "failed", "error_correction", 0.0, f"纠错校正失败: {e}")
            return None
    
    async def _perform_note_summary(self, task_id: str, corrected_text: str) -> Optional[Dict[str, Any]]:
        """执行笔记总结"""
        try:
            await self._push_console_output(task_id, "开始生成笔记总结...")
            
            task = self.tasks[task_id]
            title = task.get("title", "智能笔记")
            
            # 使用从文件加载的笔记总结提示词模板
            note_summary_template = self.prompts.get('note_summary',
                "请对以下文本内容进行笔记总结，生成结构化的学习笔记：\n\n原始内容：\n{corrected_text}")
            
            # 格式化提示词，插入纠错后的文本
            prompt = note_summary_template.format(corrected_text=corrected_text)
            
            await self._push_console_output(task_id, "正在调用Kimi-K2模型生成笔记总结...")
            
            response = self.kimi_client.chat.completions.create(
                model="moonshotai/kimi-k2-instruct",
                messages=[
                    {"role": "system", "content": "你是一个专业的学习笔记整理专家，擅长将复杂内容整理成结构化的学习材料。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3
            )
            
            summary_content = response.choices[0].message.content.strip()
            
            await self._push_console_output(task_id, "正在提取关键词...")
            
            # 使用从文件加载的关键词提取提示词
            keyword_template = self.prompts.get('keyword_extraction',
                "请从以下内容中提取5-10个关键词，用逗号分隔：\n{content}")
            
            keywords_prompt = keyword_template.format(content=corrected_text)
            keywords_response = self.kimi_client.chat.completions.create(
                model="moonshotai/kimi-k2-instruct",
                messages=[
                    {"role": "system", "content": "你是一个关键词提取专家。"},
                    {"role": "user", "content": keywords_prompt}
                ],
                temperature=0.1
            )
            
            keywords = keywords_response.choices[0].message.content.strip()
            
            summary_result = {
                "title": title,
                "content": summary_content,
                "keywords": keywords
            }
            
            await self._push_console_output(task_id, f"笔记总结生成完成，生成了 {len(summary_content)} 个字符的总结")
            
            # 实时推送总结结果
            await self._push_intermediate_result(task_id, "summary_completed", {
                "summary": summary_result,
                "step": "笔记总结完成",
                "progress": 85.0
            })
            
            return summary_result
            
        except Exception as e:
            await self._push_console_output(task_id, f"笔记总结失败: {e}")
            logger.error(f"笔记总结失败 {task_id}: {e}")
            await self._update_task_status(task_id, "failed", "note_summary", 0.0, f"笔记总结失败: {e}")
            return None
    
    async def _generate_knowledge_base_record(self, task_id: str, summary_result: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """生成知识库记录"""
        try:
            from datetime import datetime
            
            await self._push_console_output(task_id, "开始生成知识库记录...")
            
            # 使用从文件加载的知识库记录提示词模板
            knowledge_record_template = self.prompts.get('knowledge_base_record',
                "请根据笔记总结内容生成结构化的知识库记录：\n\n笔记总结：\n{note_summary}")
            
            # 格式化提示词，插入笔记总结内容
            prompt = knowledge_record_template.format(note_summary=summary_result["content"])
            
            await self._push_console_output(task_id, "正在调用Kimi API生成知识库记录...")
            
            response = self.kimi_client.chat.completions.create(
                model="moonshotai/kimi-k2-instruct",
                messages=[
                    {"role": "system", "content": "你是一个专业的知识管理专家，擅长生成结构化的知识库记录。请严格按照JSON格式返回结果，不要添加任何额外的文字说明。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2
            )
            
            response_content = response.choices[0].message.content.strip()
            
            await self._push_console_output(task_id, "正在解析知识库记录JSON...")
            
            # 改进的JSON解析逻辑
            try:
                import json
                import re
                
                # 记录原始响应用于调试
                logger.info(f"知识库记录原始响应: {response_content[:200]}...")
                
                # 第一步：基础清理
                cleaned_content = response_content.strip()
                
                # 移除markdown代码块标记
                if cleaned_content.startswith('```json'):
                    cleaned_content = cleaned_content[7:]
                elif cleaned_content.startswith('```'):
                    cleaned_content = cleaned_content[3:]
                    
                if cleaned_content.endswith('```'):
                    cleaned_content = cleaned_content[:-3]
                
                # 移除可能的前后空白和换行
                cleaned_content = cleaned_content.strip()
                
                # 第二步：查找JSON起止符
                if not cleaned_content.startswith('{'):
                    # 查找第一个 { 的位置
                    json_start = cleaned_content.find('{')
                    if json_start != -1:
                        cleaned_content = cleaned_content[json_start:]
                        await self._push_console_output(task_id, f"找到JSON起始位置: {json_start}")
                
                if not cleaned_content.endswith('}'):
                    # 查找最后一个 } 的位置
                    json_end = cleaned_content.rfind('}')
                    if json_end != -1:
                        cleaned_content = cleaned_content[:json_end + 1]
                        await self._push_console_output(task_id, f"找到JSON结束位置: {json_end}")
                
                await self._push_console_output(task_id, f"清理后的JSON内容长度: {len(cleaned_content)}")
                
                # 第三步：尝试解析JSON
                knowledge_record = None
                try:
                    knowledge_record = json.loads(cleaned_content)
                    await self._push_console_output(task_id, "JSON解析成功")
                except json.JSONDecodeError as e:
                    await self._push_console_output(task_id, f"JSON解析失败: {e}，尝试修复...")
                    
                    # 第四步：尝试修复常见问题
                    # 移除注释和空行
                    lines = cleaned_content.split('\n')
                    json_lines = []
                    for line in lines:
                        line = line.strip()
                        if line and not line.startswith('//') and not line.startswith('#'):
                            # 移除行内注释
                            if '//' in line:
                                line = line[:line.find('//')]
                            json_lines.append(line)
                    
                    fixed_content = '\n'.join(json_lines).strip()
                    
                    # 尝试修复不完整的JSON
                    if fixed_content and not fixed_content.endswith('}'):
                        # 如果JSON不完整，尝试补全
                        brace_count = fixed_content.count('{') - fixed_content.count('}')
                        if brace_count > 0:
                            fixed_content += '}' * brace_count
                            await self._push_console_output(task_id, f"补全JSON括号: {brace_count}个")
                    
                    # 第五步：再次尝试解析
                    try:
                        knowledge_record = json.loads(fixed_content)
                        await self._push_console_output(task_id, "修复后JSON解析成功")
                    except json.JSONDecodeError as e2:
                        await self._push_console_output(task_id, f"修复后仍然失败: {e2}")
                        
                        # 第六步：最后的尝试 - 使用正则表达式提取字段
                        await self._push_console_output(task_id, "尝试使用正则表达式提取字段...")
                        
                        title_match = re.search(r'"title"\s*:\s*"([^"]*)"', response_content)
                        date_match = re.search(r'"date"\s*:\s*"([^"]*)"', response_content)
                        preview_match = re.search(r'"content_preview"\s*:\s*"([^"]*)"', response_content)
                        
                        if title_match:
                            knowledge_record = {
                                "title": title_match.group(1)[:50],  # 限制长度
                                "date": date_match.group(1) if date_match else datetime.now().strftime("%Y-%m-%d"),
                                "content_preview": preview_match.group(1)[:200] if preview_match else summary_result.get("content", "")[:200]
                            }
                            await self._push_console_output(task_id, "正则表达式提取成功")
                        else:
                            raise ValueError("无法提取任何有效字段")
                
                # 验证和补充必要字段
                if not isinstance(knowledge_record, dict):
                    raise ValueError("解析结果不是字典格式")
                    
                # 确保包含必要字段并限制长度
                if "title" not in knowledge_record or not knowledge_record["title"]:
                    knowledge_record["title"] = summary_result.get("title", "智能笔记")
                
                # 限制标题长度为50个字符
                if len(knowledge_record["title"]) > 50:
                    knowledge_record["title"] = knowledge_record["title"][:50]
                
                if "date" not in knowledge_record or not knowledge_record["date"]:
                    knowledge_record["date"] = datetime.now().strftime("%Y-%m-%d")
                    
                if "content_preview" not in knowledge_record or not knowledge_record["content_preview"]:
                    # 生成内容预览
                    content = summary_result.get("content", "")
                    if len(content) > 200:
                        knowledge_record["content_preview"] = content[:200] + "..."
                    else:
                        knowledge_record["content_preview"] = content
                        
            except (json.JSONDecodeError, ValueError, KeyError) as e:
                await self._push_console_output(task_id, f"JSON解析完全失败: {e}，使用默认格式")
                logger.warning(f"知识库记录JSON解析失败，使用默认格式: {e}")
                
                # 如果解析失败，使用默认格式
                knowledge_record = {
                    "title": summary_result.get("title", "智能笔记")[:50],  # 限制长度
                    "date": datetime.now().strftime("%Y-%m-%d"),
                    "content_preview": summary_result.get("content", "智能笔记内容")[:200] + ("..." if len(summary_result.get("content", "")) > 200 else "")
                }
            
            await self._push_console_output(task_id, f"知识库记录生成完成，标题: {knowledge_record.get('title', '未知')}")
            
            # 实时推送知识库记录结果
            await self._push_intermediate_result(task_id, "knowledge_record_completed", {
                "knowledge_record": knowledge_record,
                "step": "知识库记录生成完成",
                "progress": 85.0
            })
            
            return knowledge_record
            
        except Exception as e:
            await self._push_console_output(task_id, f"知识库记录生成失败: {e}")
            logger.error(f"知识库记录生成失败 {task_id}: {e}")
            await self._update_task_status(task_id, "failed", "knowledge_base_record", 0.0, f"知识库记录生成失败: {e}")
            return None
    
    async def _save_to_database(self, task_id: str, ocr_text: str, corrected_text: str, summary_result: Dict[str, Any], knowledge_record: Dict[str, Any]) -> Optional[int]:
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
                summary_status="completed",
                knowledge_title=knowledge_record.get("title"),
                knowledge_date=knowledge_record.get("date"),
                knowledge_preview=knowledge_record.get("content_preview")
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
            
            # 实时推送保存结果
            await self._push_intermediate_result(task_id, "save_completed", {
                "content_id": content.id,
                "step": "保存到数据库完成",
                "progress": 100.0
            })
            
            logger.info(f"内容已保存到数据库，ID: {content.id}，用户: {user_id}")
            return content.id
            
        except Exception as e:
            logger.error(f"保存到数据库失败 {task_id}: {e}")
            await self._update_task_status(task_id, "failed", "save_to_database", 0.0, f"保存到数据库失败: {e}")
            return None
        finally:
            if 'db' in locals():
                db.close()
    
    async def _save_to_database_text(self, task_id: str, original_text: str, corrected_text: str, summary_result: Dict[str, Any], knowledge_record: Dict[str, Any]) -> Optional[int]:
        """保存文字任务到数据库"""
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
            
            # 创建Content记录（文字模式）
            content = Content(
                content_type="text",  # 标记为文字类型
                image_data=None,  # 文字模式没有图片数据
                text_data=corrected_text,  # 存储纠错后的文本
                filename=None,  # 文字模式没有文件名
                summary_title=summary_result["title"],
                summary_content=summary_result["content"],
                summary_status="completed",
                knowledge_title=knowledge_record.get("title"),
                knowledge_date=knowledge_record.get("date"),
                knowledge_preview=knowledge_record.get("content_preview"),
                original_text=original_text  # 存储原始输入文字
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
            
            # 实时推送保存结果
            await self._push_intermediate_result(task_id, "save_completed", {
                "content_id": content.id,
                "step": "保存到数据库完成",
                "progress": 100.0
            })
            
            logger.info(f"文字内容已保存到数据库，ID: {content.id}，用户: {user_id}")
            return content.id
            
        except Exception as e:
            logger.error(f"保存文字任务到数据库失败 {task_id}: {e}")
            await self._update_task_status(task_id, "failed", "save_to_database", 0.0, f"保存到数据库失败: {e}")
            return None
        finally:
            if 'db' in locals():
                db.close()
    
    async def _push_console_output(self, task_id: str, message: str):
        """推送控制台输出到前端"""
        try:
            if task_id in self.tasks:
                # 添加到任务的控制台输出历史
                if "console_outputs" not in self.tasks[task_id]:
                    self.tasks[task_id]["console_outputs"] = []
                
                self.tasks[task_id]["console_outputs"].append({
                    "timestamp": datetime.now(),
                    "message": message
                })
                
                # 推送到前端
                await self._push_intermediate_result(task_id, "console_output", {
                    "message": message,
                    "timestamp": datetime.now().isoformat()
                })
                
                # 同时输出到日志
                logger.info(f"任务 {task_id} 控制台输出: {message}")
        except Exception as e:
            logger.error(f"推送控制台输出失败 {task_id}: {e}")

    async def _push_intermediate_result(self, task_id: str, result_type: str, data: Dict[str, Any]):
        """推送中间结果"""
        if task_id in self.tasks:
            # 将中间结果存储到任务中
            if "intermediate_results" not in self.tasks[task_id]:
                self.tasks[task_id]["intermediate_results"] = []
            
            intermediate_result = {
                "type": result_type,
                "data": data,
                "timestamp": datetime.now()
            }
            
            self.tasks[task_id]["intermediate_results"].append(intermediate_result)
            self.tasks[task_id]["updated_at"] = datetime.now()
            
            logger.info(f"任务 {task_id} 推送中间结果: {result_type}")
            
            # 立即刷新任务状态，确保流式推送能够检测到变化
            await asyncio.sleep(0.01)  # 短暂延迟确保状态更新被检测到
    
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
            
            logger.info(f"任务 {task_id} 状态更新: {status} - {current_step} ({progress}%)")
            
            # 通过WebSocket推送状态更新
            try:
                from app.api.v2.endpoints.smart_note_websocket import websocket_service
                await websocket_service.push_status_update(task_id, status, current_step, progress)
                
                # 如果任务完成，推送最终结果
                if status == "completed":
                    result = self.tasks[task_id].get("result")
                    if result:
                        await websocket_service.push_task_completed(task_id, result)
                elif status == "failed":
                    await websocket_service.push_task_failed(task_id, error_message or "处理失败")
                    
            except Exception as e:
                logger.warning(f"WebSocket推送状态更新失败: {e}")
    
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

    async def _generate_tags_for_content(self, task_id: str, content_id: int,
                                       summary_result: Dict[str, Any], knowledge_record: Dict[str, Any]):
        """为内容生成标签"""
        try:
            await self._push_console_output(task_id, "开始生成内容标签...")

            # 导入标签生成服务
            from app.services.tag_generation_service import tag_generation_service
            from app.db.session import get_db
            from app.crud.content import content as content_crud

            # 获取数据库会话
            db = next(get_db())

            try:
                # 获取内容对象
                content = content_crud.get(db, content_id)
                if not content:
                    await self._push_console_output(task_id, "错误: 找不到内容对象")
                    return

                # 生成标签
                result = await tag_generation_service.generate_tags_for_content(db, content)

                if result.get("success"):
                    tag_count = result.get("tag_count", 0)
                    existing_tags = result.get("existing_tags", [])
                    new_tags = result.get("new_tags", [])

                    await self._push_console_output(task_id, f"标签生成成功: 共生成 {tag_count} 个标签")
                    if existing_tags:
                        await self._push_console_output(task_id, f"使用现有标签: {', '.join(existing_tags)}")
                    if new_tags:
                        await self._push_console_output(task_id, f"创建新标签: {', '.join(new_tags)}")
                else:
                    error_msg = result.get("error", "未知错误")
                    await self._push_console_output(task_id, f"标签生成失败: {error_msg}")

            finally:
                db.close()

        except Exception as e:
            logger.error(f"标签生成失败 {task_id}: {e}")
            await self._push_console_output(task_id, f"标签生成失败: {str(e)}")


# 全局服务实例
smart_note_service = SmartNoteService()