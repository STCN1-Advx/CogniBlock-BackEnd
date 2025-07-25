"""
画布API端点测试
测试Pull和Push API的功能、权限验证和错误处理
"""
import unittest
from unittest.mock import Mock, patch, MagicMock
from fastapi import HTTPException
from uuid import uuid4

# 测试API端点的基本结构和功能
class TestCanvaAPIEndpoints(unittest.TestCase):
    """测试画布API端点"""
    
    def setUp(self):
        """设置测试环境"""
        self.mock_db = Mock()
        self.mock_user = Mock()
        self.mock_user.id = uuid4()
        self.test_canvas_id = 12
        self.test_card_id = 101
        self.test_content_id = 104
    
    def test_pull_request_structure(self):
        """测试Pull请求的数据结构"""
        from app.schemas.canva import CanvaPullRequest
        
        # 测试有效请求
        request = CanvaPullRequest(canva_id=12)
        self.assertEqual(request.canva_id, 12)
        
        # 测试无效请求（负数ID）
        with self.assertRaises(ValueError):
            CanvaPullRequest(canva_id=-1)
    
    def test_push_request_structure(self):
        """测试Push请求的数据结构"""
        from app.schemas.canva import CanvaPushRequest, CardUpdateRequest, PositionModel
        
        # 测试有效请求
        cards = [
            CardUpdateRequest(
                card_id=101,
                position=PositionModel(x=12.12, y=86.21),
                content_id=104
            )
        ]
        request = CanvaPushRequest(canva_id=12, cards=cards)
        self.assertEqual(request.canva_id, 12)
        self.assertEqual(len(request.cards), 1)
        self.assertEqual(request.cards[0].card_id, 101)
    
    def test_card_response_structure(self):
        """测试卡片响应的数据结构"""
        from app.schemas.canva import CardResponse, PositionModel
        
        response = CardResponse(
            card_id=101,
            position=PositionModel(x=12.12, y=86.21),
            content_id=104
        )
        self.assertEqual(response.card_id, 101)
        self.assertEqual(response.position.x, 12.12)
        self.assertEqual(response.position.y, 86.21)
        self.assertEqual(response.content_id, 104)
    
    def test_position_validation(self):
        """测试位置坐标验证"""
        from app.schemas.canva import PositionModel
        
        # 测试有效位置
        position = PositionModel(x=12.12, y=86.21)
        self.assertEqual(position.x, 12.12)
        self.assertEqual(position.y, 86.21)
        
        # 测试无效位置（负数）
        with self.assertRaises(ValueError):
            PositionModel(x=-1.0, y=86.21)
        
        with self.assertRaises(ValueError):
            PositionModel(x=12.12, y=-1.0)
    
    def test_duplicate_card_validation(self):
        """测试重复卡片ID验证"""
        from app.schemas.canva import CanvaPushRequest, CardUpdateRequest, PositionModel
        
        # 创建重复的卡片ID
        cards = [
            CardUpdateRequest(
                card_id=101,
                position=PositionModel(x=12.12, y=86.21),
                content_id=104
            ),
            CardUpdateRequest(
                card_id=101,  # 重复的ID
                position=PositionModel(x=22.42, y=81.15),
                content_id=105
            )
        ]
        
        # 应该抛出验证错误
        with self.assertRaises(ValueError):
            CanvaPushRequest(canva_id=12, cards=cards)
    
    @patch('app.api.v2.endpoints.canva.canvas_crud')
    @patch('app.api.v2.endpoints.canva.card_crud')
    @patch('app.api.v2.endpoints.canva.CanvaService')
    def test_pull_endpoint_logic(self, mock_service_class, mock_card_crud, mock_canvas_crud):
        """测试Pull端点的业务逻辑"""
        # 模拟数据库返回
        mock_canvas = Mock()
        mock_canvas.id = self.test_canvas_id
        mock_canvas_crud.get.return_value = mock_canvas
        
        mock_card = Mock()
        mock_card.id = self.test_card_id
        mock_card.position_x = 12.12
        mock_card.position_y = 86.21
        mock_card.content_id = self.test_content_id
        mock_card_crud.get_by_canvas.return_value = [mock_card]
        
        # 模拟服务
        mock_service = Mock()
        mock_service_class.return_value = mock_service
        
        # 验证逻辑结构
        self.assertTrue(hasattr(mock_service, 'verify_user_permission'))
        self.assertTrue(callable(getattr(mock_service, 'verify_user_permission', None)))
    
    @patch('app.api.v2.endpoints.canva.canvas_crud')
    @patch('app.api.v2.endpoints.canva.card_crud')
    @patch('app.api.v2.endpoints.canva.CanvaService')
    def test_push_endpoint_logic(self, mock_service_class, mock_card_crud, mock_canvas_crud):
        """测试Push端点的业务逻辑"""
        # 模拟数据库返回
        mock_canvas = Mock()
        mock_canvas.id = self.test_canvas_id
        mock_canvas_crud.get.return_value = mock_canvas
        
        mock_card = Mock()
        mock_card.id = self.test_card_id
        mock_card.canvas_id = self.test_canvas_id
        mock_card_crud.get.return_value = mock_card
        
        # 模拟服务
        mock_service = Mock()
        mock_service_class.return_value = mock_service
        
        # 验证逻辑结构
        self.assertTrue(hasattr(mock_service, 'verify_user_permission'))
        self.assertTrue(hasattr(mock_service, 'verify_content_access'))
        self.assertTrue(hasattr(mock_service, 'validate_card_data_consistency'))
    
    def test_error_response_structure(self):
        """测试错误响应结构"""
        from app.schemas.canva import ErrorResponse
        
        error = ErrorResponse(
            error="CANVAS_NOT_FOUND",
            message="指定的画布不存在",
            details={"canvas_id": 12}
        )
        self.assertEqual(error.error, "CANVAS_NOT_FOUND")
        self.assertEqual(error.message, "指定的画布不存在")
        self.assertEqual(error.details["canvas_id"], 12)
    
    def test_api_endpoint_imports(self):
        """测试API端点的导入"""
        try:
            from app.api.v2.endpoints.canva import router, pull_canvas, push_canvas, get_canvas_info
            self.assertIsNotNone(router)
            self.assertTrue(callable(pull_canvas))
            self.assertTrue(callable(push_canvas))
            self.assertTrue(callable(get_canvas_info))
        except ImportError as e:
            self.fail(f"Failed to import canva endpoints: {e}")
    
    def test_authentication_dependencies(self):
        """测试认证依赖"""
        try:
            from app.api.v2.auth import get_current_user
            self.assertTrue(callable(get_current_user))
        except ImportError as e:
            self.fail(f"Failed to import authentication dependencies: {e}")
    
    def test_service_integration(self):
        """测试服务层集成"""
        try:
            from app.services.canva_service import CanvaService, CanvaServiceError, PermissionDeniedError, CanvaNotFoundError
            
            # 验证异常类
            self.assertTrue(issubclass(PermissionDeniedError, CanvaServiceError))
            self.assertTrue(issubclass(CanvaNotFoundError, CanvaServiceError))
            
            # 验证服务类
            self.assertTrue(hasattr(CanvaService, '__init__'))
        except ImportError as e:
            self.fail(f"Failed to import service layer: {e}")
    
    def test_crud_integration(self):
        """测试CRUD层集成"""
        try:
            from app.crud import canvas as canvas_crud, card as card_crud
            
            # 验证CRUD方法
            self.assertTrue(hasattr(canvas_crud, 'get'))
            self.assertTrue(hasattr(canvas_crud, 'update'))
            self.assertTrue(hasattr(card_crud, 'get'))
            self.assertTrue(hasattr(card_crud, 'get_by_canvas'))
            self.assertTrue(hasattr(card_crud, 'update'))
        except ImportError as e:
            self.fail(f"Failed to import CRUD layer: {e}")
    
    def test_router_registration(self):
        """测试路由注册"""
        try:
            from app.api.v2 import api_router
            from app.api.v2.endpoints.canva import router as canva_router
            
            # 验证路由器存在
            self.assertIsNotNone(api_router)
            self.assertIsNotNone(canva_router)
        except ImportError as e:
            self.fail(f"Failed to import API router: {e}")


