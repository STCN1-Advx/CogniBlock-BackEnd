"""
测试画布DTOs的数据验证功能
"""
from pydantic import ValidationError
from app.schemas.canva import (
    PositionModel,
    CanvaPullRequest,
    CardUpdateRequest,
    CanvaPushRequest,
    ContentCreate,
    ErrorResponse
)


def test_position_model_valid():
    """测试有效的位置模型"""
    position = PositionModel(x=12.12, y=86.21)
    assert position.x == 12.12
    assert position.y == 86.21


def test_position_model_invalid_negative():
    """测试负数位置（应该失败）"""
    try:
        PositionModel(x=-1.0, y=86.21)
        assert False, "应该抛出ValidationError"
    except ValidationError:
        pass  # 预期的异常


def test_canva_pull_request_valid():
    """测试有效的拉取请求"""
    request = CanvaPullRequest(canva_id=12)
    assert request.canva_id == 12


def test_canva_pull_request_invalid_zero():
    """测试无效的画布ID（应该失败）"""
    try:
        CanvaPullRequest(canva_id=0)
        assert False, "应该抛出ValidationError"
    except ValidationError:
        pass  # 预期的异常


def test_card_update_request_valid():
    """测试有效的卡片更新请求"""
    request = CardUpdateRequest(
        card_id=101,
        position=PositionModel(x=12.12, y=86.21),
        content_id=104
    )
    assert request.card_id == 101
    assert request.position.x == 12.12
    assert request.content_id == 104


def test_canva_push_request_valid():
    """测试有效的推送请求"""
    request = CanvaPushRequest(
        canva_id=12,
        cards=[
            CardUpdateRequest(
                card_id=101,
                position=PositionModel(x=12.12, y=86.21),
                content_id=104
            ),
            CardUpdateRequest(
                card_id=102,
                position=PositionModel(x=22.42, y=81.15),
                content_id=101
            )
        ]
    )
    assert request.canva_id == 12
    assert len(request.cards) == 2


def test_canva_push_request_duplicate_card_ids():
    """测试重复卡片ID（应该失败）"""
    try:
        CanvaPushRequest(
            canva_id=12,
            cards=[
                CardUpdateRequest(
                    card_id=101,
                    position=PositionModel(x=12.12, y=86.21),
                    content_id=104
                ),
                CardUpdateRequest(
                    card_id=101,  # 重复的card_id
                    position=PositionModel(x=22.42, y=81.15),
                    content_id=101
                )
            ]
        )
        assert False, "应该抛出ValidationError"
    except ValidationError:
        pass  # 预期的异常


def test_canva_push_request_empty_cards():
    """测试空卡片列表（应该失败）"""
    try:
        CanvaPushRequest(canva_id=12, cards=[])
        assert False, "应该抛出ValidationError"
    except ValidationError:
        pass  # 预期的异常


def test_content_create_image_valid():
    """测试有效的图片内容创建"""
    content = ContentCreate(
        content_type="image",
        image_data="base64encodeddata",
        text_data=None
    )
    assert content.content_type == "image"
    assert content.image_data == "base64encodeddata"


def test_content_create_text_valid():
    """测试有效的文本内容创建"""
    content = ContentCreate(
        content_type="text",
        image_data=None,
        text_data="这是一些文本内容"
    )
    assert content.content_type == "text"
    assert content.text_data == "这是一些文本内容"


def test_content_create_image_missing_data():
    """测试图片类型缺少图片数据（应该失败）"""
    try:
        ContentCreate(
            content_type="image",
            image_data=None,
            text_data=None
        )
        assert False, "应该抛出ValidationError"
    except ValidationError:
        pass  # 预期的异常


def test_content_create_text_missing_data():
    """测试文本类型缺少文本数据（应该失败）"""
    try:
        ContentCreate(
            content_type="text",
            image_data=None,
            text_data=None
        )
        assert False, "应该抛出ValidationError"
    except ValidationError:
        pass  # 预期的异常


def test_content_create_invalid_type():
    """测试无效的内容类型（应该失败）"""
    try:
        ContentCreate(
            content_type="video",  # 无效类型
            image_data=None,
            text_data="一些文本"
        )
        assert False, "应该抛出ValidationError"
    except ValidationError:
        pass  # 预期的异常


def test_error_response():
    """测试错误响应模型"""
    error = ErrorResponse(
        error="CANVAS_NOT_FOUND",
        message="指定的画布不存在",
        details={"canvas_id": 12}
    )
    assert error.error == "CANVAS_NOT_FOUND"
    assert error.message == "指定的画布不存在"
    assert error.details["canvas_id"] == 12


if __name__ == "__main__":
    # 运行一些基本测试
    print("运行DTOs验证测试...")
    
    try:
        test_position_model_valid()
        print("✓ 位置模型测试通过")
        
        test_canva_pull_request_valid()
        print("✓ 拉取请求测试通过")
        
        test_card_update_request_valid()
        print("✓ 卡片更新请求测试通过")
        
        test_canva_push_request_valid()
        print("✓ 推送请求测试通过")
        
        test_content_create_image_valid()
        print("✓ 图片内容创建测试通过")
        
        test_content_create_text_valid()
        print("✓ 文本内容创建测试通过")
        
        test_error_response()
        print("✓ 错误响应测试通过")
        
        print("\n所有基本测试都通过了！")
        
    except Exception as e:
        print(f"✗ 测试失败: {e}")