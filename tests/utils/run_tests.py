"""
简单的测试运行脚本

使用PostgreSQL测试数据库运行所有单元测试
"""

import os
import sys
import subprocess
from pathlib import Path

def setup_test_environment():
    """设置测试环境变量"""
    # 设置测试数据库URL
    os.environ["TEST_DATABASE_URL"] = "postgresql://postgres:password@localhost:5432/cogniblock_test"
    
    # 设置其他测试环境变量
    os.environ["TESTING"] = "true"
    os.environ["LOG_LEVEL"] = "WARNING"
    
    print("✅ 测试环境变量设置完成")

def run_tests():
    """运行所有单元测试"""
    test_files = [
        "test_models_unit.py",
        "test_crud_unit.py", 
        "test_service_unit.py",
        "test_api_unit.py"
    ]
    
    print("🚀 开始运行单元测试...")
    
    for test_file in test_files:
        if os.path.exists(test_file):
            print(f"\n📋 运行 {test_file}...")
            try:
                result = subprocess.run([
                    sys.executable, "-m", "pytest", test_file, "-v", "--tb=short"
                ], capture_output=True, text=True, timeout=60)
                
                if result.returncode == 0:
                    print(f"✅ {test_file} 测试通过")
                else:
                    print(f"❌ {test_file} 测试失败")
                    print("错误输出:")
                    print(result.stdout)
                    print(result.stderr)
                    
            except subprocess.TimeoutExpired:
                print(f"⏰ {test_file} 测试超时")
            except Exception as e:
                print(f"❌ 运行 {test_file} 时出错: {e}")
        else:
            print(f"⚠️  测试文件 {test_file} 不存在")

def run_specific_test(test_name):
    """运行特定测试"""
    print(f"🎯 运行特定测试: {test_name}")
    
    try:
        result = subprocess.run([
            sys.executable, "-m", "pytest", test_name, "-v", "--tb=short"
        ], timeout=30)
        
        if result.returncode == 0:
            print(f"✅ {test_name} 测试通过")
        else:
            print(f"❌ {test_name} 测试失败")
            
    except subprocess.TimeoutExpired:
        print(f"⏰ {test_name} 测试超时")
    except Exception as e:
        print(f"❌ 运行 {test_name} 时出错: {e}")

def main():
    """主函数"""
    print("🧪 CogniBlock 单元测试运行器")
    print("=" * 50)
    
    # 设置测试环境
    setup_test_environment()
    
    # 检查参数
    if len(sys.argv) > 1:
        test_target = sys.argv[1]
        run_specific_test(test_target)
    else:
        run_tests()
    
    print("\n🏁 测试完成")

if __name__ == "__main__":
    main()