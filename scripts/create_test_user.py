#!/usr/bin/env python3
"""
创建测试用户
"""

import sys
import os
import uuid
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.session import SessionLocal
from app.models.user import User


def create_test_user():
    """创建测试用户"""
    print("👤 创建测试用户...")
    
    db = SessionLocal()
    try:
        # 检查是否已有测试用户
        test_user_id = uuid.UUID("550e8400-e29b-41d4-a716-446655440000")
        existing_user = db.query(User).filter(User.id == test_user_id).first()
        
        if existing_user:
            print(f"✅ 测试用户已存在: {existing_user.name} ({existing_user.id})")
            return existing_user
        
        # 创建新的测试用户
        test_user = User(
            id=test_user_id,
            oauth_id="test_oauth_id",
            name="测试用户",
            email="test@example.com",
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        db.add(test_user)
        db.commit()
        db.refresh(test_user)
        
        print(f"✅ 测试用户创建成功: {test_user.name} ({test_user.id})")
        return test_user
        
    except Exception as e:
        print(f"❌ 创建测试用户失败: {e}")
        return None
    finally:
        db.close()


if __name__ == "__main__":
    create_test_user()
