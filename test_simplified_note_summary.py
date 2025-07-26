#!/usr/bin/env python3
"""
简化笔记总结API测试脚本
测试新的单一API端点和WebSocket功能
"""

import asyncio
import json
import requests
import websockets
from datetime import datetime
import time

# API配置
BASE_URL = "http://localhost:8000"
API_BASE = f"{BASE_URL}/api/v2/note-summary"
WS_BASE = "ws://localhost:8000/api/v2/note-summary"

# 测试用户ID（需要根据实际情况调整）
TEST_USER_ID = "test_user_123"

def print_section(title):
    """打印测试章节标题"""
    print(f"\n{'='*60}")
    print(f"🧪 {title}")
    print(f"{'='*60}")

def print_result(test_name, success, details=None):
    """打印测试结果"""
    status = "✅ 通过" if success else "❌ 失败"
    print(f"{status} {test_name}")
    if details:
        print(f"   详情: {details}")

async def test_websocket_connection():
    """测试WebSocket连接"""
    print_section("WebSocket连接测试")
    
    try:
        uri = f"{WS_BASE}/ws/{TEST_USER_ID}"
        
        async with websockets.connect(uri) as websocket:
            print(f"🔗 连接到: {uri}")
            
            # 发送心跳
            await websocket.send("ping")
            response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
            
            if response == "pong":
                print_result("WebSocket心跳测试", True, "收到pong响应")
                return True
            else:
                print_result("WebSocket心跳测试", False, f"意外响应: {response}")
                return False
                
    except Exception as e:
        print_result("WebSocket连接", False, str(e))
        return False

def test_health_check():
    """测试健康检查端点"""
    print_section("健康检查测试")
    
    try:
        response = requests.get(f"{API_BASE}/health", timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            print_result("健康检查", True, f"状态: {data.get('status')}")
            
            # 打印详细信息
            if 'tasks' in data:
                tasks = data['tasks']
                print(f"   任务状态: 活跃={tasks.get('active', 0)}, 运行中={tasks.get('running', 0)}")
            
            if 'websocket' in data:
                ws = data['websocket']
                print(f"   WebSocket: 连接数={ws.get('total_connections', 0)}, 用户数={ws.get('active_users', 0)}")
            
            return True
        else:
            print_result("健康检查", False, f"状态码: {response.status_code}")
            return False
            
    except Exception as e:
        print_result("健康检查", False, str(e))
        return False

def test_create_summary_without_auth():
    """测试未认证的总结创建"""
    print_section("未认证访问测试")
    
    try:
        payload = {
            "content_ids": ["test_content_1", "test_content_2"]
        }
        
        response = requests.post(f"{API_BASE}/summarize", json=payload, timeout=10)
        
        if response.status_code == 401:
            print_result("未认证访问拒绝", True, "正确返回401状态码")
            return True
        else:
            print_result("未认证访问拒绝", False, f"状态码: {response.status_code}")
            return False
            
    except Exception as e:
        print_result("未认证访问测试", False, str(e))
        return False

def test_get_content_summary_without_auth():
    """测试未认证的内容总结获取"""
    print_section("未认证内容访问测试")
    
    try:
        response = requests.get(f"{API_BASE}/content/test_content_1", timeout=10)
        
        if response.status_code == 401:
            print_result("未认证内容访问拒绝", True, "正确返回401状态码")
            return True
        else:
            print_result("未认证内容访问拒绝", False, f"状态码: {response.status_code}")
            return False
            
    except Exception as e:
        print_result("未认证内容访问测试", False, str(e))
        return False

def test_api_documentation():
    """测试API文档访问"""
    print_section("API文档测试")
    
    try:
        # 测试OpenAPI文档
        response = requests.get(f"{BASE_URL}/openapi.json", timeout=10)
        
        if response.status_code == 200:
            openapi_data = response.json()
            print_result("OpenAPI文档", True, f"版本: {openapi_data.get('info', {}).get('version')}")
            
            # 检查是否包含笔记总结端点
            paths = openapi_data.get('paths', {})
            note_summary_paths = [path for path in paths.keys() if 'note-summary' in path]
            
            if note_summary_paths:
                print_result("笔记总结端点", True, f"找到 {len(note_summary_paths)} 个端点")
                for path in note_summary_paths[:3]:  # 只显示前3个
                    print(f"   - {path}")
            else:
                print_result("笔记总结端点", False, "未找到相关端点")
            
            return True
        else:
            print_result("OpenAPI文档", False, f"状态码: {response.status_code}")
            return False
            
    except Exception as e:
        print_result("API文档测试", False, str(e))
        return False

def test_swagger_ui():
    """测试Swagger UI访问"""
    print_section("Swagger UI测试")
    
    try:
        response = requests.get(f"{BASE_URL}/docs", timeout=10)
        
        if response.status_code == 200:
            print_result("Swagger UI", True, "文档页面可访问")
            return True
        else:
            print_result("Swagger UI", False, f"状态码: {response.status_code}")
            return False
            
    except Exception as e:
        print_result("Swagger UI测试", False, str(e))
        return False

async def run_websocket_tests():
    """运行WebSocket相关测试"""
    print_section("WebSocket功能测试")
    
    # 测试连接
    connection_success = await test_websocket_connection()
    
    if connection_success:
        print("✅ WebSocket功能正常")
    else:
        print("❌ WebSocket功能异常")
    
    return connection_success

def run_api_tests():
    """运行API相关测试"""
    print_section("API功能测试")
    
    results = []
    
    # 健康检查
    results.append(test_health_check())
    
    # 认证测试
    results.append(test_create_summary_without_auth())
    results.append(test_get_content_summary_without_auth())
    
    # 文档测试
    results.append(test_api_documentation())
    results.append(test_swagger_ui())
    
    success_count = sum(results)
    total_count = len(results)
    
    print(f"\n📊 API测试结果: {success_count}/{total_count} 通过")
    
    return success_count == total_count

async def main():
    """主测试函数"""
    print("🚀 开始简化笔记总结API测试")
    print(f"📍 测试目标: {BASE_URL}")
    print(f"⏰ 测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 等待服务器启动
    print("\n⏳ 等待服务器启动...")
    time.sleep(2)
    
    # 运行API测试
    api_success = run_api_tests()
    
    # 运行WebSocket测试
    ws_success = await run_websocket_tests()
    
    # 总结
    print_section("测试总结")
    
    if api_success and ws_success:
        print("🎉 所有测试通过！简化的笔记总结API已准备就绪")
        print("\n📋 可用端点:")
        print("   - POST /api/v2/note-summary/summarize - 创建总结任务")
        print("   - GET /api/v2/note-summary/task/{task_id} - 获取任务状态")
        print("   - GET /api/v2/note-summary/content/{content_id} - 获取内容总结")
        print("   - GET /api/v2/note-summary/user/tasks - 获取用户任务列表")
        print("   - DELETE /api/v2/note-summary/task/{task_id} - 取消任务")
        print("   - WS /api/v2/note-summary/ws/{user_id} - WebSocket实时通知")
        print("   - GET /api/v2/note-summary/health - 健康检查")
        
        print("\n🔗 文档链接:")
        print(f"   - Swagger UI: {BASE_URL}/docs")
        print(f"   - ReDoc: {BASE_URL}/redoc")
        print(f"   - OpenAPI JSON: {BASE_URL}/openapi.json")
        
    else:
        print("⚠️ 部分测试失败，请检查服务器状态")
        if not api_success:
            print("   - API功能存在问题")
        if not ws_success:
            print("   - WebSocket功能存在问题")

if __name__ == "__main__":
    asyncio.run(main())