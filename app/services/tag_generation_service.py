import json
import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from openai import OpenAI
import os

from app.crud.tag import tag as tag_crud
from app.crud.content_tag import content_tag as content_tag_crud
from app.models.content import Content

logger = logging.getLogger(__name__)


class TagGenerationService:
    """AI标签生成服务"""
    
    def __init__(self):
        """初始化服务"""
        self._init_ai_client()
        self._load_prompts()
    
    def _init_ai_client(self):
        """初始化AI客户端"""
        try:
            # 使用PPINFRA的API
            ppinfra_api_key = os.getenv("PPINFRA_API_KEY")
            ppinfra_base_url = os.getenv("PPINFRA_BASE_URL", "https://api.ppinfra.com/v3/openai")
            
            if ppinfra_api_key:
                self.ai_client = OpenAI(
                    api_key=ppinfra_api_key,
                    base_url=ppinfra_base_url
                )
                logger.info("AI客户端初始化成功")
            else:
                logger.warning("PPINFRA API密钥未配置，标签生成功能将不可用")
                self.ai_client = None
                
        except Exception as e:
            logger.error(f"AI客户端初始化失败: {e}")
            self.ai_client = None
    
    def _load_prompts(self):
        """加载提示词"""
        self.tag_generation_prompt = """
基于以下内容，为其生成3-5个最相关的标签。

内容摘要：{summary_content}
知识库记录：{knowledge_record}

现有标签列表：{existing_tags}

请按以下规则生成标签：
1. 优先从现有标签中选择最匹配的标签
2. 如果现有标签不够准确，可以生成新的标签
3. 标签应该简洁、准确、有代表性
4. 标签名称应该是中文，长度在2-10个字符之间
5. 避免过于宽泛的标签（如"学习"、"知识"等）

请严格按照以下JSON格式返回结果，不要添加任何其他文字：
{
    "existing_tags": ["现有标签1", "现有标签2"],
    "new_tags": ["新标签1", "新标签2"]
}
"""
    
    async def generate_tags_for_content(self, db: Session, content: Content) -> Dict[str, Any]:
        """为内容生成标签"""
        if not self.ai_client:
            logger.warning("AI客户端未初始化，跳过标签生成")
            return {"success": False, "error": "AI客户端未初始化"}
        
        try:
            # 准备内容数据
            summary_content = content.summary_content or ""
            knowledge_record = content.knowledge_preview or ""
            
            if not summary_content and not knowledge_record:
                logger.warning(f"Content {content.id} 没有可用于标签生成的内容")
                return {"success": False, "error": "没有可用于标签生成的内容"}
            
            # 获取现有标签
            existing_tags = tag_crud.get_multi(db, limit=200)
            existing_tag_names = [tag.name for tag in existing_tags]
            
            # 构建提示词
            prompt = self.tag_generation_prompt.format(
                summary_content=summary_content,
                knowledge_record=knowledge_record,
                existing_tags=", ".join(existing_tag_names[:50])  # 限制标签数量避免提示词过长
            )
            
            # 调用AI生成标签
            response = self.ai_client.chat.completions.create(
                model="moonshotai/kimi-k2-instruct",
                messages=[
                    {"role": "system", "content": "你是一个专业的内容标签生成专家。请严格按照JSON格式返回结果。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=500
            )
            
            response_content = response.choices[0].message.content.strip()
            logger.info(f"AI标签生成响应: {response_content}")
            
            # 解析响应
            try:
                tag_data = json.loads(response_content)
                existing_tags_selected = tag_data.get("existing_tags", [])
                new_tags = tag_data.get("new_tags", [])
            except json.JSONDecodeError as e:
                logger.error(f"解析AI响应失败: {e}, 响应内容: {response_content}")
                return {"success": False, "error": "AI响应格式错误"}
            
            # 处理标签
            tag_ids = []
            
            # 处理现有标签
            for tag_name in existing_tags_selected:
                tag = tag_crud.get_by_name(db, tag_name)
                if tag:
                    tag_ids.append(tag.id)
                    logger.info(f"使用现有标签: {tag_name}")
            
            # 处理新标签
            for tag_name in new_tags:
                if tag_name and len(tag_name.strip()) >= 2:
                    tag = tag_crud.get_or_create(db, tag_name.strip())
                    tag_ids.append(tag.id)
                    logger.info(f"创建新标签: {tag_name}")
            
            # 为内容添加标签
            if tag_ids:
                content_tag_crud.update_content_tags(db, content.id, tag_ids, confidence=0.8)
                logger.info(f"为Content {content.id} 添加了 {len(tag_ids)} 个标签")
            
            return {
                "success": True,
                "tag_count": len(tag_ids),
                "existing_tags": existing_tags_selected,
                "new_tags": new_tags
            }
            
        except Exception as e:
            logger.error(f"标签生成失败: {e}")
            return {"success": False, "error": str(e)}
    
    def generate_tags_for_text(self, db: Session, text_content: str, 
                              content_id: Optional[int] = None) -> Dict[str, Any]:
        """为纯文本生成标签（同步版本）"""
        if not self.ai_client:
            logger.warning("AI客户端未初始化，跳过标签生成")
            return {"success": False, "error": "AI客户端未初始化"}
        
        try:
            # 获取现有标签
            existing_tags = tag_crud.get_multi(db, limit=200)
            existing_tag_names = [tag.name for tag in existing_tags]
            
            # 构建简化的提示词
            prompt = f"""
基于以下文本内容，生成3-5个最相关的标签：

文本内容：{text_content}

现有标签列表：{", ".join(existing_tag_names[:50])}

请严格按照以下JSON格式返回结果：
{{
    "existing_tags": ["现有标签1", "现有标签2"],
    "new_tags": ["新标签1", "新标签2"]
}}
"""
            
            # 调用AI生成标签
            response = self.ai_client.chat.completions.create(
                model="moonshotai/kimi-k2-instruct",
                messages=[
                    {"role": "system", "content": "你是一个专业的内容标签生成专家。请严格按照JSON格式返回结果。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=500
            )
            
            response_content = response.choices[0].message.content.strip()
            
            # 解析响应
            try:
                tag_data = json.loads(response_content)
                existing_tags_selected = tag_data.get("existing_tags", [])
                new_tags = tag_data.get("new_tags", [])
            except json.JSONDecodeError as e:
                logger.error(f"解析AI响应失败: {e}")
                return {"success": False, "error": "AI响应格式错误"}
            
            # 处理标签
            tag_ids = []
            
            # 处理现有标签
            for tag_name in existing_tags_selected:
                tag = tag_crud.get_by_name(db, tag_name)
                if tag:
                    tag_ids.append(tag.id)
            
            # 处理新标签
            for tag_name in new_tags:
                if tag_name and len(tag_name.strip()) >= 2:
                    tag = tag_crud.get_or_create(db, tag_name.strip())
                    tag_ids.append(tag.id)
            
            # 如果提供了content_id，为内容添加标签
            if content_id and tag_ids:
                content_tag_crud.update_content_tags(db, content_id, tag_ids, confidence=0.8)
            
            return {
                "success": True,
                "tag_ids": tag_ids,
                "existing_tags": existing_tags_selected,
                "new_tags": new_tags
            }
            
        except Exception as e:
            logger.error(f"标签生成失败: {e}")
            return {"success": False, "error": str(e)}


# 创建全局实例
tag_generation_service = TagGenerationService()
