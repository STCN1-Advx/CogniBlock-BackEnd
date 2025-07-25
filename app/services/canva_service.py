"""
画布业务服务层
处理画布相关的业务逻辑，包括权限验证、数据一致性检查等
"""

import logging
from typing import List, Optional, Dict, Any
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.crud import canvas, card, content
from app.schemas.canva import (
    CanvaPullRequest, CanvaPushRequest, CardUpdateRequest, 
    CanvaResponse, CardResponse, PositionModel, ErrorResponse
)
from app.models.canvas import Canvas
from app.models.card import Card
from app.models.content import Content

logger = logging.getLogger(__name__)


class CanvaServiceError(Exception):
    """画布服务异常基类"""
    def __init__(self, message: str, error_code: str = "CANVA_ERROR"):
        self.message = message
        self.error_code = error_code
        super().__init__(self.message)


class PermissionDeniedError(CanvaServiceError):
    """权限拒绝异常"""
    def __init__(self, message: str = "权限不足"):
        super().__init__(message, "PERMISSION_DENIED")


class CanvaNotFoundError(CanvaServiceError):
    """画布未找到异常"""
    def __init__(self, message: str = "画布不存在"):
        super().__init__(message, "CANVA_NOT_FOUND")


class DataConsistencyError(CanvaServiceError):
    """数据一致性异常"""
    def __init__(self, message: str = "数据一致性错误"):
        super().__init__(message, "DATA_CONSISTENCY_ERROR")


