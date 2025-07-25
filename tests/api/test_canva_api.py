"""
API端点单元测试

测试画布API端点的请求处理、响应格式、错误处理和权限验证。
"""

import unittest
from unittest.mock import Mock, patch, AsyncMock
import json
from uuid import uuid4
from fastapi.testclient import TestClient
from fastapi import status
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.db.base import Base
from app.db.session import get_db
from app.models.canvas import Canvas
from app.models.card import Card
from app.models.content import Content
from app.models.user_content import UserContent
from app.models.user import User
from app.api.v2.auth import get_current_user


class TestAPIEndpoints(unittest.TestCase):
    """API端点单元测试类"""
    
    @classmethod
    def setUpClass(cls):
        """设置测试环境"""
        # 使用PostgreSQL测试数据库
        import os
        test_db_url = os.getenv("TEST_DATABASE_URL", "postgresql://postgres:password@localhost:5432/cogniblock_test")
        cls.engine = create_engine(test_db_url, echo=False)
        Base.metadata.create_all(cls.engine)
        cls.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=cls.engine)
        
        # 创建测试客户端
        cls.client = TestClient(app)
    
    def setUp(self):
        """每个测试前的设置"""
        self.db = self.SessionLocal()
        
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
        
        # 创建测试卡片
        self.test_card = Card(
            canvas_id=self.test_canvas.id,
            content_id=self.test_content.id,
            position_x=10.5,
            position_y=20.3
        )
        self.db.add(self.test_card)
        self.db.commit()
        
        # 模拟依赖注入
        def override_get_db():
            try:
                yield self.db
            finally:
                pass
        
        def override_get_current_user():
            return self.test_user
        
        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user
    
    def tearDown(self):
        """每个测试后的清理"""
        app.dependency_overrides.clear()
        self.db.rollback()
        self.db.close()
    
    def test_pull_canvas_success(self):
        """测试Pull API成功响应"""
        # 准备请求数据
        request_data = {
            "canva_id": self.test_canvas.id
        }
        
        # 发送请求
        response = self.client.post(
            "/api/v2/canva/pull",
            json=request_data,
            headers={"X-User-ID": str(self.test_user_id)}
        )
        
        # 验证响应
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        response_data = response.json()
        self.assertIsInstance(response_data, list)
        self.assertEqual(len(response_data), 1)
        
        card_data = response_data[0]
        self.assertEqual(card_data["card_id"], self.test_card.id)
        self.assertEqual(card_data["position"]["x"], 10.5)
        self.assertEqual(card_data["position"]["y"], 20.3)
        self.assertEqual(card_data["content_id"], self.test_content.id)
    
    def test_pull_canvas_not_found(self):
        """测试Pull API - 画布不存在"""
        request_data = {
            "canva_id": 999999
        }
        
        response = self.client.post(
            "/api/v2/canva/pull",
            json=request_data,
            headers={"X-User-ID": str(self.test_user_id)}
        )
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn("not found", response.json()["detail"].lower())
    
    def test_pull_canvas_permission_denied(self):
        """测试Pull API - 权限拒绝"""
        # 使用其他用户的认证
        def override_get_current_user():
            return self.other_user
        
        app.dependency_overrides[get_current_user] = override_get_current_user
        
        request_data = {
            "canva_id": self.test_canvas.id
        }
        
        response = self.client.post(
            "/api/v2/canva/pull",
            json=request_data,
            headers={"X-User-ID": str(self.other_user_id)}
        )
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_pull_canvas_invalid_request(self):
        """测试Pull API - 无效请求"""
        # 缺少canva_id
        request_data = {}
        
        response = self.client.post(
            "/api/v2/canva/pull",
            json=request_data,
            headers={"X-User-ID": str(self.test_user_id)}
        )
        
        self.assertEqual(response.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)
    
    def test_push_canvas_success(self):
        """测试Push API成功响应"""
        request_data = {
            "canva_id": self.test_canvas.id,
            "cards": [
                {
                    "card_id": self.test_card.id,
                    "position": {"x": 30.5, "y": 40.7},
                    "content_id": self.test_content.id
                }
            ]
        }
        
        response = self.client.post(
            "/api/v2/canva/push",
            json=request_data,
            headers={"X-User-ID": str(self.test_user_id)}
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        response_data = response.json()
        self.assertIn("message", response_data)
        self.assertEqual(response_data["canvas_id"], self.test_canvas.id)
        self.assertEqual(response_data["updated_cards"], 1)
        
        # 验证数据库中的数据已更新
        self.db.refresh(self.test_card)
        self.assertEqual(self.test_card.position_x, 30.5)
        self.assertEqual(self.test_card.position_y, 40.7)
    
    def test_push_canvas_batch_update(self):
        """测试Push API批量更新"""
        # 创建更多测试卡片
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
        
        # 准备批量更新请求
        request_data = {
            "canva_id": self.test_canvas.id,
            "cards": []
        }
        
        for i, card in enumerate(cards):
            request_data["cards"].append({
                "card_id": card.id,
                "position": {"x": float(i * 10), "y": float(i * 10)},
                "content_id": self.test_content.id
            })
        
        response = self.client.post(
            "/api/v2/canva/push",
            json=request_data,
            headers={"X-User-ID": str(self.test_user_id)}
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["updated_cards"], 3)
        
        # 验证所有卡片都已更新
        for i, card in enumerate(cards):
            self.db.refresh(card)
            expected_pos = float(i * 10)
            self.assertEqual(card.position_x, expected_pos)
            self.assertEqual(card.position_y, expected_pos)
    
    def test_push_canvas_card_not_found(self):
        """测试Push API - 卡片不存在"""
        request_data = {
            "canva_id": self.test_canvas.id,
            "cards": [
                {
                    "card_id": 999999,  # 不存在的卡片ID
                    "position": {"x": 30.5, "y": 40.7},
                    "content_id": self.test_content.id
                }
            ]
        }
        
        response = self.client.post(
            "/api/v2/canva/push",
            json=request_data,
            headers={"X-User-ID": str(self.test_user_id)}
        )
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn("not found", response.json()["detail"].lower())
    
    def test_push_canvas_card_wrong_canvas(self):
        """测试Push API - 卡片不属于指定画布"""
        # 创建另一个画布和卡片
        other_canvas = Canvas(owner_id=self.test_user_id, name="Other Canvas")
        self.db.add(other_canvas)
        self.db.commit()
        
        other_card = Card(
            canvas_id=other_canvas.id,
            content_id=self.test_content.id,
            position_x=0.0,
            position_y=0.0
        )
        self.db.add(other_card)
        self.db.commit()
        
        # 尝试在错误的画布中更新卡片
        request_data = {
            "canva_id": self.test_canvas.id,
            "cards": [
                {
                    "card_id": other_card.id,  # 属于其他画布的卡片
                    "position": {"x": 30.5, "y": 40.7},
                    "content_id": self.test_content.id
                }
            ]
        }
        
        response = self.client.post(
            "/api/v2/canva/push",
            json=request_data,
            headers={"X-User-ID": str(self.test_user_id)}
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("does not belong", response.json()["detail"])
    
    def test_push_canvas_permission_denied(self):
        """测试Push API - 权限拒绝"""
        def override_get_current_user():
            return self.other_user
        
        app.dependency_overrides[get_current_user] = override_get_current_user
        
        request_data = {
            "canva_id": self.test_canvas.id,
            "cards": [
                {
                    "card_id": self.test_card.id,
                    "position": {"x": 30.5, "y": 40.7},
                    "content_id": self.test_content.id
                }
            ]
        }
        
        response = self.client.post(
            "/api/v2/canva/push",
            json=request_data,
            headers={"X-User-ID": str(self.other_user_id)}
        )
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_push_canvas_invalid_data(self):
        """测试Push API - 无效数据"""
        # 测试负数位置
        request_data = {
            "canva_id": self.test_canvas.id,
            "cards": [
                {
                    "card_id": self.test_card.id,
                    "position": {"x": -10.0, "y": 20.0},  # 负数位置
                    "content_id": self.test_content.id
                }
            ]
        }
        
        response = self.client.post(
            "/api/v2/canva/push",
            json=request_data,
            headers={"X-User-ID": str(self.test_user_id)}
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_push_canvas_empty_cards(self):
        """测试Push API - 空卡片列表"""
        request_data = {
            "canva_id": self.test_canvas.id,
            "cards": []
        }
        
        response = self.client.post(
            "/api/v2/canva/push",
            json=request_data,
            headers={"X-User-ID": str(self.test_user_id)}
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_get_canvas_info_success(self):
        """测试获取画布信息成功"""
        response = self.client.get(
            f"/api/v2/canva/info/{self.test_canvas.id}",
            headers={"X-User-ID": str(self.test_user_id)}
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        response_data = response.json()
        self.assertEqual(response_data["id"], self.test_canvas.id)
        self.assertEqual(response_data["name"], "Test Canvas")
        self.assertEqual(response_data["owner_id"], str(self.test_user_id))
        self.assertIn("created_at", response_data)
        self.assertIn("updated_at", response_data)
    
    def test_get_canvas_info_not_found(self):
        """测试获取画布信息 - 画布不存在"""
        response = self.client.get(
            "/api/v2/canva/info/999999",
            headers={"X-User-ID": str(self.test_user_id)}
        )
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_get_canvas_info_permission_denied(self):
        """测试获取画布信息 - 权限拒绝"""
        def override_get_current_user():
            return self.other_user
        
        app.dependency_overrides[get_current_user] = override_get_current_user
        
        response = self.client.get(
            f"/api/v2/canva/info/{self.test_canvas.id}",
            headers={"X-User-ID": str(self.other_user_id)}
        )
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_authentication_required(self):
        """测试认证要求"""
        # 清除认证依赖覆盖
        app.dependency_overrides.clear()
        
        request_data = {
            "canva_id": self.test_canvas.id
        }
        
        # 不提供认证头
        response = self.client.post(
            "/api/v2/canva/pull",
            json=request_data
        )
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_invalid_user_id_header(self):
        """测试无效的用户ID头"""
        app.dependency_overrides.clear()
        
        request_data = {
            "canva_id": self.test_canvas.id
        }
        
        response = self.client.post(
            "/api/v2/canva/pull",
            json=request_data,
            headers={"X-User-ID": "invalid-uuid"}
        )
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_api_response_format(self):
        """测试API响应格式"""
        # 测试Pull API响应格式
        request_data = {"canva_id": self.test_canvas.id}
        
        response = self.client.post(
            "/api/v2/canva/pull",
            json=request_data,
            headers={"X-User-ID": str(self.test_user_id)}
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.headers["content-type"], "application/json")
        
        # 验证响应结构
        response_data = response.json()
        self.assertIsInstance(response_data, list)
        
        if response_data:
            card = response_data[0]
            required_fields = ["card_id", "position", "content_id"]
            for field in required_fields:
                self.assertIn(field, card)
            
            self.assertIn("x", card["position"])
            self.assertIn("y", card["position"])
    
    def test_api_error_response_format(self):
        """测试API错误响应格式"""
        request_data = {"canva_id": 999999}
        
        response = self.client.post(
            "/api/v2/canva/pull",
            json=request_data,
            headers={"X-User-ID": str(self.test_user_id)}
        )
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        
        error_data = response.json()
        self.assertIn("detail", error_data)
        self.assertIsInstance(error_data["detail"], str)
    
    def test_api_performance(self):
        """测试API性能"""
        import time
        
        # 创建大量测试数据
        cards = []
        for i in range(50):
            card = Card(
                canvas_id=self.test_canvas.id,
                content_id=self.test_content.id,
                position_x=float(i),
                position_y=float(i)
            )
            cards.append(card)
            self.db.add(card)
        self.db.commit()
        
        # 测试Pull API性能
        start_time = time.time()
        response = self.client.post(
            "/api/v2/canva/pull",
            json={"canva_id": self.test_canvas.id},
            headers={"X-User-ID": str(self.test_user_id)}
        )
        pull_time = time.time() - start_time
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertLess(pull_time, 2.0)  # 应该在2秒内完成
        
        # 测试Push API性能
        push_data = {
            "canva_id": self.test_canvas.id,
            "cards": [
                {
                    "card_id": card.id,
                    "position": {"x": float(i * 2), "y": float(i * 2)},
                    "content_id": self.test_content.id
                }
                for i, card in enumerate(cards[:10])  # 只更新前10个卡片
            ]
        }
        
        start_time = time.time()
        response = self.client.post(
            "/api/v2/canva/push",
            json=push_data,
            headers={"X-User-ID": str(self.test_user_id)}
        )
        push_time = time.time() - start_time
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertLess(push_time, 3.0)  # 应该在3秒内完成


if __name__ == "__main__":
    unittest.main()