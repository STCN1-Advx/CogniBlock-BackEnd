#!/usr/bin/env python3
"""
CogniBlock 测试运行器
统一的测试入口点，支持运行不同类型的测试
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def run_unit_tests():
    """运行单元测试"""
    print("运行单元测试...")
    cmd = ["python", "-m", "pytest", "tests/unit", "-v"]
    return subprocess.run(cmd, cwd=project_root).returncode

def run_integration_tests():
    """运行集成测试"""
    print("运行集成测试...")
    cmd = ["python", "-m", "pytest", "tests/integration", "-v"]
    return subprocess.run(cmd, cwd=project_root).returncode

def run_api_tests():
    """运行API测试"""
    print("运行API测试...")
    cmd = ["python", "-m", "pytest", "tests/api", "-v"]
    return subprocess.run(cmd, cwd=project_root).returncode

def run_all_tests():
    """运行所有测试"""
    print("运行所有测试...")
    cmd = ["python", "-m", "pytest", "tests", "-v"]
    return subprocess.run(cmd, cwd=project_root).returncode

def run_quick_check():
    """运行快速检查"""
    print("运行快速检查...")
    try:
        from tests.utils.basic_test import main as basic_test
        return basic_test()
    except ImportError:
        print("无法导入基础测试模块")
        return 1

def main():
    parser = argparse.ArgumentParser(description="CogniBlock 测试运行器")
    parser.add_argument("--type", choices=["unit", "integration", "api", "all", "quick"], 
                       default="quick", help="测试类型")
    parser.add_argument("--verbose", "-v", action="store_true", help="详细输出")
    
    args = parser.parse_args()
    
    if args.type == "unit":
        return run_unit_tests()
    elif args.type == "integration":
        return run_integration_tests()
    elif args.type == "api":
        return run_api_tests()
    elif args.type == "all":
        return run_all_tests()
    elif args.type == "quick":
        return run_quick_check()
    
    return 0

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)