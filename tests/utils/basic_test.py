"""
CogniBlock 基础测试
简化版本，避免Unicode字符问题
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

def test_imports():
    """测试模块导入"""
    print("测试模块导入...")
    
    try:
        from app.models.canvas import Canvas
        from app.models.card import Card
        from app.models.content import Content
        from app.models.user import User
        from app.schemas.canva import CanvaPullRequest, CanvaPushRequest
        from app.services.canva_service import CanvaService
        from app.crud.canvas import canvas
        from app.api.v2.endpoints.canva import router
        
        print("所有模块导入成功")
        return True
        
    except Exception as e:
        print(f"模块导入失败: {e}")
        return False

def test_schemas():
    """测试数据模式"""
    print("测试数据模式...")
    
    try:
        from app.schemas.canva import PositionModel, CardUpdateRequest
        
        # 测试Position模型
        position = PositionModel(x=10.5, y=20.3)
        assert position.x == 10.5
        assert position.y == 20.3
        
        # 测试Card更新请求
        card_update = CardUpdateRequest(
            card_id=1,
            position=position,
            content_id=1
        )
        assert card_update.card_id == 1
        
        print("数据模式验证通过")
        return True
        
    except Exception as e:
        print(f"数据模式测试失败: {e}")
        return False

def test_validation():
    """测试数据验证"""
    print("测试数据验证...")
    
    try:
        from app.schemas.canva import PositionModel
        from pydantic import ValidationError
        
        # 测试有效数据
        valid_position = PositionModel(x=10.5, y=20.3)
        assert valid_position.x >= 0
        
        # 测试无效数据
        try:
            invalid_position = PositionModel(x=-10.0, y=20.0)
            print("应该拒绝负数位置")
            return False
        except ValidationError:
            print("正确拒绝了负数位置")
        
        print("数据验证正确")
        return True
        
    except Exception as e:
        print(f"数据验证测试失败: {e}")
        return False

def main():
    """主测试函数"""
    print("CogniBlock 简单测试")
    print("=" * 30)
    
    tests = [
        ("模块导入", test_imports),
        ("数据模式", test_schemas),
        ("数据验证", test_validation)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n{test_name}测试:")
        try:
            if test_func():
                passed += 1
                print(f"{test_name}测试通过")
        except Exception as e:
            print(f"{test_name}测试出错: {e}")
        print("-" * 20)
    
    print(f"\n测试结果: {passed}/{total} 通过")
    
    if passed == total:
        print("所有测试通过！")
        return True
    else:
        print("部分测试失败")
        return False

if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)