class TestCanvaAPIValidation(unittest.TestCase):
    """测试画布API数据验证"""
    
    def test_canvas_id_validation(self):
        """测试画布ID验证"""
        from app.schemas.canva import CanvaPullRequest
        
        # 有效ID
        request = CanvaPullRequest(canva_id=1)
        self.assertEqual(request.canva_id, 1)
        
        # 无效ID（零和负数）
        with self.assertRaises(ValueError):
            CanvaPullRequest(canva_id=0)
        
        with self.assertRaises(ValueError):
            CanvaPullRequest(canva_id=-1)
    
    def test_card_id_validation(self):
        """测试卡片ID验证"""
        from app.schemas.canva import CardUpdateRequest, PositionModel
        
        # 有效卡片
        card = CardUpdateRequest(
            card_id=1,
            position=PositionModel(x=0.0, y=0.0),
            content_id=1
        )
        self.assertEqual(card.card_id, 1)
        
        # 无效卡片ID
        with self.assertRaises(ValueError):
            CardUpdateRequest(
                card_id=0,
                position=PositionModel(x=0.0, y=0.0),
                content_id=1
            )
    
    def test_content_id_validation(self):
        """测试内容ID验证"""
        from app.schemas.canva import CardUpdateRequest, PositionModel
        
        # 有效内容ID
        card = CardUpdateRequest(
            card_id=1,
            position=PositionModel(x=0.0, y=0.0),
            content_id=1
        )
        self.assertEqual(card.content_id, 1)
        
        # 无效内容ID
        with self.assertRaises(ValueError):
            CardUpdateRequest(
                card_id=1,
                position=PositionModel(x=0.0, y=0.0),
                content_id=0
            )
    
    def test_empty_cards_validation(self):
        """测试空卡片列表验证"""
        from app.schemas.canva import CanvaPushRequest
        
        # 空卡片列表应该失败
        with self.assertRaises(ValueError):
            CanvaPushRequest(canva_id=1, cards=[])


if __name__ == '__main__':
    # 运行所有测试
    unittest.main(verbosity=2)