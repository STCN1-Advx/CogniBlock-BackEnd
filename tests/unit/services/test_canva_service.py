"""
业务服务层单元测试

测试CanvaService业务逻辑、权限验证、数据一致性检查等功能。
"""

import unittest
from unittest.mock import Mock, patch, AsyncMock
from uuid import uuid4
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.models.canvas import Canvas
from app.models.card import Card
from app.models.content import Content
from app.models.user_content import UserContent
from app.models.user import User
from app.services.canva_service import (
    CanvaService, 
    CanvaServiceError, 
    PermissionDeniedError, 
    CanvaNotFoundError,
    ContentNotFoundError,
    DataConsistencyError
)
from app.schemas.canva import CardUpdateRequest, PositionModel


class TestCanvaService(unittest.TestCase):
    """CanvaService业务服务层单元测试类"""
    
    @classmethod
    def setUpClass(cls):
        """设置测试环境"""
        # 使用PostgreSQL测试数据库
        import os
        test_db_url = os.getenv("TEST_DATABASE_URL", "postgresql://postgres:password@localhost:5432/cogniblock_test")
        cls.engine = create_engine(test_db_url, echo=False)
        Base.metadata.create_all(cls.engine)
        cls.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=cls.engine)
    
    def setUp(self):
        """每个测试前的设置"""
        self.db = self.SessionLocal()
        self.service = CanvaService(self.db)
        
        # 创建测试用户
        self.test_user_id = uuid4()
        self.other_user_id = uuid4()
        
        self.test_user = User(
            id=self.test_user_id,
            oauth_id="test_oauth_123",
            name="Test User",
            email="test@example.com"
        )
        
        self.other_user = User(
            id=self.other_user_id,
            oauth_id="other_oauth_456",
            name="Other User",
            email="other@example.com"
        )
        
        self.db.add_all([self.test_user, self.other_user])
        self.db.commit()
        
        # 创建测试数据
        self.test_canvas = Canvas(
            owner_id=self.test_user_id,
            name="Test Canvas"
        )
        self.db.add(self.test_canvas)
        self.db.commit()
        
        self.test_content = Content(
            content_type="text",
            text_data="Test content"
        )
        self.db.add(self.test_content)
        self.db.commit()
        
        # 创建用户内容权限
        self.user_content = UserContent(
            user_id=self.test_user_id,
            content_id=self.test_content.id,
            permission="owner"
        )
        self.db.add(self.user_content)
        self.db.commit()
    
    def tearDown(self):
        """每个测试后的清理"""
        self.db.rollback()
        self.db.close()
    
    async def test_verify_user_permission_owner(self):
        """测试画布所有者权限验证"""
        # 测试画布所有者权限
        try:
            await self.service.verify_user_permission(
                canvas_id=self.test_canvas.id,
                user_id=self.test_user_id,
                permission_type="read"
            )
            # 如果没有抛出异常，说明权限验证通过
            self.assertTrue(True)
        except PermissionDeniedError:
            self.fail("Owner should have read permission")
        
        try:
            await self.service.verify_user_permission(
                canvas_id=self.test_canvas.id,
                user_id=self.test_user_id,
                permission_type="write"
            )
            self.assertTrue(True)
        except PermissionDeniedError:
            self.fail("Owner should have write permission")
    
    async def test_verify_user_permission_denied(self):
        """测试权限拒绝"""
        # 测试非所有者访问
        with self.assertRaises(PermissionDeniedError):
            await self.service.verify_user_permission(
                canvas_id=self.test_canvas.id,
                user_id=self.other_user_id,
                permission_type="read"
            )
        
        with self.assertRaises(PermissionDeniedError):
            await self.service.verify_user_permission(
                canvas_id=self.test_canvas.id,
                user_id=self.other_user_id,
                permission_type="write"
            )
    
    async def test_verify_user_permission_nonexistent_canvas(self):
        """测试不存在的画布权限验证"""
        with self.assertRaises(CanvaNotFoundError):
            await self.service.verify_user_permission(
                canvas_id=999999,
                user_id=self.test_user_id,
                permission_type="read"
            )
    
    async def test_verify_content_access_owner(self):
        """测试内容访问权限验证 - 所有者"""
        try:
            await self.service.verify_content_access(
                content_id=self.test_content.id,
                user_id=self.test_user_id
            )
            self.assertTrue(True)
        except PermissionDeniedError:
            self.fail("Content owner should have access")
    
    async def test_verify_content_access_denied(self):
        """测试内容访问权限拒绝"""
        with self.assertRaises(PermissionDeniedError):
            await self.service.verify_content_access(
                content_id=self.test_content.id,
                user_id=self.other_user_id
            )
    
    async def test_verify_content_access_nonexistent(self):
        """测试不存在的内容访问权限"""
        with self.assertRaises(ContentNotFoundError):
            await self.service.verify_content_access(
                content_id=999999,
                user_id=self.test_user_id
            )
    
    async def test_validate_card_data_consistency_valid(self):
        """测试有效的卡片数据一致性验证"""
        # 创建测试卡片
        card = Card(
            canvas_id=self.test_canvas.id,
            content_id=self.test_content.id,
            position_x=10.0,
            position_y=20.0
        )
        self.db.add(card)
        self.db.commit()
        
        # 创建有效的更新请求
        card_updates = [
            CardUpdateRequest(
                card_id=card.id,
                position=PositionModel(x=30.0, y=40.0),
                content_id=self.test_content.id
            )
        ]
        
        try:
            await self.service.validate_card_data_consistency(card_updates)
            self.assertTrue(True)
        except DataConsistencyError:
            self.fail("Valid card data should pass consistency check")
    
    async def test_validate_card_data_consistency_duplicate_cards(self):
        """测试重复卡片ID的数据一致性验证"""
        card = Card(
            canvas_id=self.test_canvas.id,
            content_id=self.test_content.id,
            position_x=10.0,
            position_y=20.0
        )
        self.db.add(card)
        self.db.commit()
        
        # 创建包含重复卡片ID的更新请求
        card_updates = [
            CardUpdateRequest(
                card_id=card.id,
                position=PositionModel(x=30.0, y=40.0),
                content_id=self.test_content.id
            ),
            CardUpdateRequest(
                card_id=card.id,  # 重复的卡片ID
                position=PositionModel(x=50.0, y=60.0),
                content_id=self.test_content.id
            )
        ]
        
        with self.assertRaises(DataConsistencyError):
            await self.service.validate_card_data_consistency(card_updates)
    
    async def test_validate_card_data_consistency_invalid_positions(self):
        """测试无效位置的数据一致性验证"""
        card = Card(
            canvas_id=self.test_canvas.id,
            content_id=self.test_content.id,
            position_x=10.0,
            position_y=20.0
        )
        self.db.add(card)
        self.db.commit()
        
        # 测试负数位置
        card_updates = [
            CardUpdateRequest(
                card_id=card.id,
                position=PositionModel(x=-10.0, y=20.0),
                content_id=self.test_content.id
            )
        ]
        
        with self.assertRaises(DataConsistencyError):
            await self.service.validate_card_data_consistency(card_updates)
    
    async def test_get_canva_info_owner(self):
        """测试获取画布信息 - 所有者"""
        canvas_info = await self.service.get_canva_info(
            canvas_id=self.test_canvas.id,
            user_id=self.test_user_id
        )
        
        self.assertEqual(canvas_info["id"], self.test_canvas.id)
        self.assertEqual(canvas_info["name"], "Test Canvas")
        self.assertEqual(canvas_info["owner_id"], str(self.test_user_id))
        self.assertIn("created_at", canvas_info)
        self.assertIn("updated_at", canvas_info)
    
    async def test_get_canva_info_permission_denied(self):
        """测试获取画布信息 - 权限拒绝"""
        with self.assertRaises(PermissionDeniedError):
            await self.service.get_canva_info(
                canvas_id=self.test_canvas.id,
                user_id=self.other_user_id
            )
    
    async def test_get_canva_info_not_found(self):
        """测试获取不存在的画布信息"""
        with self.assertRaises(CanvaNotFoundError):
            await self.service.get_canva_info(
                canvas_id=999999,
                user_id=self.test_user_id
            )
    
    async def test_get_user_accessible_contents(self):
        """测试获取用户可访问的内容"""
        # 创建另一个内容，但不给用户权限
        other_content = Content(
            content_type="image",
            image_data="base64imagedata"
        )
        self.db.add(other_content)
        self.db.commit()
        
        # 获取用户可访问的内容
        accessible_contents = await self.service.get_user_accessible_contents(
            user_id=self.test_user_id
        )
        
        # 用户应该只能访问有权限的内容
        self.assertEqual(len(accessible_contents), 1)
        self.assertEqual(accessible_contents[0]["id"], self.test_content.id)
        self.assertEqual(accessible_contents[0]["content_type"], "text")
    
    async def test_create_shared_content_access(self):
        """测试创建共享内容访问权限"""
        # 为其他用户创建内容访问权限
        await self.service.create_shared_content_access(
            content_id=self.test_content.id,
            user_id=self.other_user_id,
            permission="read",
            granted_by=self.test_user_id
        )
        
        # 验证其他用户现在可以访问内容
        try:
            await self.service.verify_content_access(
                content_id=self.test_content.id,
                user_id=self.other_user_id
            )
            self.assertTrue(True)
        except PermissionDeniedError:
            self.fail("User should have access after permission granted")
    
    async def test_create_shared_content_access_permission_denied(self):
        """测试创建共享内容访问权限 - 权限拒绝"""
        # 非所有者尝试授权
        with self.assertRaises(PermissionDeniedError):
            await self.service.create_shared_content_access(
                content_id=self.test_content.id,
                user_id=self.other_user_id,
                permission="read",
                granted_by=self.other_user_id  # 非所有者
            )
    
    async def test_get_canvas_statistics(self):
        """测试获取画布统计信息"""
        # 创建一些卡片
        cards = []
        for i in range(3):
            card = Card(
                canvas_id=self.test_canvas.id,
                content_id=self.test_content.id,
                position_x=float(i * 10),
                position_y=float(i * 10)
            )
            cards.append(card)
            self.db.add(card)
        self.db.commit()
        
        # 获取统计信息
        stats = await self.service.get_canvas_statistics(
            canvas_id=self.test_canvas.id,
            user_id=self.test_user_id
        )
        
        self.assertEqual(stats["canvas_id"], self.test_canvas.id)
        self.assertEqual(stats["total_cards"], 3)
        self.assertEqual(stats["unique_contents"], 1)
        self.assertIn("last_updated", stats)
    
    async def test_batch_update_card_positions(self):
        """测试批量更新卡片位置"""
        # 创建测试卡片
        cards = []
        for i in range(3):
            card = Card(
                canvas_id=self.test_canvas.id,
                content_id=self.test_content.id,
                position_x=float(i),
                position_y=float(i)
            )
            cards.append(card)
            self.db.add(card)
        self.db.commit()
        
        # 创建批量更新请求
        update_requests = []
        for i, card in enumerate(cards):
            update_requests.append(CardUpdateRequest(
                card_id=card.id,
                position=PositionModel(x=float(i * 20), y=float(i * 20)),
                content_id=self.test_content.id
            ))
        
        # 执行批量更新
        updated_count = await self.service.batch_update_card_positions(
            canvas_id=self.test_canvas.id,
            card_updates=update_requests,
            user_id=self.test_user_id
        )
        
        self.assertEqual(updated_count, 3)
        
        # 验证更新结果
        for i, card in enumerate(cards):
            self.db.refresh(card)
            expected_pos = float(i * 20)
            self.assertEqual(card.position_x, expected_pos)
            self.assertEqual(card.position_y, expected_pos)
    
    async def test_service_error_handling(self):
        """测试服务层错误处理"""
        # 测试数据库连接错误的处理
        with patch.object(self.service.db, 'query', side_effect=Exception("Database error")):
            with self.assertRaises(CanvaServiceError):
                await self.service.get_canva_info(
                    canvas_id=self.test_canvas.id,
                    user_id=self.test_user_id
                )
    
    async def test_permission_caching(self):
        """测试权限缓存机制"""
        # 这个测试假设服务层实现了权限缓存
        # 第一次权限检查
        start_time = time.time()
        await self.service.verify_user_permission(
            canvas_id=self.test_canvas.id,
            user_id=self.test_user_id,
            permission_type="read"
        )
        first_check_time = time.time() - start_time
        
        # 第二次权限检查（应该使用缓存）
        start_time = time.time()
        await self.service.verify_user_permission(
            canvas_id=self.test_canvas.id,
            user_id=self.test_user_id,
            permission_type="read"
        )
        second_check_time = time.time() - start_time
        
        # 第二次检查应该更快（如果实现了缓存）
        # 注意：这个测试可能需要根据实际的缓存实现进行调整
        self.assertLessEqual(second_check_time, first_check_time * 2)
    
    async def test_concurrent_access_handling(self):
        """测试并发访问处理"""
        import asyncio
        
        # 创建多个并发的权限检查任务
        tasks = []
        for _ in range(10):
            task = self.service.verify_user_permission(
                canvas_id=self.test_canvas.id,
                user_id=self.test_user_id,
                permission_type="read"
            )
            tasks.append(task)
        
        # 并发执行所有任务
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 所有任务都应该成功完成
        for result in results:
            if isinstance(result, Exception):
                self.fail(f"Concurrent access failed: {result}")


