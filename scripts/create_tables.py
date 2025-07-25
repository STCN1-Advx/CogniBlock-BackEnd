#!/usr/bin/env python3
"""
简单的数据库表创建脚本 - 用于MVP快速开发
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.base import engine, Base
from app.models.user import User

def create_tables():
    """创建所有数据库表"""
    print("正在创建数据库表...")
    Base.metadata.create_all(bind=engine)
    print("数据库表创建完成！")

if __name__ == "__main__":
    create_tables()
