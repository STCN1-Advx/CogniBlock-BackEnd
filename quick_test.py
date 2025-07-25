"""
快速测试脚本

简单验证画布API功能是否正常
"""

import os
import sys
from uuid import uuid4

# 设置环境变量
os.environ["TEST_DATABASE_URL"] = "postgresql://postgres:password@localhost:5432/cogniblock_test"

def test_imports():
    """测试导入是否正常"""
    print("📦 测试模块导入...")
    
    try:
        from app.models.canvas import Canvas
        from app.models.card import Card
        from app.models.content import Content
        from app.models.user import User
        from app.schemas.canva import CanvaPullRequest, CanvaPushRequest
        from app.api.v2.endpoints.canva import router
        print("✅ 所有模块导入成功")
        return True
    except Exception as e:
        print(f"❌ 导入失败: {e}")
        return False

def test_schemas():
    """测试数据模式"""
    print("📋 测试数据模式...")
    
    try:
        from app.schemas.canva import CanvaPullRequest, CanvaPushRequest, CardUpdateRequest, PositionModel
        
        # 测试Pull请求
        pull_request = CanvaPullRequest(canva_id=1)
        print(f"✅ Pull请求创建成功: {pull_request}")
        
        # 测试Push请求
        position = PositionModel(x=10.5, y=20.3)
        card_update = CardUpdateRequest(
            card_id=1,
            position=position,
            content_id=1
        )
        push_request = CanvaPushRequest(
            canva_id=1,
            cards=[card_update]
        )
        print(f"✅ Push请求创建成功: {push_request}")
        
        return True
    except Exception as e:
        print(f"❌ 数据模式测试失败: {e}")
        return False

def test_database_connection():
    """测试数据库连接"""
    print("🔗 测试数据库连接...")
    
    try:
        from sqlalchemy import create_engine
        from app.db.base import Base
        
        test_db_url = os.getenv("TEST_DATABASE_URL")
        engine = create_engine(test_db_url, echo=False)
        
        # 测试连接
        with engine.connect() as conn:
            result = conn.execute("SELECT 1")
            if result.fetchone():
                print("✅ 数据库连接成功")
                
        # 创建表
        Base.metadata.create_all(engine)
        print("✅ 数据库表创建成功")
        
        engine.dispose()
        return True
        
    except Exception as e:
        print(f"❌ 数据库连接失败: {e}")
        print("💡 请确保PostgreSQL正在运行且数据库存在")
        return False

def test_api_endpoints():
    """测试API端点"""
    print("🌐 测试API端点...")
    
    try:
        from app.api.v2.endpoints.canva import router
        from fastapi import FastAPI
        
        app = FastAPI()
        app.include_router(router, prefix="/canva")
        
        # 检查路由
        routes = [route.path for route in app.routes]
        expected_routes = ["/canva/pull", "/canva/push"]
        
        for route in expected_routes:
            if any(route in r for r in routes):
                print(f"✅ 路由 {route} 存在")
            else:
                print(f"❌ 路由 {route} 不存在")
                return False
                
        return True
        
    except Exception as e:
        print(f"❌ API端点测试失败: {e}")
        return False

def main():
    """主测试函数"""
    print("🧪 CogniBlock 快速功能测试")
    print("=" * 40)
    
    tests = [
        ("模块导入", test_imports),
        ("数据模式", test_schemas),
        ("数据库连接", test_database_connection),
        ("API端点", test_api_endpoints)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n🔍 {test_name}测试:")
        if test_func():
            passed += 1
        print("-" * 30)
    
    print(f"\n📊 测试结果: {passed}/{total} 通过")
    
    if passed == total:
        print("🎉 所有测试通过！画布API功能正常")
        return True
    else:
        print("⚠️  部分测试失败，请检查配置")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)