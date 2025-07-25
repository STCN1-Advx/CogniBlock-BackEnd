"""
简化的数据模型单元测试

使用简单的PostgreSQL配置进行测试
"""

import unittest
import os
from datetime import datetime
from uuid import uuid4
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
        # 简单的PostgreSQL测试配置
        test_db_url = os.getenv("TEST_DATABASE_URL", "postgresql://postgres:password@localhost:5432/cogniblock_test")
        cls.engine = create_engine(test_db_url, echo=False)
        
        # 创建所有表（如果不存在）
        try:
            Base.metadata.create_all(cls.engine)
        except Exception as e:
            print(f"警告: 创建表时出错 {e}")
            
        cls.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=cls.engine)
    
    def setUp(self):
        """每个测试前的设置"""
        self.db = self.SessionLocal()
        
        # 清理测试数据
        try:
            self.db.query(Card).delete()
            self.db.query(UserContent).delete()
            self.db.query(Content).delete()
            self.db.query(Canvas).delete()
            self.db.query(User).delete()
            self.db.commit()
        except:
            self.db.rollback()
        
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
        try:
            self.db.rollback()
        except:
            pass
        finally:
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


if __name__ == "__main__":
    unittest.main()