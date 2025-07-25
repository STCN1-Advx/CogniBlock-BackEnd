"""
CRUD操作单元测试

测试所有画布相关CRUD操作的功能、性能和错误处理。
"""

import unittest
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
from app.crud import canvas as canvas_crud
from app.crud import card as card_crud
from app.crud import content as content_crud
from app.schemas.canva import CanvasCreate, CanvasUpdate, ContentCreate, ContentUpdate


class TestCRUDOperations(unittest.TestCase):
    """CRUD操作单元测试类"""
    
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
    
    def test_canvas_crud_create(self):
        """测试Canvas CRUD创建操作"""
        canvas_data = CanvasCreate(
            owner_id=self.test_user_id,
            name="Test Canvas"
        )
        
        canvas = canvas_crud.create(self.db, obj_in=canvas_data)
        
        self.assertIsNotNone(canvas.id)
        self.assertEqual(canvas.owner_id, self.test_user_id)
        self.assertEqual(canvas.name, "Test Canvas")
        self.assertIsInstance(canvas.created_at, datetime)
    
    def test_canvas_crud_get(self):
        """测试Canvas CRUD获取操作"""
        # 创建测试canvas
        canvas = Canvas(owner_id=self.test_user_id, name="Test Canvas")
        self.db.add(canvas)
        self.db.commit()
        
        # 测试通过ID获取
        retrieved_canvas = canvas_crud.get(self.db, id=canvas.id)
        self.assertIsNotNone(retrieved_canvas)
        self.assertEqual(retrieved_canvas.id, canvas.id)
        self.assertEqual(retrieved_canvas.name, "Test Canvas")
        
        # 测试获取不存在的canvas
        non_existent = canvas_crud.get(self.db, id=999999)
        self.assertIsNone(non_existent)
    
    def test_canvas_crud_get_multi(self):
        """测试Canvas CRUD批量获取操作"""
        # 创建多个canvas
        canvases = []
        for i in range(3):
            canvas = Canvas(owner_id=self.test_user_id, name=f"Canvas {i}")
            canvases.append(canvas)
            self.db.add(canvas)
        self.db.commit()
        
        # 测试批量获取
        retrieved_canvases = canvas_crud.get_multi(self.db, skip=0, limit=10)
        self.assertEqual(len(retrieved_canvases), 3)
        
        # 测试分页
        paginated_canvases = canvas_crud.get_multi(self.db, skip=1, limit=2)
        self.assertEqual(len(paginated_canvases), 2)
    
    def test_canvas_crud_update(self):
        """测试Canvas CRUD更新操作"""
        # 创建测试canvas
        canvas = Canvas(owner_id=self.test_user_id, name="Original Canvas")
        self.db.add(canvas)
        self.db.commit()
        
        # 更新canvas
        update_data = CanvasUpdate(name="Updated Canvas")
        updated_canvas = canvas_crud.update(self.db, db_obj=canvas, obj_in=update_data)
        
        self.assertEqual(updated_canvas.name, "Updated Canvas")
        self.assertEqual(updated_canvas.id, canvas.id)
        
        # 验证数据库中的数据已更新
        db_canvas = canvas_crud.get(self.db, id=canvas.id)
        self.assertEqual(db_canvas.name, "Updated Canvas")
    
    def test_canvas_crud_delete(self):
        """测试Canvas CRUD删除操作"""
        # 创建测试canvas
        canvas = Canvas(owner_id=self.test_user_id, name="To Delete Canvas")
        self.db.add(canvas)
        self.db.commit()
        canvas_id = canvas.id
        
        # 删除canvas
        deleted_canvas = canvas_crud.remove(self.db, id=canvas_id)
        self.assertIsNotNone(deleted_canvas)
        self.assertEqual(deleted_canvas.id, canvas_id)
        
        # 验证canvas已被删除
        retrieved_canvas = canvas_crud.get(self.db, id=canvas_id)
        self.assertIsNone(retrieved_canvas)
    
    def test_canvas_crud_get_by_owner(self):
        """测试按所有者获取Canvas"""
        # 创建另一个用户
        other_user_id = uuid4()
        other_user = User(
            id=other_user_id,
            oauth_id="other_oauth_123",
            name="Other User",
            email="other@example.com"
        )
        self.db.add(other_user)
        self.db.commit()
        
        # 为不同用户创建canvas
        canvas1 = Canvas(owner_id=self.test_user_id, name="User1 Canvas")
        canvas2 = Canvas(owner_id=other_user_id, name="User2 Canvas")
        canvas3 = Canvas(owner_id=self.test_user_id, name="User1 Canvas 2")
        
        self.db.add_all([canvas1, canvas2, canvas3])
        self.db.commit()
        
        # 测试按所有者获取
        user1_canvases = canvas_crud.get_by_owner(self.db, owner_id=self.test_user_id)
        self.assertEqual(len(user1_canvases), 2)
        
        user2_canvases = canvas_crud.get_by_owner(self.db, owner_id=other_user_id)
        self.assertEqual(len(user2_canvases), 1)
    
    def test_content_crud_create(self):
        """测试Content CRUD创建操作"""
        # 测试文本内容创建
        text_content_data = ContentCreate(
            content_type="text",
            text_data="This is test text"
        )
        
        text_content = content_crud.create(self.db, obj_in=text_content_data)
        self.assertIsNotNone(text_content.id)
        self.assertEqual(text_content.content_type, "text")
        self.assertEqual(text_content.text_data, "This is test text")
        self.assertIsNone(text_content.image_data)
        
        # 测试图片内容创建
        image_content_data = ContentCreate(
            content_type="image",
            image_data="base64encodeddata"
        )
        
        image_content = content_crud.create(self.db, obj_in=image_content_data)
        self.assertIsNotNone(image_content.id)
        self.assertEqual(image_content.content_type, "image")
        self.assertEqual(image_content.image_data, "base64encodeddata")
        self.assertIsNone(image_content.text_data)
    
    def test_content_crud_get_by_type(self):
        """测试按类型获取Content"""
        # 创建不同类型的内容
        text_content = Content(content_type="text", text_data="Text content")
        image_content = Content(content_type="image", image_data="Image data")
        
        self.db.add_all([text_content, image_content])
        self.db.commit()
        
        # 测试按类型获取
        text_contents = content_crud.get_by_type(self.db, content_type="text")
        self.assertEqual(len(text_contents), 1)
        self.assertEqual(text_contents[0].content_type, "text")
        
        image_contents = content_crud.get_by_type(self.db, content_type="image")
        self.assertEqual(len(image_contents), 1)
        self.assertEqual(image_contents[0].content_type, "image")
    
    def test_content_crud_update(self):
        """测试Content CRUD更新操作"""
        # 创建测试内容
        content = Content(content_type="text", text_data="Original text")
        self.db.add(content)
        self.db.commit()
        
        # 更新内容
        update_data = ContentUpdate(text_data="Updated text")
        updated_content = content_crud.update(self.db, db_obj=content, obj_in=update_data)
        
        self.assertEqual(updated_content.text_data, "Updated text")
        self.assertEqual(updated_content.content_type, "text")
    
    def test_card_crud_create(self):
        """测试Card CRUD创建操作"""
        # 创建依赖数据
        canvas = Canvas(owner_id=self.test_user_id, name="Test Canvas")
        content = Content(content_type="text", text_data="Test content")
        self.db.add_all([canvas, content])
        self.db.commit()
        
        # 创建card
        card_data = {
            "canvas_id": canvas.id,
            "content_id": content.id,
            "position_x": 10.5,
            "position_y": 20.3
        }
        
        card = card_crud.create(self.db, obj_in=card_data)
        self.assertIsNotNone(card.id)
        self.assertEqual(card.canvas_id, canvas.id)
        self.assertEqual(card.content_id, content.id)
        self.assertEqual(card.position_x, 10.5)
        self.assertEqual(card.position_y, 20.3)
    
    def test_card_crud_get_by_canvas(self):
        """测试按画布获取Card"""
        # 创建依赖数据
        canvas1 = Canvas(owner_id=self.test_user_id, name="Canvas 1")
        canvas2 = Canvas(owner_id=self.test_user_id, name="Canvas 2")
        content = Content(content_type="text", text_data="Test content")
        self.db.add_all([canvas1, canvas2, content])
        self.db.commit()
        
        # 为不同canvas创建card
        card1 = Card(canvas_id=canvas1.id, content_id=content.id, position_x=1.0, position_y=1.0)
        card2 = Card(canvas_id=canvas1.id, content_id=content.id, position_x=2.0, position_y=2.0)
        card3 = Card(canvas_id=canvas2.id, content_id=content.id, position_x=3.0, position_y=3.0)
        
        self.db.add_all([card1, card2, card3])
        self.db.commit()
        
        # 测试按canvas获取
        canvas1_cards = card_crud.get_by_canvas(self.db, canvas_id=canvas1.id)
        self.assertEqual(len(canvas1_cards), 2)
        
        canvas2_cards = card_crud.get_by_canvas(self.db, canvas_id=canvas2.id)
        self.assertEqual(len(canvas2_cards), 1)
    
    def test_card_crud_update_position(self):
        """测试Card位置更新"""
        # 创建依赖数据
        canvas = Canvas(owner_id=self.test_user_id, name="Test Canvas")
        content = Content(content_type="text", text_data="Test content")
        self.db.add_all([canvas, content])
        self.db.commit()
        
        # 创建card
        card = Card(canvas_id=canvas.id, content_id=content.id, position_x=10.0, position_y=20.0)
        self.db.add(card)
        self.db.commit()
        
        # 更新位置
        update_data = {
            "position_x": 30.5,
            "position_y": 40.7
        }
        updated_card = card_crud.update(self.db, db_obj=card, obj_in=update_data)
        
        self.assertEqual(updated_card.position_x, 30.5)
        self.assertEqual(updated_card.position_y, 40.7)
        self.assertEqual(updated_card.canvas_id, canvas.id)
        self.assertEqual(updated_card.content_id, content.id)
    
    def test_card_crud_batch_update(self):
        """测试Card批量更新"""
        # 创建依赖数据
        canvas = Canvas(owner_id=self.test_user_id, name="Test Canvas")
        content = Content(content_type="text", text_data="Test content")
        self.db.add_all([canvas, content])
        self.db.commit()
        
        # 创建多个card
        cards = []
        for i in range(3):
            card = Card(
                canvas_id=canvas.id,
                content_id=content.id,
                position_x=float(i),
                position_y=float(i)
            )
            cards.append(card)
            self.db.add(card)
        self.db.commit()
        
        # 批量更新
        update_data = [
            {"card_id": cards[0].id, "position_x": 10.0, "position_y": 10.0},
            {"card_id": cards[1].id, "position_x": 20.0, "position_y": 20.0},
            {"card_id": cards[2].id, "position_x": 30.0, "position_y": 30.0}
        ]
        
        updated_cards = card_crud.batch_update_positions(self.db, updates=update_data)
        self.assertEqual(len(updated_cards), 3)
        
        # 验证更新结果
        for i, card in enumerate(updated_cards):
            expected_pos = float((i + 1) * 10)
            self.assertEqual(card.position_x, expected_pos)
            self.assertEqual(card.position_y, expected_pos)
    
    def test_crud_error_handling(self):
        """测试CRUD错误处理"""
        # 测试获取不存在的记录
        non_existent_canvas = canvas_crud.get(self.db, id=999999)
        self.assertIsNone(non_existent_canvas)
        
        # 测试删除不存在的记录
        deleted_canvas = canvas_crud.remove(self.db, id=999999)
        self.assertIsNone(deleted_canvas)
        
        # 测试外键约束错误
        with self.assertRaises(IntegrityError):
            invalid_card_data = {
                "canvas_id": 999999,  # 不存在的canvas_id
                "content_id": 1,
                "position_x": 0.0,
                "position_y": 0.0
            }
            card_crud.create(self.db, obj_in=invalid_card_data)
    
    def test_crud_performance(self):
        """测试CRUD性能"""
        import time
        
        # 创建大量数据进行性能测试
        canvas = Canvas(owner_id=self.test_user_id, name="Performance Test Canvas")
        self.db.add(canvas)
        self.db.commit()
        
        content = Content(content_type="text", text_data="Performance test content")
        self.db.add(content)
        self.db.commit()
        
        # 批量创建card
        start_time = time.time()
        cards = []
        for i in range(100):
            card = Card(
                canvas_id=canvas.id,
                content_id=content.id,
                position_x=float(i),
                position_y=float(i)
            )
            cards.append(card)
        
        self.db.add_all(cards)
        self.db.commit()
        create_time = time.time() - start_time
        
        # 批量查询
        start_time = time.time()
        retrieved_cards = card_crud.get_by_canvas(self.db, canvas_id=canvas.id)
        query_time = time.time() - start_time
        
        # 验证性能（这些阈值可以根据实际需求调整）
        self.assertLess(create_time, 5.0)  # 创建100个card应该在5秒内完成
        self.assertLess(query_time, 1.0)   # 查询100个card应该在1秒内完成
        self.assertEqual(len(retrieved_cards), 100)
    
    def test_crud_transaction_rollback(self):
        """测试CRUD事务回滚"""
        # 创建一个canvas
        canvas = Canvas(owner_id=self.test_user_id, name="Transaction Test")
        self.db.add(canvas)
        self.db.commit()
        
        try:
            # 开始事务
            content = Content(content_type="text", text_data="Test content")
            self.db.add(content)
            self.db.flush()  # 获取content.id但不提交
            
            # 创建一个有效的card
            card = Card(
                canvas_id=canvas.id,
                content_id=content.id,
                position_x=10.0,
                position_y=20.0
            )
            self.db.add(card)
            
            # 创建一个无效的card（触发错误）
            invalid_card = Card(
                canvas_id=999999,  # 不存在的canvas_id
                content_id=content.id,
                position_x=30.0,
                position_y=40.0
            )
            self.db.add(invalid_card)
            self.db.commit()  # 这应该失败
            
        except IntegrityError:
            self.db.rollback()
            
            # 验证所有操作都被回滚
            content_count = self.db.query(Content).count()
            card_count = self.db.query(Card).count()
            
            # 应该只有原始数据，没有新创建的数据
            self.assertEqual(content_count, 0)
            self.assertEqual(card_count, 0)


if __name__ == "__main__":
    unittest.main()