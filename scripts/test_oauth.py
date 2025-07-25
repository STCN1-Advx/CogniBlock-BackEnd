#!/usr/bin/env python3
"""
OAuth测试脚本 - 启动服务器并打开测试页面
"""
import webbrowser
import time
import subprocess
import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def start_server():
    """启动FastAPI服务器"""
    print("🚀 启动CogniBlock服务器...")
    try:
        # 切换到项目根目录
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        # 启动服务器
        process = subprocess.Popen([
            sys.executable, "-m", "uvicorn", 
            "app.main:app", 
            "--reload", 
            "--host", "0.0.0.0", 
            "--port", "8000"
        ], cwd=project_root)
        
        # 等待服务器启动
        print("⏳ 等待服务器启动...")
        time.sleep(3)
        
        # 打开测试页面
        test_url = "http://localhost:8000/static/oauth_test.html"
        print(f"🌐 打开测试页面: {test_url}")
        webbrowser.open(test_url)
        
        print("\n" + "="*50)
        print("🎯 OAuth测试说明:")
        print("1. 点击 '开始 OAuth 登录' 按钮")
        print("2. 在Casdoor页面完成登录")
        print("3. 登录成功后会自动回调并显示用户信息")
        print("4. 可以测试其他API端点")
        print("\n📋 API端点:")
        print("- 登录: GET /api/v2/auth/login")
        print("- 回调: GET /api/v2/auth/oauth/callback")
        print("- 用户: GET /api/v2/users/{user_id}")
        print("- 健康检查: GET /health")
        print("- API文档: http://localhost:8000/docs")
        print("="*50)
        
        print("\n按 Ctrl+C 停止服务器")
        
        # 等待用户中断
        try:
            process.wait()
        except KeyboardInterrupt:
            print("\n🛑 正在停止服务器...")
            process.terminate()
            process.wait()
            print("✅ 服务器已停止")
            
    except Exception as e:
        print(f"❌ 启动失败: {e}")
        return False
    
    return True

if __name__ == "__main__":
    print("🔐 CogniBlock OAuth 测试工具")
    print("="*30)
    
    # 检查依赖
    try:
        import fastapi
        import uvicorn
        import jwt
        import requests
        print("✅ 依赖检查通过")
    except ImportError as e:
        print(f"❌ 缺少依赖: {e}")
        print("请运行: pip install -r requirements.txt")
        sys.exit(1)
    
    # 检查数据库连接
    try:
        from app.db.base import engine
        with engine.connect() as conn:
            print("✅ 数据库连接正常")
    except Exception as e:
        print(f"⚠️  数据库连接警告: {e}")
        print("请确保PostgreSQL正在运行")
    
    # 启动服务器
    start_server()
