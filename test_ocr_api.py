"""
OCR API 测试脚本
用于测试 /api/v2/ocr 端点的功能
"""

import requests
import json
import time
import os
from pathlib import Path

# API基础URL
BASE_URL = "http://localhost:8000/api/v2/ocr"

def test_get_models():
    """测试获取模型列表"""
    print("=== 测试获取模型列表 ===")
    try:
        response = requests.get(f"{BASE_URL}/models")
        print(f"状态码: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"可用模型数量: {len(data['models'])}")
            for model in data['models']:
                print(f"- {model['name']}: {model['description']} (可用: {model['available']})")
        else:
            print(f"错误: {response.text}")
    except Exception as e:
        print(f"请求失败: {e}")
    print()

def test_create_ocr_task(image_path: str):
    """测试创建OCR任务"""
    print("=== 测试创建OCR任务 ===")
    
    if not os.path.exists(image_path):
        print(f"图片文件不存在: {image_path}")
        return None
    
    try:
        with open(image_path, 'rb') as f:
            files = {'file': f}
            data = {
                'model': 'gemini-2.0-flash-exp',
                'prompt': '请提取这张图片中的所有文字内容，保持原有的格式和布局。'
            }
            
            response = requests.post(f"{BASE_URL}/extract", files=files, data=data)
            print(f"状态码: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                task_id = result['task_id']
                print(f"任务ID: {task_id}")
                print(f"状态: {result['status']}")
                print(f"消息: {result['message']}")
                return task_id
            else:
                print(f"错误: {response.text}")
                return None
    except Exception as e:
        print(f"请求失败: {e}")
        return None
    print()

def test_get_task_status(task_id: str):
    """测试获取任务状态"""
    print("=== 测试获取任务状态 ===")
    try:
        response = requests.get(f"{BASE_URL}/task/{task_id}")
        print(f"状态码: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"任务ID: {data['task_id']}")
            print(f"状态: {data['status']}")
            print(f"进度: {data['progress']}%")
            if data.get('result'):
                print(f"结果: {data['result'][:100]}...")
            if data.get('error'):
                print(f"错误: {data['error']}")
            return data['status']
        else:
            print(f"错误: {response.text}")
            return None
    except Exception as e:
        print(f"请求失败: {e}")
        return None
    print()

def test_get_task_result(task_id: str):
    """测试获取任务结果"""
    print("=== 测试获取任务结果 ===")
    try:
        response = requests.get(f"{BASE_URL}/task/{task_id}/result")
        print(f"状态码: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"任务ID: {data['task_id']}")
            print(f"模型: {data['model']}")
            print(f"结果: {data['result']}")
        else:
            print(f"错误: {response.text}")
    except Exception as e:
        print(f"请求失败: {e}")
    print()

def test_stream_ocr(image_path: str):
    """测试流式OCR"""
    print("=== 测试流式OCR ===")
    
    if not os.path.exists(image_path):
        print(f"图片文件不存在: {image_path}")
        return
    
    try:
        with open(image_path, 'rb') as f:
            files = {'file': f}
            data = {
                'model': 'gemini-2.0-flash-exp',
                'prompt': '请提取这张图片中的所有文字内容，保持原有的格式和布局。'
            }
            
            response = requests.post(f"{BASE_URL}/extract/stream", files=files, data=data, stream=True)
            print(f"状态码: {response.status_code}")
            
            if response.status_code == 200:
                print("流式响应:")
                for line in response.iter_lines():
                    if line:
                        line_str = line.decode('utf-8')
                        if line_str.startswith('data: '):
                            try:
                                data = json.loads(line_str[6:])
                                if data.get('chunk'):
                                    print(data['chunk'], end='', flush=True)
                                elif data.get('finished'):
                                    print("\n[流式传输完成]")
                                    break
                                elif data.get('error'):
                                    print(f"\n[错误]: {data['error']}")
                                    break
                            except json.JSONDecodeError:
                                continue
            else:
                print(f"错误: {response.text}")
    except Exception as e:
        print(f"请求失败: {e}")
    print()

def main():
    """主测试函数"""
    print("OCR API 测试开始")
    print("=" * 50)
    
    # 1. 测试获取模型列表
    test_get_models()
    
    # 2. 准备测试图片（需要用户提供）
    image_path = input("请输入测试图片路径（或按回车跳过任务测试）: ").strip()
    
    if image_path and os.path.exists(image_path):
        # 3. 测试创建OCR任务
        task_id = test_create_ocr_task(image_path)
        
        if task_id:
            # 4. 轮询任务状态直到完成
            print("=== 轮询任务状态 ===")
            max_attempts = 30  # 最多等待30次
            attempt = 0
            
            while attempt < max_attempts:
                status = test_get_task_status(task_id)
                if status in ['completed', 'failed']:
                    break
                time.sleep(2)  # 等待2秒
                attempt += 1
            
            # 5. 如果任务完成，获取结果
            if status == 'completed':
                test_get_task_result(task_id)
        
        # 6. 测试流式OCR
        test_stream_ocr(image_path)
    else:
        print("跳过任务测试（未提供有效图片路径）")
    
    print("=" * 50)
    print("OCR API 测试完成")

if __name__ == "__main__":
    main()