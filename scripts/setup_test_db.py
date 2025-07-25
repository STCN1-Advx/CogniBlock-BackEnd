"""
测试数据库设置脚本

用于创建和配置PostgreSQL测试数据库
"""

import os
import sys
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.base import Base


def create_test_database():
    """创建测试数据库"""
    # 默认连接参数
    default_params = {
        'host': 'localhost',
        'port': 5432,
        'user': 'postgres',
        'password': 'password'
    }
    
    test_db_name = 'cogniblock_test'
    
    try:
        # 连接到PostgreSQL服务器（不指定数据库）
        conn = psycopg2.connect(
            host=default_params['host'],
            port=default_params['port'],
            user=default_params['user'],
            password=default_params['password'],
            database='postgres'  # 连接到默认数据库
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        # 检查测试数据库是否存在
        cursor.execute(
            "SELECT 1 FROM pg_catalog.pg_database WHERE datname = %s",
            (test_db_name,)
        )
        exists = cursor.fetchone()
        
        if not exists:
            # 创建测试数据库
            cursor.execute(f'CREATE DATABASE "{test_db_name}"')
            print(f"✅ 测试数据库 '{test_db_name}' 创建成功")
        else:
            print(f"ℹ️  测试数据库 '{test_db_name}' 已存在")
        
        cursor.close()
        conn.close()
        
        # 测试连接到新创建的数据库
        test_db_url = f"postgresql://{default_params['user']}:{default_params['password']}@{default_params['host']}:{default_params['port']}/{test_db_name}"
        
        engine = create_engine(test_db_url)
        
        # 创建所有表
        Base.metadata.create_all(engine)
        print("✅ 数据库表结构创建成功")
        
        # 测试连接
        with engine.connect() as connection:
            result = connection.execute("SELECT 1")
            if result.fetchone():
                print("✅ 数据库连接测试成功")
        
        engine.dispose()
        
        print(f"\n🎉 测试数据库设置完成!")
        print(f"数据库URL: {test_db_url}")
        print(f"环境变量: TEST_DATABASE_URL={test_db_url}")
        
        return test_db_url
        
    except psycopg2.Error as e:
        print(f"❌ PostgreSQL错误: {e}")
        print("\n💡 请确保:")
        print("1. PostgreSQL服务正在运行")
        print("2. 用户名和密码正确")
        print("3. 有创建数据库的权限")
        return None
        
    except OperationalError as e:
        print(f"❌ 数据库连接错误: {e}")
        return None
        
    except Exception as e:
        print(f"❌ 未知错误: {e}")
        return None


def drop_test_database():
    """删除测试数据库"""
    default_params = {
        'host': 'localhost',
        'port': 5432,
        'user': 'postgres',
        'password': 'password'
    }
    
    test_db_name = 'cogniblock_test'
    
    try:
        conn = psycopg2.connect(
            host=default_params['host'],
            port=default_params['port'],
            user=default_params['user'],
            password=default_params['password'],
            database='postgres'
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        # 终止所有连接到测试数据库的会话
        cursor.execute(f"""
            SELECT pg_terminate_backend(pid)
            FROM pg_stat_activity
            WHERE datname = '{test_db_name}' AND pid <> pg_backend_pid()
        """)
        
        # 删除测试数据库
        cursor.execute(f'DROP DATABASE IF EXISTS "{test_db_name}"')
        print(f"✅ 测试数据库 '{test_db_name}' 删除成功")
        
        cursor.close()
        conn.close()
        
    except psycopg2.Error as e:
        print(f"❌ 删除数据库时出错: {e}")


def reset_test_database():
    """重置测试数据库"""
    print("🔄 重置测试数据库...")
    drop_test_database()
    return create_test_database()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="测试数据库管理工具")
    parser.add_argument("action", choices=["create", "drop", "reset"], 
                       help="操作类型: create(创建), drop(删除), reset(重置)")
    
    args = parser.parse_args()
    
    if args.action == "create":
        create_test_database()
    elif args.action == "drop":
        drop_test_database()
    elif args.action == "reset":
        reset_test_database()