class CanvaService:
    """画布业务服务类"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def verify_user_permission(self, db: Session, canva_id: int, user_id: UUID) -> Canvas:
        """
        验证用户对画布的访问权限
        
        Args:
            db: 数据库会话
            canva_id: 画布ID
            user_id: 用户ID
            
        Returns:
            Canvas: 画布对象
            
        Raises:
            CanvaNotFoundError: 画布不存在
            PermissionDeniedError: 权限不足
        """
        # 检查画布是否存在
        canva = canvas.get(db, canva_id)
        if not canva:
            self.logger.warning(f"画布不存在: canva_id={canva_id}")
            raise CanvaNotFoundError(f"画布 {canva_id} 不存在")
        
        # 检查用户权限
        if not canvas.check_ownership(db, canva_id, user_id):
            self.logger.warning(f"用户权限不足: user_id={user_id}, canva_id={canva_id}")
            raise PermissionDeniedError(f"用户无权访问画布 {canva_id}")
        
        return canva
    
    def verify_content_access(self, db: Session, content_id: int, user_id: UUID) -> Content:
        """
        验证用户对内容的访问权限
        
        Args:
            db: 数据库会话
            content_id: 内容ID
            user_id: 用户ID
            
        Returns:
            Content: 内容对象
            
        Raises:
            CanvaServiceError: 内容不存在或权限不足
        """
        # 检查内容是否存在
        content_obj = content.get(db, content_id)
        if not content_obj:
            raise CanvaServiceError(f"内容 {content_id} 不存在", "CONTENT_NOT_FOUND")
        
        # 检查用户权限
        if not content.check_user_access(db, content_id, user_id):
            raise PermissionDeniedError(f"用户无权访问内容 {content_id}")
        
        return content_obj
    
    def validate_card_data_consistency(self, db: Session, cards_data: List[CardUpdateRequest], user_id: UUID) -> None:
        """
        验证卡片数据的一致性
        
        Args:
            db: 数据库会话
            cards_data: 卡片更新数据列表
            user_id: 用户ID
            
        Raises:
            DataConsistencyError: 数据一致性错误
        """
        # 检查卡片ID是否重复
        card_ids = [card_data.card_id for card_data in cards_data]
        if len(card_ids) != len(set(card_ids)):
            raise DataConsistencyError("卡片ID不能重复")
        
        # 验证每个卡片的内容访问权限
        for card_data in cards_data:
            try:
                self.verify_content_access(db, card_data.content_id, user_id)
            except CanvaServiceError as e:
                raise DataConsistencyError(f"卡片 {card_data.card_id} 的内容验证失败: {e.message}")
        
        # 验证位置数据
        for card_data in cards_data:
            if card_data.position.x < 0 or card_data.position.y < 0:
                raise DataConsistencyError(f"卡片 {card_data.card_id} 的位置坐标不能为负数")
    
    def pull_canva(self, db: Session, request: CanvaPullRequest, user_id: UUID) -> CanvaResponse:
        """
        拉取画布当前状态
        
        Args:
            db: 数据库会话
            request: 拉取请求
            user_id: 用户ID
            
        Returns:
            CanvaResponse: 画布响应数据
            
        Raises:
            CanvaNotFoundError: 画布不存在
            PermissionDeniedError: 权限不足
        """
        try:
            # 验证用户权限
            canva_obj = self.verify_user_permission(db, request.canva_id, user_id)
            
            # 获取画布中的所有卡片
            cards_list = card.get_by_canvas(db, request.canva_id)
            
            # 构建响应数据
            card_responses = []
            for card_obj in cards_list:
                # 验证内容访问权限
                try:
                    self.verify_content_access(db, card_obj.content_id, user_id)
                    
                    card_response = CardResponse(
                        card_id=card_obj.id,
                        position=PositionModel(x=card_obj.position_x, y=card_obj.position_y),
                        content_id=card_obj.content_id
                    )
                    card_responses.append(card_response)
                except CanvaServiceError as e:
                    # 记录权限问题但不中断整个操作
                    self.logger.warning(f"跳过无权限访问的卡片: card_id={card_obj.id}, {e.message}")
                    continue
            
            response = CanvaResponse(
                canva_id=request.canva_id,
                cards=card_responses
            )
            
            self.logger.info(f"成功拉取画布: canva_id={request.canva_id}, cards_count={len(card_responses)}")
            return response
            
        except CanvaServiceError:
            raise
        except Exception as e:
            self.logger.error(f"拉取画布失败: {str(e)}")
            raise CanvaServiceError(f"拉取画布失败: {str(e)}")
    
    def push_canva(self, db: Session, request: CanvaPushRequest, user_id: UUID) -> Dict[str, Any]:
        """
        推送画布更新
        
        Args:
            db: 数据库会话
            request: 推送请求
            user_id: 用户ID
            
        Returns:
            Dict[str, Any]: 操作结果
            
        Raises:
            CanvaNotFoundError: 画布不存在
            PermissionDeniedError: 权限不足
            DataConsistencyError: 数据一致性错误
        """
        try:
            # 验证用户权限
            canva_obj = self.verify_user_permission(db, request.canva_id, user_id)
            
            # 验证数据一致性
            self.validate_card_data_consistency(db, request.cards, user_id)
            
            # 开始事务处理
            updated_cards = []
            failed_cards = []
            
            for card_data in request.cards:
                try:
                    # 检查卡片是否存在于该画布中
                    card_obj = card.get_by_canvas_and_id(db, request.canva_id, card_data.card_id)
                    
                    if card_obj:
                        # 更新现有卡片
                        updated_card = card.update(db, card_obj, card_data)
                        updated_cards.append(updated_card.id)
                    else:
                        # 创建新卡片
                        new_card = card.create(
                            db=db,
                            canvas_id=request.canva_id,
                            content_id=card_data.content_id,
                            position_x=card_data.position.x,
                            position_y=card_data.position.y
                        )
                        updated_cards.append(new_card.id)
                        
                except Exception as e:
                    self.logger.error(f"更新卡片失败: card_id={card_data.card_id}, error={str(e)}")
                    failed_cards.append({
                        "card_id": card_data.card_id,
                        "error": str(e)
                    })
            
            # 检查是否有失败的操作
            if failed_cards:
                raise DataConsistencyError(f"部分卡片更新失败: {failed_cards}")
            
            result = {
                "success": True,
                "message": "画布更新成功",
                "canva_id": request.canva_id,
                "updated_cards_count": len(updated_cards),
                "updated_card_ids": updated_cards
            }
            
            self.logger.info(f"成功推送画布更新: canva_id={request.canva_id}, updated_cards={len(updated_cards)}")
            return result
            
        except CanvaServiceError:
            raise
        except SQLAlchemyError as e:
            db.rollback()
            self.logger.error(f"数据库操作失败: {str(e)}")
            raise DataConsistencyError(f"数据库操作失败: {str(e)}")
        except Exception as e:
            db.rollback()
            self.logger.error(f"推送画布更新失败: {str(e)}")
            raise CanvaServiceError(f"推送画布更新失败: {str(e)}")
    
    def get_canva_info(self, db: Session, canva_id: int, user_id: UUID) -> Dict[str, Any]:
        """
        获取画布基本信息
        
        Args:
            db: 数据库会话
            canva_id: 画布ID
            user_id: 用户ID
            
        Returns:
            Dict[str, Any]: 画布信息
        """
        try:
            # 验证用户权限
            canva_obj = self.verify_user_permission(db, canva_id, user_id)
            
            # 获取卡片数量
            cards_count = canvas.get_cards_count(db, canva_id)
            
            return {
                "canva_id": canva_obj.id,
                "name": canva_obj.name,
                "owner_id": str(canva_obj.owner_id),
                "cards_count": cards_count,
                "created_at": canva_obj.created_at.isoformat(),
                "updated_at": canva_obj.updated_at.isoformat()
            }
            
        except CanvaServiceError:
            raise
        except Exception as e:
            self.logger.error(f"获取画布信息失败: {str(e)}")
            raise CanvaServiceError(f"获取画布信息失败: {str(e)}")
    
    def validate_canva_state(self, db: Session, canva_id: int, user_id: UUID) -> Dict[str, Any]:
        """
        验证画布状态的一致性
        
        Args:
            db: 数据库会话
            canva_id: 画布ID
            user_id: 用户ID
            
        Returns:
            Dict[str, Any]: 验证结果
        """
        try:
            # 验证用户权限
            self.verify_user_permission(db, canva_id, user_id)
            
            # 获取所有卡片
            cards_list = card.get_by_canvas(db, canva_id)
            
            validation_result = {
                "canva_id": canva_id,
                "total_cards": len(cards_list),
                "valid_cards": 0,
                "invalid_cards": 0,
                "issues": []
            }
            
            for card_obj in cards_list:
                # 检查内容是否存在
                content_obj = content.get(db, card_obj.content_id)
                if not content_obj:
                    validation_result["invalid_cards"] += 1
                    validation_result["issues"].append({
                        "card_id": card_obj.id,
                        "issue": f"关联的内容 {card_obj.content_id} 不存在"
                    })
                    continue
                
                # 检查用户是否有权限访问内容
                if not content.check_user_access(db, card_obj.content_id, user_id):
                    validation_result["invalid_cards"] += 1
                    validation_result["issues"].append({
                        "card_id": card_obj.id,
                        "issue": f"用户无权访问内容 {card_obj.content_id}"
                    })
                    continue
                
                validation_result["valid_cards"] += 1
            
            validation_result["is_consistent"] = validation_result["invalid_cards"] == 0
            
            return validation_result
            
        except CanvaServiceError:
            raise
        except Exception as e:
            self.logger.error(f"验证画布状态失败: {str(e)}")
            raise CanvaServiceError(f"验证画布状态失败: {str(e)}")


# 创建服务实例
canva_service = CanvaService()