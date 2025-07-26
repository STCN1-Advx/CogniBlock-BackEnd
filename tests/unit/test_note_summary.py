"""
笔记总结功能单元测试
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from app.utils.text_processing import TextProcessor, ConfidenceCalculator
from app.utils.task_manager import TaskManager, TaskStatus, SummaryTask
from app.schemas.note_summary import SummaryRequest


class TestTextProcessor:
    """文本处理器测试"""
    
    def setup_method(self):
        """测试前设置"""
        self.processor = TextProcessor()
    
    @pytest.mark.asyncio
    async def test_parse_summary_response(self):
        """测试解析AI响应"""
        response = """
        标题：测试总结标题
        主题：测试主题
        内容：这是测试内容
        包含多行内容
        """
        
        result = self.processor._parse_summary_response(response)
        
        assert result["title"] == "测试总结标题"
        assert result["topic"] == "测试主题"
        assert "这是测试内容" in result["content"]
        assert "包含多行内容" in result["content"]
    
    @pytest.mark.asyncio
    async def test_parse_summary_response_missing_fields(self):
        """测试解析缺少字段的响应"""
        response = "标题：只有标题"
        
        result = self.processor._parse_summary_response(response)
        
        assert result["title"] == "只有标题"
        assert result["topic"] == "知识整理"  # 默认值
        assert result["content"] == "总结内容生成失败，请重试。"  # 默认值
    
    @pytest.mark.asyncio
    @patch('openai.AsyncOpenAI')
    async def test_generate_single_summary(self, mock_openai):
        """测试生成单笔记总结"""
        # 模拟OpenAI响应
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = """
        标题：数学公式总结
        主题：微积分基础
        内容：这是关于微积分的总结内容
        """
        
        mock_client = AsyncMock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client
        
        # 重新初始化处理器以使用模拟的客户端
        self.processor.client = mock_client
        
        result = await self.processor.generate_single_summary("测试标题", "测试内容")
        
        assert result["title"] == "数学公式总结"
        assert result["topic"] == "微积分基础"
        assert "微积分" in result["content"]


class TestConfidenceCalculator:
    """置信度计算器测试"""
    
    def setup_method(self):
        """测试前设置"""
        self.calculator = ConfidenceCalculator()
    
    def test_extract_keywords(self):
        """测试关键词提取"""
        text = "这是一个测试文本，包含一些关键词和概念。"
        keywords = self.calculator._extract_keywords(text)
        
        assert isinstance(keywords, dict)
        assert len(keywords) > 0
        # 检查是否过滤了停用词
        assert "的" not in keywords
        assert "是" not in keywords
    
    def test_cosine_similarity(self):
        """测试余弦相似度计算"""
        keywords1 = {"测试": 2, "文本": 1, "相似度": 1}
        keywords2 = {"测试": 1, "文本": 2, "计算": 1}
        
        similarity = self.calculator._cosine_similarity(keywords1, keywords2)
        
        assert 0 <= similarity <= 1
        assert similarity > 0  # 应该有一定相似度
    
    def test_calculate_similarity(self):
        """测试文本相似度计算"""
        text1 = "这是关于机器学习的文本内容"
        text2 = "机器学习是人工智能的重要分支"
        
        similarity = self.calculator.calculate_similarity(text1, text2)
        
        assert 0 <= similarity <= 100
        assert similarity > 0  # 应该有一定相似度
    
    def test_calculate_confidence_scores(self):
        """测试置信度分数计算"""
        comprehensive_summary = {
            "content": "这是综合总结内容，包含机器学习和深度学习的概念"
        }
        
        individual_summaries = [
            {"content": "机器学习是人工智能的重要分支"},
            {"content": "深度学习是机器学习的子领域"},
            {"content": "完全不相关的内容"}
        ]
        
        scores = self.calculator.calculate_confidence_scores(
            comprehensive_summary, individual_summaries
        )
        
        assert len(scores) == 3
        assert all(0 <= score <= 100 for score in scores)
        # 前两个应该有较高的相似度
        assert scores[0] > scores[2]
        assert scores[1] > scores[2]


class TestTaskManager:
    """任务管理器测试"""
    
    def setup_method(self):
        """测试前设置"""
        self.task_manager = TaskManager()
    
    def test_summary_task_creation(self):
        """测试总结任务创建"""
        task = SummaryTask(
            task_id="test-task-id",
            user_id="test-user-id",
            content_ids=["1", "2", "3"]
        )
        
        assert task.task_id == "test-task-id"
        assert task.user_id == "test-user-id"
        assert task.content_ids == ["1", "2", "3"]
        assert task.status == TaskStatus.PENDING
        assert task.progress == 0
    
    def test_task_to_dict(self):
        """测试任务转换为字典"""
        task = SummaryTask(
            task_id="test-task-id",
            user_id="test-user-id",
            content_ids=["1", "2", "3"]
        )
        
        task_dict = task.to_dict()
        
        assert task_dict["task_id"] == "test-task-id"
        assert task_dict["user_id"] == "test-user-id"
        assert task_dict["content_ids"] == ["1", "2", "3"]
        assert task_dict["status"] == "pending"
        assert task_dict["progress"] == 0
    
    @pytest.mark.asyncio
    async def test_create_task_insufficient_content(self):
        """测试内容数量不足时的错误处理"""
        with pytest.raises(ValueError, match="内容数量不足"):
            await self.task_manager.create_task("user-id", ["1"])  # 只有1个内容
    
    @pytest.mark.asyncio
    async def test_get_task_status_nonexistent(self):
        """测试获取不存在任务的状态"""
        result = await self.task_manager.get_task_status("nonexistent-task")
        assert result is None
    
    @pytest.mark.asyncio
    async def test_get_user_tasks_empty(self):
        """测试获取空的用户任务列表"""
        tasks = await self.task_manager.get_user_tasks("user-id")
        assert tasks == []


class TestSummarySchemas:
    """总结相关数据模型测试"""
    
    def test_summary_request_validation(self):
        """测试总结请求验证"""
        # 有效请求
        request = SummaryRequest(content_ids=["1", "2", "3"])
        assert request.content_ids == ["1", "2", "3"]
        
        # 空列表应该通过验证（业务逻辑会处理）
        request = SummaryRequest(content_ids=[])
        assert request.content_ids == []


def test_imports():
    """测试模块导入"""
    try:
        from app.utils.text_processing import text_processor, confidence_calculator
        from app.utils.task_manager import task_manager
        from app.schemas.note_summary import SummaryRequest
        from app.api.v2.endpoints.note_summary import router
        
        assert text_processor is not None
        assert confidence_calculator is not None
        assert task_manager is not None
        assert router is not None
        
    except ImportError as e:
        pytest.fail(f"导入失败: {e}")


def test_api_router_registration():
    """测试API路由注册"""
    try:
        from app.api.v2 import api_router
        from fastapi import APIRouter
        
        assert isinstance(api_router, APIRouter)
        
        # 检查路由是否包含笔记总结端点
        routes = [route.path for route in api_router.routes]
        note_summary_routes = [route for route in routes if 'note-summary' in route]
        
        assert len(note_summary_routes) > 0, "笔记总结路由未正确注册"
        
    except ImportError as e:
        pytest.fail(f"API路由导入失败: {e}")


if __name__ == "__main__":
    # 运行基本测试
    print("🧪 运行笔记总结功能测试...")
    
    # 测试导入
    test_imports()
    print("✅ 模块导入测试通过")
    
    # 测试路由注册
    test_api_router_registration()
    print("✅ API路由注册测试通过")
    
    # 测试置信度计算器
    calculator = ConfidenceCalculator()
    similarity = calculator.calculate_similarity(
        "这是关于机器学习的内容",
        "机器学习是人工智能的分支"
    )
    print(f"✅ 文本相似度计算测试通过，相似度: {similarity}%")
    
    # 测试任务创建
    task = SummaryTask(
        task_id="test-id",
        user_id="user-id",
        content_ids=["1", "2", "3"]
    )
    task_dict = task.to_dict()
    print(f"✅ 任务创建测试通过，任务状态: {task_dict['status']}")
    
    print("🎉 所有基本测试通过！")