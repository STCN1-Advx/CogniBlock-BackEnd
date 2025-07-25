#!/usr/bin/env python3
"""
简单的数据库重置脚本 - 删除旧表并重新创建
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.base import engine, Base
from app.models.user import User

def reset_database():
    """删除所有表并重新创建"""
    print("正在删除旧的数据库表...")
    Base.metadata.drop_all(bind=engine)
    print("旧表删除完成!")
    
    print("正在创建新的数据库表...")
    Base.metadata.create_all(bind=engine)
    print("新表创建完成!")
    print("🎉 数据库重置成功! 现在使用UUID作为用户ID!")

if __name__ == "__main__":
    reset_database()