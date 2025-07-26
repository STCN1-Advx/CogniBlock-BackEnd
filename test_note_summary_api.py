#!/usr/bin/env python3
"""
笔记总结API功能测试脚本
"""

import requests
import json
import time
from typing import Dict, Any

# API基础URL
BASE_URL = "http://localhost:8000/api/v2"

def test_note_summary_api():
    """测试笔记总结API功能"""
    print("🧪 开始测试笔记总结API功能...")
    print("=" * 50)
    
    # 测试数据
    test_content_ids = ["1", "2", "3"]  # 假设这些内容ID存在
    
    try:
        # 1. 测试创建总结任务
        print("📝 测试创建总结任务...")
        create_response = requests.post(
            f"{BASE_URL}/note-summary/create",
            json={"content_ids": test_content_ids},
            headers={"Content-Type": "application/json"}
        )
        
        print(f"状态码: {create_response.status_code}")
        if create_response.status_code == 200:
            task_data = create_response.json()
            task_id = task_data.get("task_id")
            print(f"✅ 任务创建成功，任务ID: {task_id}")
            
            # 2. 测试获取任务状态
            print("\n📊 测试获取任务状态...")
            status_response = requests.get(f"{BASE_URL}/note-summary/task/{task_id}")
            print(f"状态码: {status_response.status_code}")
            if status_response.status_code == 200:
                status_data = status_response.json()
                print(f"✅ 任务状态: {status_data.get('status')}")
                print(f"   进度: {status_data.get('progress', 0)}%")
            else:
                print(f"❌ 获取任务状态失败: {status_response.text}")
            
            # 3. 测试获取用户任务列表
            print("\n📋 测试获取用户任务列表...")
            tasks_response = requests.get(f"{BASE_URL}/note-summary/tasks")
            print(f"状态码: {tasks_response.status_code}")
            if tasks_response.status_code == 200:
                tasks_data = tasks_response.json()
                print(f"✅ 用户任务数量: {len(tasks_data.get('tasks', []))}")
            else:
                print(f"❌ 获取任务列表失败: {tasks_response.text}")
                
        else:
            print(f"❌ 创建任务失败: {create_response.text}")
        
        # 4. 测试获取单个内容总结
        print("\n📄 测试获取单个内容总结...")
        content_response = requests.get(f"{BASE_URL}/note-summary/content/1/summary")
        print(f"状态码: {content_response.status_code}")
        if content_response.status_code == 200:
            content_data = content_response.json()
            print(f"✅ 内容总结获取成功")
            print(f"   标题: {content_data.get('title', 'N/A')}")
            print(f"   主题: {content_data.get('topic', 'N/A')}")
        elif content_response.status_code == 404:
            print("ℹ️  该内容暂无总结（正常情况）")
        else:
            print(f"❌ 获取内容总结失败: {content_response.text}")
        
        # 5. 测试搜索总结内容
        print("\n🔍 测试搜索总结内容...")
        search_response = requests.get(
            f"{BASE_URL}/note-summary/search",
            params={"query": "测试", "limit": 10}
        )
        print(f"状态码: {search_response.status_code}")
        if search_response.status_code == 200:
            search_data = search_response.json()
            print(f"✅ 搜索结果数量: {len(search_data.get('results', []))}")
        else:
            print(f"❌ 搜索失败: {search_response.text}")
        
        # 6. 测试获取统计信息
        print("\n📈 测试获取统计信息...")
        stats_response = requests.get(f"{BASE_URL}/note-summary/stats")
        print(f"状态码: {stats_response.status_code}")
        if stats_response.status_code == 200:
            stats_data = stats_response.json()
            print(f"✅ 统计信息获取成功")
            print(f"   总内容数: {stats_data.get('total_contents', 0)}")
            print(f"   已总结数: {stats_data.get('summarized_contents', 0)}")
        else:
            print(f"❌ 获取统计信息失败: {stats_response.text}")
            
    except requests.exceptions.ConnectionError:
        print("❌ 连接失败：请确保服务器正在运行")
    except Exception as e:
        print(f"❌ 测试过程中发生错误: {e}")
    
    print("\n" + "=" * 50)
    print("🎯 笔记总结API测试完成")

def test_api_documentation():
    """测试API文档是否可访问"""
    print("\n📚 测试API文档访问...")
    try:
        docs_response = requests.get("http://localhost:8000/docs")
        if docs_response.status_code == 200:
            print("✅ API文档可正常访问: http://localhost:8000/docs")
        else:
            print(f"❌ API文档访问失败: {docs_response.status_code}")
    except Exception as e:
        print(f"❌ API文档访问错误: {e}")

def test_server_health():
    """测试服务器健康状态"""
    print("🏥 测试服务器健康状态...")
    try:
        health_response = requests.get("http://localhost:8000/")
        if health_response.status_code == 200:
            print("✅ 服务器运行正常")
        else:
            print(f"⚠️  服务器响应异常: {health_response.status_code}")
    except Exception as e:
        print(f"❌ 服务器连接失败: {e}")

if __name__ == "__main__":
    print("🚀 CogniBlock 笔记总结功能测试")
    print("=" * 50)
    
    # 基础健康检查
    test_server_health()
    
    # API文档检查
    test_api_documentation()
    
    # 笔记总结功能测试
    test_note_summary_api()
    
    print("\n🎉 所有测试完成！")
    print("💡 提示：某些测试可能因为缺少认证或测试数据而失败，这是正常的。")
    print("📖 请访问 http://localhost:8000/docs 查看完整的API文档。")