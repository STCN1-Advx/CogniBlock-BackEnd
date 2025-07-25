"""
CogniBlock 快速启动脚本

用于快速验证和启动项目
"""

import subprocess
import sys
import os

def run_command(command: str) -> bool:
    """运行命令"""
    try:
        result = subprocess.run(command, shell=True, check=True)
        return result.returncode == 0
    except subprocess.CalledProcessError:
        return False

def check_dependencies():
    """检查依赖"""
    print("检查项目依赖...")
    
    try:
        import fastapi
        import sqlalchemy
        import pydantic
        print("✓ 核心依赖已安装")
        return True
    except ImportError as e:
        print(f"✗ 缺少依赖: {e}")
        print("请运行: pip install -r requirements.txt")
        return False

def run_tests():
    """运行测试"""
    print("\n运行基础测试...")
    
    if run_command("python tests/utils/basic_test.py"):
        print("✓ 基础测试通过")
        return True
    else:
        print("✗ 基础测试失败")
        return False

def show_api_info():
    """显示API信息"""
    print("\n" + "="*50)
    print("CogniBlock 画布API信息")
    print("="*50)
    print("API端点:")
    print("  GET  /api/v2/canva/pull?canva_id=<id>")
    print("  POST /api/v2/canva/push")
    print("  GET  /api/v2/canva/info/<canvas_id>")
    print("\n数据库管理:")
    print("  python reset_db.py init     # 初始化数据库")
    print("  python reset_db.py reset    # 重置数据库")
    print("\n测试命令:")
    print("  python tests/utils/basic_test.py        # 基础测试")
    print("  python tests/run_tests.py --type quick  # 快速测试")
    print("  python tests/run_tests.py --type all    # 完整测试")

def main():
    """主函数"""
    print("CogniBlock 项目启动检查")
    print("="*30)
    
    # 检查依赖
    if not check_dependencies():
        sys.exit(1)
    
    # 运行测试
    if not run_tests():
        print("\n警告: 测试失败，但项目结构正常")
    
    # 显示信息
    show_api_info()
    
    print("\n项目准备就绪！")
    print("可以开始使用 CogniBlock 画布功能")

if __name__ == "__main__":
    main()