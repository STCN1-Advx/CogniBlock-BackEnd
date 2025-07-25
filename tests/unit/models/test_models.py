"""
数据模型单元测试

测试所有画布相关数据模型的约束、关系和验证规则。
"""

import unittest
from datetime import datetime
from uuid import uuid4, UUID
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError

from app.db.base import Base
from app.models.canvas import Canvas
from app.models.card import Card
from app.models.content import Content
from app.models.user_content import UserContent
from app.models.user import User


class TestDataModels(unittest.TestCase):
    """数据模型单元测试类"""
    
    @classmethod
    def setUpClass(cls):
        """设置测试数据库"""
        # 使用PostgreSQL测试数据库
        import os
        test_db_url = os.getenv("TEST_DATABASE_URL", "postgresql://postgres:password@localhost:5432/cogniblock_test")
        cls.engine = create_engine(test_db_url, echo=False)
        Base.metadata.create_all(cls.engine)
        cls.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=cls.engine)
    
    def setUp(self):
        """每个测试前的设置"""
        self.db = self.SessionLocal()
        
        # 创建测试用户
        self.test_user_id = uuid4()
        self.test_user = User(
            id=self.test_user_id,
            oauth_id="test_oauth_123",
            name="Test User",
            email="test@example.com"
        )
        self.db.add(self.test_user)
        self.db.commit()
    
    def tearDown(self):
        """每个测试后的清理"""
        self.db.rollback()
        self.db.close()
    
    def test_canvas_model_creation(self):
        """测试Canvas模型创建"""
        canvas = Canvas(
            owner_id=self.test_user_id,
            name="Test Canvas"
        )
        self.db.add(canvas)
        self.db.commit()
        
        # 验证Canvas创建成功
        self.assertIsNotNone(canvas.id)
        self.assertEqual(canvas.owner_id, self.test_user_id)
        self.assertEqual(canvas.name, "Test Canvas")
        self.assertIsInstance(canvas.created_at, datetime)
        self.assertIsInstance(canvas.updated_at, datetime)
    
    def test_canvas_model_constraints(self):
        """测试Canvas模型约束"""
        # 测试owner_id外键约束
        invalid_user_id = uuid4()
        canvas = Canvas(
            owner_id=invalid_user_id,
            name="Invalid Canvas"
        )
        self.db.add(canvas)
        
        with self.assertRaises(IntegrityError):
            self.db.commit()
    
    def test_content_model_creation(self):
        """测试Content模型创建"""
        # 测试文本内容
        text_content = Content(
            content_type="text",
            text_data="This is test text content"
        )
        self.db.add(text_content)
        self.db.commit()
        
        self.assertIsNotNone(text_content.id)
        self.assertEqual(text_content.content_type, "text")
        self.assertEqual(text_content.text_data, "This is test text content")
        self.assertIsNone(text_content.image_data)
        
        # 测试图片内容
        image_content = Content(
            content_type="image",
            image_data="base64encodedimagedata"
        )
        self.db.add(image_content)
        self.db.commit()
        
        self.assertIsNotNone(image_content.id)
        self.assertEqual(image_content.content_type, "image")
        self.assertEqual(image_content.image_data, "base64encodedimagedata")
        self.assertIsNone(image_content.text_data)
    
    def test_content_model_validation(self):
        """测试Content模型验证"""
        # 测试content_type不能为空
        with self.assertRaises(IntegrityError):
            content = Content(
                content_type=None,
                text_data="Test"
            )
            self.db.add(content)
            self.db.commit()
    
    def test_card_model_creation(self):
        """测试Card模型创建"""
        # 先创建Canvas和Content
        canvas = Canvas(owner_id=self.test_user_id, name="Test Canvas")
        content = Content(content_type="text", text_data="Test content")
        self.db.add(canvas)
        self.db.add(content)
        self.db.commit()
        
        # 创建Card
        card = Card(
            canvas_id=canvas.id,
            content_id=content.id,
            position_x=10.5,
            position_y=20.3
        )
        self.db.add(card)
        self.db.commit()
        
        self.assertIsNotNone(card.id)
        self.assertEqual(card.canvas_id, canvas.id)
        self.assertEqual(card.content_id, content.id)
        self.assertEqual(card.position_x, 10.5)
        self.assertEqual(card.position_y, 20.3)
    
    def test_card_model_constraints(self):
        """测试Card模型约束"""
        # 测试canvas_id外键约束
        content = Content(content_type="text", text_data="Test")
        self.db.add(content)
        self.db.commit()
        
        card = Card(
            canvas_id=999999,  # 不存在的canvas_id
            content_id=content.id,
            position_x=0.0,
            position_y=0.0
        )
        self.db.add(card)
        
        with self.assertRaises(IntegrityError):
            self.db.commit()
    
    def test_card_position_validation(self):
        """测试Card位置验证"""
        canvas = Canvas(owner_id=self.test_user_id, name="Test Canvas")
        content = Content(content_type="text", text_data="Test")
        self.db.add(canvas)
        self.db.add(content)
        self.db.commit()
        
        # 测试position不能为空
        with self.assertRaises(IntegrityError):
            card = Card(
                canvas_id=canvas.id,
                content_id=content.id,
                position_x=None,
                position_y=20.0
            )
            self.db.add(card)
            self.db.commit()
    
    def test_user_content_model_creation(self):
        """测试UserContent模型创建"""
        content = Content(content_type="text", text_data="Test content")
        self.db.add(content)
        self.db.commit()
        
        user_content = UserContent(
            user_id=self.test_user_id,
            content_id=content.id,
            permission="read"
        )
        self.db.add(user_content)
        self.db.commit()
        
        self.assertIsNotNone(user_content.id)
        self.assertEqual(user_content.user_id, self.test_user_id)
        self.assertEqual(user_content.content_id, content.id)
        self.assertEqual(user_content.permission, "read")
    
    def test_user_content_unique_constraint(self):
        """测试UserContent唯一约束"""
        content = Content(content_type="text", text_data="Test content")
        self.db.add(content)
        self.db.commit()
        
        # 创建第一个用户内容关联
        user_content1 = UserContent(
            user_id=self.test_user_id,
            content_id=content.id,
            permission="read"
        )
        self.db.add(user_content1)
        self.db.commit()
        
        # 尝试创建重复的用户内容关联
        user_content2 = UserContent(
            user_id=self.test_user_id,
            content_id=content.id,
            permission="write"
        )
        self.db.add(user_content2)
        
        with self.assertRaises(IntegrityError):
            self.db.commit()
    
    def test_model_relationships(self):
        """测试模型关系"""
        # 创建完整的关系链
        canvas = Canvas(owner_id=self.test_user_id, name="Test Canvas")
        content = Content(content_type="text", text_data="Test content")
        self.db.add(canvas)
        self.db.add(content)
        self.db.commit()
        
        card = Card(
            canvas_id=canvas.id,
            content_id=content.id,
            position_x=10.0,
            position_y=20.0
        )
        self.db.add(card)
        self.db.commit()
        
        user_content = UserContent(
            user_id=self.test_user_id,
            content_id=content.id,
            permission="owner"
        )
        self.db.add(user_content)
        self.db.commit()
        
        # 验证关系
        self.assertEqual(card.canvas_id, canvas.id)
        self.assertEqual(card.content_id, content.id)
        self.assertEqual(user_content.user_id, self.test_user_id)
        self.assertEqual(user_content.content_id, content.id)
    
    def test_cascade_delete(self):
        """测试级联删除"""
        canvas = Canvas(owner_id=self.test_user_id, name="Test Canvas")
        content = Content(content_type="text", text_data="Test content")
        self.db.add(canvas)
        self.db.add(content)
        self.db.commit()
        
        card = Card(
            canvas_id=canvas.id,
            content_id=content.id,
            position_x=10.0,
            position_y=20.0
        )
        self.db.add(card)
        self.db.commit()
        
        # 删除canvas，应该级联删除card
        self.db.delete(canvas)
        self.db.commit()
        
        # 验证card被删除
        remaining_card = self.db.query(Card).filter(Card.id == card.id).first()
        self.assertIsNone(remaining_card)
    
    def test_model_timestamps(self):
        """测试模型时间戳"""
        canvas = Canvas(owner_id=self.test_user_id, name="Test Canvas")
        self.db.add(canvas)
        self.db.commit()
        
        # 验证创建时间
        self.assertIsNotNone(canvas.created_at)
        self.assertIsNotNone(canvas.updated_at)
        
        # 记录原始时间
        original_updated_at = canvas.updated_at
        
        # 更新canvas
        canvas.name = "Updated Canvas"
        self.db.commit()
        
        # 验证更新时间改变
        self.assertGreater(canvas.updated_at, original_updated_at)


if __name__ == "__main__":
    unittest.main()