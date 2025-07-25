# pytest配置文件
import pytest
import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 测试数据库配置
TEST_DATABASE_URL = "postgresql://postgres:password@localhost:5432/cogniblock_test"

@pytest.fixture(scope="session")
def test_db():
    """测试数据库会话级别的fixture"""
    # 这里可以添加测试数据库的设置和清理逻辑
    yield TEST_DATABASE_URL

@pytest.fixture(scope="function")
def clean_db():
    """每个测试函数级别的数据库清理fixture"""
    # 这里可以添加每个测试前后的数据库清理逻辑
    yield
    # 清理逻辑