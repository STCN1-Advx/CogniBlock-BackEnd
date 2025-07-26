#!/usr/bin/env python3
"""
手动添加社群功能字段到contents表
"""

import sys
import os
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings


def add_community_fields():
    """添加社群功能字段到contents表"""
    print("🔧 添加社群功能字段到contents表...")
    
    try:
        # 解析数据库URL
        db_url = settings.DATABASE_URL
        
        # 连接数据库
        conn = psycopg2.connect(db_url)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        # 检查字段是否已存在
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'contents' 
            AND column_name IN ('is_public', 'public_title', 'public_description', 'published_at')
        """)
        existing_columns = [row[0] for row in cursor.fetchall()]
        
        # 需要添加的字段
        fields_to_add = [
            ("is_public", "ALTER TABLE contents ADD COLUMN is_public BOOLEAN DEFAULT FALSE NOT NULL"),
            ("public_title", "ALTER TABLE contents ADD COLUMN public_title VARCHAR(255)"),
            ("public_description", "ALTER TABLE contents ADD COLUMN public_description TEXT"),
            ("published_at", "ALTER TABLE contents ADD COLUMN published_at TIMESTAMP WITH TIME ZONE")
        ]
        
        added_count = 0
        for field_name, sql in fields_to_add:
            if field_name not in existing_columns:
                try:
                    cursor.execute(sql)
                    print(f"✅ 添加字段: {field_name}")
                    added_count += 1
                except Exception as e:
                    print(f"❌ 添加字段 {field_name} 失败: {e}")
            else:
                print(f"⏭️  字段已存在: {field_name}")
        
        cursor.close()
        conn.close()
        
        print(f"✅ 社群功能字段添加完成，新增 {added_count} 个字段")
        return True
        
    except Exception as e:
        print(f"❌ 添加字段失败: {e}")
        return False


if __name__ == "__main__":
    success = add_community_fields()
    sys.exit(0 if success else 1)
