"""
文本处理和AI集成模块

提供单笔记总结、多笔记综合总结、置信度计算等功能
"""

import asyncio
import logging
import os
from typing import List, Dict, Any, Optional
from openai import AsyncOpenAI
import jieba
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
from app.core.config import settings

logger = logging.getLogger(__name__)


class TextProcessor:
    """文本处理器，负责生成笔记总结"""
    
    def __init__(self):
        self.client = AsyncOpenAI(
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_BASE_URL
        )
        self.model = settings.NOTE_AI_MODEL
        self.max_retries = settings.NOTE_AI_MAX_RETRIES
        self.retry_delay = settings.NOTE_AI_RETRY_DELAY
        
        # 加载提示词模板
        self._load_prompts()
    
    def _load_prompts(self):
        """加载提示词模板"""
        try:
            with open(settings.NOTE_PROMPT_SINGLE, 'r', encoding='utf-8') as f:
                self.single_prompt = f.read()
        except FileNotFoundError:
            logger.warning(f"单笔记提示词文件未找到: {settings.NOTE_PROMPT_SINGLE}")
            self.single_prompt = "请对以下笔记内容进行总结：\n{content}"
        
        try:
            with open(settings.NOTE_PROMPT_COMPREHENSIVE, 'r', encoding='utf-8') as f:
                self.comprehensive_prompt = f.read()
        except FileNotFoundError:
            logger.warning(f"综合总结提示词文件未找到: {settings.NOTE_PROMPT_COMPREHENSIVE}")
            self.comprehensive_prompt = "请对以下多份总结进行综合整理：\n{summaries}"
        
        try:
            with open(settings.NOTE_PROMPT_CORRECTION, 'r', encoding='utf-8') as f:
                self.correction_prompt = f.read()
        except FileNotFoundError:
            logger.warning(f"修正提示词文件未找到: {settings.NOTE_PROMPT_CORRECTION}")
            self.correction_prompt = "请修正以下总结：\n原始总结：{original_summary}\n综合总结：{comprehensive_summary}"
    
    async def generate_single_summary(self, content: str) -> str:
        """生成单笔记的知识点总结"""
        logger.info(f"开始生成单笔记总结，原始内容长度: {len(content)}")
        logger.info(f"内容预览: {content[:100]}..." if len(content) > 100 else f"完整内容: {content}")
        
        if not content or not content.strip():
            logger.error("内容为空或只包含空白字符")
            return "由于你没有提供任何笔记内容，我无法进行总结。请提供需要总结的笔记内容，我将按照你指定的格式和要求进行知识点总结"
        
        if len(content) > settings.NOTE_MAX_CONTENT_LENGTH:
            content = content[:settings.NOTE_MAX_CONTENT_LENGTH] + "..."
            logger.info(f"内容过长，截断到: {len(content)} 字符")
        
        prompt = self.single_prompt.format(content=content)
        logger.info(f"使用的提示词长度: {len(prompt)}")
        
        for attempt in range(self.max_retries):
            try:
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.7,
                    max_tokens=1000
                )
                
                summary = response.choices[0].message.content.strip()
                logger.info(f"成功生成单笔记总结，长度: {len(summary)}")
                return summary
                
            except Exception as e:
                logger.error(f"生成单笔记总结失败 (尝试 {attempt + 1}/{self.max_retries}): {e}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay)
                else:
                    raise
    
    async def generate_comprehensive_summary(self, summaries: List[str]) -> str:
        """生成综合总结"""
        summaries_text = "\n\n".join([f"## 笔记 {i+1} 总结\n{summary}" for i, summary in enumerate(summaries)])
        prompt = self.comprehensive_prompt.format(summaries=summaries_text)
        
        for attempt in range(self.max_retries):
            try:
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.7,
                    max_tokens=1500
                )
                
                comprehensive_summary = response.choices[0].message.content.strip()
                logger.info(f"成功生成综合总结，长度: {len(comprehensive_summary)}")
                return comprehensive_summary
                
            except Exception as e:
                logger.error(f"生成综合总结失败 (尝试 {attempt + 1}/{self.max_retries}): {e}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay)
                else:
                    raise
    
    async def correct_summary(self, original_summary: str, comprehensive_summary: str) -> str:
        """修正总结内容"""
        prompt = self.correction_prompt.format(
            original_summary=original_summary,
            comprehensive_summary=comprehensive_summary
        )
        
        for attempt in range(self.max_retries):
            try:
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.7,
                    max_tokens=1200
                )
                
                corrected_summary = response.choices[0].message.content.strip()
                logger.info(f"成功修正总结，长度: {len(corrected_summary)}")
                return corrected_summary
                
            except Exception as e:
                logger.error(f"修正总结失败 (尝试 {attempt + 1}/{self.max_retries}): {e}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay)
                else:
                    raise


class ConfidenceCalculator:
    """置信度计算器"""
    
    def __init__(self):
        self.vectorizer = TfidfVectorizer(
            tokenizer=self._tokenize,
            lowercase=False,
            max_features=1000
        )
    
    def _tokenize(self, text: str) -> List[str]:
        """中文分词"""
        return list(jieba.cut(text))
    
    def calculate_similarity(self, text1: str, text2: str) -> float:
        """计算两个文本的相似度"""
        try:
            # 使用TF-IDF向量化
            tfidf_matrix = self.vectorizer.fit_transform([text1, text2])
            
            # 计算余弦相似度
            similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
            
            return float(similarity)
        except Exception as e:
            logger.error(f"计算文本相似度失败: {e}")
            return 0.0
    
    def calculate_confidence_scores(self, comprehensive_summary: str, individual_summaries: List[str]) -> List[float]:
        """计算综合总结与各个单独总结的置信度分数"""
        scores = []
        
        for summary in individual_summaries:
            similarity = self.calculate_similarity(comprehensive_summary, summary)
            scores.append(similarity)
        
        logger.info(f"置信度分数: {scores}")
        return scores


# 全局实例
_text_processor = None
_confidence_calculator = None


def get_text_processor() -> TextProcessor:
    """获取文本处理器实例"""
    global _text_processor
    if _text_processor is None:
        _text_processor = TextProcessor()
    return _text_processor


def get_confidence_calculator() -> ConfidenceCalculator:
    """获取置信度计算器实例"""
    global _confidence_calculator
    if _confidence_calculator is None:
        _confidence_calculator = ConfidenceCalculator()
    return _confidence_calculator


async def generate_summary(content: str) -> str:
    """生成内容总结的便捷函数"""
    processor = get_text_processor()
    return await processor.generate_single_summary(content)