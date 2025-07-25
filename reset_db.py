"""
数据库重置脚本

用于在非生产环境下快速重置数据库
包含创建、删除、重置功能
"""

import os
import sys
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from app.core.database import Base
from app.models import user, canvas, card, content  # 导入所有模型

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 数据库配置
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:password@localhost:5432/cogniblock")
TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL", "postgresql://postgres:password@localhost:5432/cogniblock_test")

def get_database_url(use_test_db: bool = False) -> str:
    """获取数据库URL"""
    return TEST_DATABASE_URL if use_test_db else DATABASE_URL

def create_database(db_name: str, use_test_db: bool = False):
    """创建数据库"""
    try:
        # 连接到postgres数据库来创建新数据库
        base_url = get_database_url(use_test_db).rsplit('/', 1)[0]
        postgres_url = f"{base_url}/postgres"
        
        engine = create_engine(postgres_url, isolation_level='AUTOCOMMIT')
        
        with engine.connect() as conn:
            # 检查数据库是否已存在
            result = conn.execute(text(f"SELECT 1 FROM pg_database WHERE datname = '{db_name}'"))
            if result.fetchone():
                logger.info(f"数据库 {db_name} 已存在")
                return True
            
            # 创建数据库
            conn.execute(text(f"CREATE DATABASE {db_name}"))
            logger.info(f"✅ 成功创建数据库: {db_name}")
            return True
            
    except SQLAlchemyError as e:
        logger.error(f"❌ 创建数据库失败: {e}")
        return False

def drop_database(db_name: str, use_test_db: bool = False):
    """删除数据库"""
    try:
        # 连接到postgres数据库来删除目标数据库
        base_url = get_database_url(use_test_db).rsplit('/', 1)[0]
        postgres_url = f"{base_url}/postgres"
        
        engine = create_engine(postgres_url, isolation_level='AUTOCOMMIT')
        
        with engine.connect() as conn:
            # 终止所有连接到目标数据库的会话
            conn.execute(text(f"""
                SELECT pg_terminate_backend(pid)
                FROM pg_stat_activity
                WHERE datname = '{db_name}' AND pid <> pg_backend_pid()
            """))
            
            # 删除数据库
            conn.execute(text(f"DROP DATABASE IF EXISTS {db_name}"))
            logger.info(f"✅ 成功删除数据库: {db_name}")
            return True
            
    except SQLAlchemyError as e:
        logger.error(f"❌ 删除数据库失败: {e}")
        return False

def create_tables(use_test_db: bool = False):
    """创建所有表"""
    try:
        db_url = get_database_url(use_test_db)
        engine = create_engine(db_url)
        
        # 创建所有表
        Base.metadata.create_all(bind=engine)
        logger.info("✅ 成功创建所有表")
        return True
        
    except SQLAlchemyError as e:
        logger.error(f"❌ 创建表失败: {e}")
        return False

def drop_tables(use_test_db: bool = False):
    """删除所有表"""
    try:
        db_url = get_database_url(use_test_db)
        engine = create_engine(db_url)
        
        # 删除所有表
        Base.metadata.drop_all(bind=engine)
        logger.info("✅ 成功删除所有表")
        return True
        
    except SQLAlchemyError as e:
        logger.error(f"❌ 删除表失败: {e}")
        return False

def reset_database(use_test_db: bool = False):
    """重置数据库（删除并重新创建所有表）"""
    logger.info("🔄 开始重置数据库...")
    
    # 删除所有表
    if not drop_tables(use_test_db):
        return False
    
    # 重新创建所有表
    if not create_tables(use_test_db):
        return False
    
    logger.info("🎉 数据库重置完成！")
    return True

def init_database(use_test_db: bool = False):
    """初始化数据库（创建数据库和表）"""
    db_name = "cogniblock_test" if use_test_db else "cogniblock"
    
    logger.info(f"🚀 开始初始化数据库: {db_name}")
    
    # 创建数据库
    if not create_database(db_name, use_test_db):
        return False
    
    # 创建表
    if not create_tables(use_test_db):
        return False
    
    logger.info(f"🎉 数据库初始化完成: {db_name}")
    return True

def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("""
🗄️  CogniBlock 数据库管理工具

用法:
    python reset_db.py <命令> [选项]

命令:
    init        - 初始化数据库（创建数据库和表）
    reset       - 重置数据库（删除并重新创建表）
    create      - 仅创建表
    drop        - 仅删除表
    create-db   - 仅创建数据库
    drop-db     - 仅删除数据库

选项:
    --test      - 使用测试数据库

示例:
    python reset_db.py init          # 初始化主数据库
    python reset_db.py init --test   # 初始化测试数据库
    python reset_db.py reset         # 重置主数据库
    python reset_db.py reset --test  # 重置测试数据库
        """)
        return
    
    command = sys.argv[1]
    use_test_db = "--test" in sys.argv
    
    db_type = "测试数据库" if use_test_db else "主数据库"
    logger.info(f"🎯 目标: {db_type}")
    
    success = False
    
    if command == "init":
        success = init_database(use_test_db)
    elif command == "reset":
        success = reset_database(use_test_db)
    elif command == "create":
        success = create_tables(use_test_db)
    elif command == "drop":
        success = drop_tables(use_test_db)
    elif command == "create-db":
        db_name = "cogniblock_test" if use_test_db else "cogniblock"
        success = create_database(db_name, use_test_db)
    elif command == "drop-db":
        db_name = "cogniblock_test" if use_test_db else "cogniblock"
        success = drop_database(db_name, use_test_db)
    else:
        logger.error(f"❌ 未知命令: {command}")
        return
    
    if success:
        logger.info("✅ 操作完成")
    else:
        logger.error("❌ 操作失败")
        sys.exit(1)

if __name__ == "__main__":
    main()