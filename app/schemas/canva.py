"""
画布相关的数据传输对象 (DTOs)
包含请求和响应模型，以及数据验证规则
"""
from typing import List, Optional
from pydantic import BaseModel, Field, validator
from uuid import UUID


class PositionModel(BaseModel):
    """位置模型"""
    x: float = Field(..., description="X坐标", ge=0.0)
    y: float = Field(..., description="Y坐标", ge=0.0)
    
    class Config:
        json_schema_extra = {
            "example": {
                "x": 12.12,
                "y": 86.21
            }
        }


class CanvaPullRequest(BaseModel):
    """拉取画布请求模型"""
    canva_id: int = Field(..., description="画布ID", gt=0)
    
    class Config:
        json_schema_extra = {
            "example": {
                "canva_id": 12
            }
        }


class CardUpdateRequest(BaseModel):
    """卡片更新请求模型"""
    card_id: int = Field(..., description="卡片ID", gt=0)
    position: PositionModel = Field(..., description="卡片位置")
    content_id: int = Field(..., description="内容ID", gt=0)
    
    @validator('position')
    def validate_position(cls, v):
        """验证位置数据"""
        if not isinstance(v, PositionModel):
            raise ValueError('位置必须是有效的PositionModel对象')
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "card_id": 101,
                "position": {
                    "x": 12.12,
                    "y": 86.21
                },
                "content_id": 104
            }
        }


class CardResponse(BaseModel):
    """卡片响应模型"""
    card_id: int = Field(..., description="卡片ID")
    position: PositionModel = Field(..., description="卡片位置")
    content_id: int = Field(..., description="内容ID")
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "card_id": 101,
                "position": {
                    "x": 12.12,
                    "y": 86.21
                },
                "content_id": 104
            }
        }


class CanvaPushRequest(BaseModel):
    """推送画布更新请求模型"""
    canva_id: int = Field(..., description="画布ID", gt=0)
    cards: List[CardUpdateRequest] = Field(..., description="卡片更新列表", min_items=1)
    
    @validator('cards')
    def validate_cards(cls, v):
        """验证卡片列表"""
        if not v:
            raise ValueError('卡片列表不能为空')
        
        # 检查是否有重复的card_id
        card_ids = [card.card_id for card in v]
        if len(card_ids) != len(set(card_ids)):
            raise ValueError('卡片ID不能重复')
        
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "canva_id": 12,
                "cards": [
                    {
                        "card_id": 101,
                        "position": {
                            "x": 12.12,
                            "y": 86.21
                        },
                        "content_id": 104
                    },
                    {
                        "card_id": 102,
                        "position": {
                            "x": 22.42,
                            "y": 81.15
                        },
                        "content_id": 101
                    }
                ]
            }
        }


class CanvaResponse(BaseModel):
    """画布响应模型"""
    canva_id: int = Field(..., description="画布ID")
    cards: List[CardResponse] = Field(..., description="卡片列表")
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "canva_id": 12,
                "cards": [
                    {
                        "card_id": 101,
                        "position": {
                            "x": 12.12,
                            "y": 86.21
                        },
                        "content_id": 104
                    },
                    {
                        "card_id": 102,
                        "position": {
                            "x": 22.42,
                            "y": 81.15
                        },
                        "content_id": 101
                    }
                ]
            }
        }


# 内容相关的DTOs
class ContentBase(BaseModel):
    """内容基础模型"""
    content_type: str = Field(..., description="内容类型", pattern="^(image|text)$")
    image_data: Optional[str] = Field(None, description="Base64编码的图片数据")
    text_data: Optional[str] = Field(None, description="文本数据")
    
    @validator('image_data')
    def validate_image_data(cls, v, values):
        """验证图片数据"""
        if values.get('content_type') == 'image' and not v:
            raise ValueError('图片类型内容必须提供image_data')
        return v
    
    @validator('text_data')
    def validate_text_data(cls, v, values):
        """验证文本数据"""
        if values.get('content_type') == 'text' and not v:
            raise ValueError('文本类型内容必须提供text_data')
        return v


class ContentCreate(ContentBase):
    """创建内容请求模型"""
    pass


class ContentUpdate(ContentBase):
    """更新内容请求模型"""
    content_type: Optional[str] = Field(None, description="内容类型", pattern="^(image|text)$")


class ContentResponse(ContentBase):
    """内容响应模型"""
    id: int = Field(..., description="内容ID")
    created_at: str = Field(..., description="创建时间")
    updated_at: str = Field(..., description="更新时间")
    
    class Config:
        from_attributes = True


# 画布相关的DTOs
class CanvasBase(BaseModel):
    """画布基础模型"""
    name: Optional[str] = Field(None, description="画布名称", max_length=255)


class CanvasCreate(CanvasBase):
    """创建画布请求模型"""
    pass


class CanvasUpdate(CanvasBase):
    """更新画布请求模型"""
    pass


class CanvasResponse(CanvasBase):
    """画布响应模型"""
    id: int = Field(..., description="画布ID")
    owner_id: UUID = Field(..., description="所有者ID")
    created_at: str = Field(..., description="创建时间")
    updated_at: str = Field(..., description="更新时间")
    
    class Config:
        from_attributes = True


# 错误响应模型
class ErrorResponse(BaseModel):
    """错误响应模型"""
    error: str = Field(..., description="错误代码")
    message: str = Field(..., description="错误消息")
    details: Optional[dict] = Field(None, description="错误详情")
    
    class Config:
        json_schema_extra = {
            "example": {
                "error": "CANVAS_NOT_FOUND",
                "message": "指定的画布不存在",
                "details": {"canvas_id": 12}
            }
        }