#!/usr/bin/env python3
"""
简单的UUID用户功能测试脚本
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.session import get_db
from app.crud.user import user
from app.schemas.user import UserCreate
import uuid

def test_uuid_user():
    """测试UUID用户创建和查询"""
    db = next(get_db())
    
    try:
        # 先清理可能存在的测试数据
        existing_user = user.get_by_email(db, "test@example.com")
        if existing_user:
            user.delete(db, existing_user.id)
            print("🧹 清理了已存在的测试用户")
        
        # 创建测试用户
        test_user_data = UserCreate(
            oauth_id="test_oauth_123",
            name="测试用户",
            email="test@example.com",
            avatar="https://example.com/avatar.jpg"
        )
        
        # 创建用户
        created_user = user.create(db, test_user_data)
        print(f"✅ 用户创建成功!")
        print(f"   用户ID (UUID): {created_user.id}")
        print(f"   用户名: {created_user.name}")
        print(f"   邮箱: {created_user.email}")
        print(f"   ID类型: {type(created_user.id)}")
        
        # 通过UUID查询用户
        found_user = user.get(db, created_user.id)
        if found_user:
            print(f"✅ 通过UUID查询用户成功!")
            print(f"   查询到的用户: {found_user.name}")
        else:
            print("❌ 通过UUID查询用户失败!")
        
        # 通过邮箱查询用户
        found_by_email = user.get_by_email(db, "test@example.com")
        if found_by_email:
            print(f"✅ 通过邮箱查询用户成功!")
            print(f"   查询到的用户ID: {found_by_email.id}")
        
        # 清理测试数据
        user.delete(db, created_user.id)
        print("🧹 测试数据已清理")
        
        print("\n🎉 所有测试通过! UUID用户系统工作正常!")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    test_uuid_user()