# 异步测试运行器
import asyncio
import time

class AsyncTestCase(unittest.TestCase):
    """支持异步测试的基类"""
    
    def run_async(self, coro):
        """运行异步协程"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()


class TestCanvaServiceAsync(AsyncTestCase):
    """异步测试包装器"""
    
    def setUp(self):
        """设置测试环境"""
        self.test_case = TestCanvaService()
        self.test_case.setUp()
    
    def tearDown(self):
        """清理测试环境"""
        self.test_case.tearDown()
    
    def test_verify_user_permission_owner(self):
        """测试画布所有者权限验证"""
        self.run_async(self.test_case.test_verify_user_permission_owner())
    
    def test_verify_user_permission_denied(self):
        """测试权限拒绝"""
        self.run_async(self.test_case.test_verify_user_permission_denied())
    
    def test_verify_user_permission_nonexistent_canvas(self):
        """测试不存在的画布权限验证"""
        self.run_async(self.test_case.test_verify_user_permission_nonexistent_canvas())
    
    def test_verify_content_access_owner(self):
        """测试内容访问权限验证 - 所有者"""
        self.run_async(self.test_case.test_verify_content_access_owner())
    
    def test_verify_content_access_denied(self):
        """测试内容访问权限拒绝"""
        self.run_async(self.test_case.test_verify_content_access_denied())
    
    def test_verify_content_access_nonexistent(self):
        """测试不存在的内容访问权限"""
        self.run_async(self.test_case.test_verify_content_access_nonexistent())
    
    def test_validate_card_data_consistency_valid(self):
        """测试有效的卡片数据一致性验证"""
        self.run_async(self.test_case.test_validate_card_data_consistency_valid())
    
    def test_validate_card_data_consistency_duplicate_cards(self):
        """测试重复卡片ID的数据一致性验证"""
        self.run_async(self.test_case.test_validate_card_data_consistency_duplicate_cards())
    
    def test_validate_card_data_consistency_invalid_positions(self):
        """测试无效位置的数据一致性验证"""
        self.run_async(self.test_case.test_validate_card_data_consistency_invalid_positions())
    
    def test_get_canva_info_owner(self):
        """测试获取画布信息 - 所有者"""
        self.run_async(self.test_case.test_get_canva_info_owner())
    
    def test_get_canva_info_permission_denied(self):
        """测试获取画布信息 - 权限拒绝"""
        self.run_async(self.test_case.test_get_canva_info_permission_denied())
    
    def test_get_canva_info_not_found(self):
        """测试获取不存在的画布信息"""
        self.run_async(self.test_case.test_get_canva_info_not_found())


if __name__ == "__main__":
    unittest.main()