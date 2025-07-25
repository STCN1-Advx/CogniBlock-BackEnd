"""
画布API使用示例
展示如何使用Pull和Push API端点进行画布操作
"""
import asyncio
import json
from typing import List, Dict, Any
from uuid import uuid4

# 模拟API请求和响应的示例数据
class CanvaAPIExample:
    """画布API使用示例"""
    
    def __init__(self):
        self.base_url = "http://localhost:8000/api/v2/canva"
        self.user_id = str(uuid4())
        self.canvas_id = 12
        
    def example_pull_request(self) -> Dict[str, Any]:
        """Pull API请求示例"""
        return {
            "url": f"{self.base_url}/pull",
            "method": "POST",
            "headers": {
                "Content-Type": "application/json",
                "X-User-ID": self.user_id
            },
            "body": {
                "canva_id": self.canvas_id
            }
        }
    
    def example_pull_response(self) -> List[Dict[str, Any]]:
        """Pull API响应示例"""
        return [
            {
                "card_id": 101,
                "position": {
                    "x": 12.12,
                    "y": 86.21
                },
                "content_id": 104
            },
            {
                "card_id": 102,
                "position": {
                    "x": 22.42,
                    "y": 81.15
                },
                "content_id": 101
            },
            {
                "card_id": 103,
                "position": {
                    "x": 45.67,
                    "y": 123.89
                },
                "content_id": 107
            }
        ]
    
    def example_push_request(self) -> Dict[str, Any]:
        """Push API请求示例"""
        return {
            "url": f"{self.base_url}/push",
            "method": "POST",
            "headers": {
                "Content-Type": "application/json",
                "X-User-ID": self.user_id
            },
            "body": {
                "canva_id": self.canvas_id,
                "cards": [
                    {
                        "card_id": 101,
                        "position": {
                            "x": 15.50,  # 更新位置
                            "y": 90.30
                        },
                        "content_id": 104
                    },
                    {
                        "card_id": 102,
                        "position": {
                            "x": 25.75,  # 更新位置
                            "y": 85.60
                        },
                        "content_id": 101
                    },
                    {
                        "card_id": 103,
                        "position": {
                            "x": 50.00,  # 更新位置
                            "y": 130.00
                        },
                        "content_id": 108  # 更新内容
                    }
                ]
            }
        }
    
    def example_push_response(self) -> Dict[str, Any]:
        """Push API响应示例"""
        return {
            "message": "Canvas updated successfully",
            "canvas_id": self.canvas_id,
            "updated_cards": 3
        }
    
    def example_canvas_info_request(self) -> Dict[str, Any]:
        """画布信息API请求示例"""
        return {
            "url": f"{self.base_url}/info/{self.canvas_id}",
            "method": "GET",
            "headers": {
                "X-User-ID": self.user_id
            }
        }
    
    def example_error_responses(self) -> Dict[str, Dict[str, Any]]:
        """错误响应示例"""
        return {
            "canvas_not_found": {
                "status_code": 404,
                "body": {
                    "detail": f"Canvas with id {self.canvas_id} not found"
                }
            },
            "permission_denied": {
                "status_code": 403,
                "body": {
                    "detail": "Permission denied: User does not have access to this canvas"
                }
            },
            "validation_error": {
                "status_code": 400,
                "body": {
                    "detail": "Validation error: Card ID cannot be negative"
                }
            },
            "authentication_error": {
                "status_code": 401,
                "body": {
                    "detail": "Authentication required: X-User-ID header missing"
                }
            }
        }
    
    def print_examples(self):
        """打印所有API使用示例"""
        print("=" * 60)
        print("画布API使用示例")
        print("=" * 60)
        
        print("\n1. Pull API - 拉取画布状态")
        print("-" * 40)
        print("请求:")
        print(json.dumps(self.example_pull_request(), indent=2, ensure_ascii=False))
        print("\n响应:")
        print(json.dumps(self.example_pull_response(), indent=2, ensure_ascii=False))
        
        print("\n2. Push API - 推送画布更新")
        print("-" * 40)
        print("请求:")
        print(json.dumps(self.example_push_request(), indent=2, ensure_ascii=False))
        print("\n响应:")
        print(json.dumps(self.example_push_response(), indent=2, ensure_ascii=False))
        
        print("\n3. Canvas Info API - 获取画布信息")
        print("-" * 40)
        print("请求:")
        print(json.dumps(self.example_canvas_info_request(), indent=2, ensure_ascii=False))
        
        print("\n4. 错误响应示例")
        print("-" * 40)
        errors = self.example_error_responses()
        for error_type, error_data in errors.items():
            print(f"\n{error_type}:")
            print(json.dumps(error_data, indent=2, ensure_ascii=False))


class CanvaAPIWorkflow:
    """画布API工作流示例"""
    
    def __init__(self):
        self.canvas_id = 12
        self.user_id = str(uuid4())
    
    async def simulate_canvas_workflow(self):
        """模拟完整的画布操作工作流"""
        print("\n" + "=" * 60)
        print("画布API工作流示例")
        print("=" * 60)
        
        # 步骤1: 拉取画布当前状态
        print("\n步骤1: 拉取画布当前状态")
        print("-" * 30)
        current_state = await self.pull_canvas_state()
        print(f"获取到 {len(current_state)} 个卡片")
        
        # 步骤2: 修改卡片位置
        print("\n步骤2: 修改卡片位置")
        print("-" * 30)
        updated_cards = self.update_card_positions(current_state)
        print(f"更新了 {len(updated_cards)} 个卡片的位置")
        
        # 步骤3: 推送更新
        print("\n步骤3: 推送更新到服务器")
        print("-" * 30)
        result = await self.push_canvas_updates(updated_cards)
        print(f"推送结果: {result['message']}")
        
        # 步骤4: 验证更新
        print("\n步骤4: 验证更新结果")
        print("-" * 30)
        new_state = await self.pull_canvas_state()
        print(f"验证完成，当前有 {len(new_state)} 个卡片")
        
        return new_state
    
    async def pull_canvas_state(self) -> List[Dict[str, Any]]:
        """模拟拉取画布状态"""
        # 模拟API调用
        await asyncio.sleep(0.1)  # 模拟网络延迟
        
        return [
            {
                "card_id": 101,
                "position": {"x": 12.12, "y": 86.21},
                "content_id": 104
            },
            {
                "card_id": 102,
                "position": {"x": 22.42, "y": 81.15},
                "content_id": 101
            }
        ]
    
    def update_card_positions(self, cards: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """更新卡片位置"""
        updated_cards = []
        
        for card in cards:
            # 模拟位置更新（向右移动10个单位）
            updated_card = card.copy()
            updated_card["position"]["x"] += 10.0
            updated_cards.append(updated_card)
        
        return updated_cards
    
    async def push_canvas_updates(self, cards: List[Dict[str, Any]]) -> Dict[str, Any]:
        """模拟推送画布更新"""
        # 模拟API调用
        await asyncio.sleep(0.1)  # 模拟网络延迟
        
        return {
            "message": "Canvas updated successfully",
            "canvas_id": self.canvas_id,
            "updated_cards": len(cards)
        }


class CanvaAPIValidationExamples:
    """画布API数据验证示例"""
    
    def demonstrate_validation_rules(self):
        """演示数据验证规则"""
        print("\n" + "=" * 60)
        print("画布API数据验证示例")
        print("=" * 60)
        
        print("\n1. 有效的Pull请求")
        print("-" * 30)
        valid_pull = {
            "canva_id": 12  # 正整数
        }
        print(json.dumps(valid_pull, indent=2))
        
        print("\n2. 无效的Pull请求")
        print("-" * 30)
        invalid_pulls = [
            {"canva_id": 0},      # 零
            {"canva_id": -1},     # 负数
            {}                    # 缺少字段
        ]
        for i, invalid in enumerate(invalid_pulls, 1):
            print(f"无效示例 {i}: {json.dumps(invalid)}")
        
        print("\n3. 有效的Push请求")
        print("-" * 30)
        valid_push = {
            "canva_id": 12,
            "cards": [
                {
                    "card_id": 101,
                    "position": {"x": 12.12, "y": 86.21},
                    "content_id": 104
                }
            ]
        }
        print(json.dumps(valid_push, indent=2))
        
        print("\n4. 无效的Push请求")
        print("-" * 30)
        invalid_pushes = [
            {
                "canva_id": 12,
                "cards": []  # 空卡片列表
            },
            {
                "canva_id": 12,
                "cards": [
                    {
                        "card_id": 101,
                        "position": {"x": -1.0, "y": 86.21},  # 负坐标
                        "content_id": 104
                    }
                ]
            },
            {
                "canva_id": 12,
                "cards": [
                    {
                        "card_id": 101,
                        "position": {"x": 12.12, "y": 86.21},
                        "content_id": 104
                    },
                    {
                        "card_id": 101,  # 重复的card_id
                        "position": {"x": 22.42, "y": 81.15},
                        "content_id": 105
                    }
                ]
            }
        ]
        
        for i, invalid in enumerate(invalid_pushes, 1):
            print(f"无效示例 {i}:")
            print(json.dumps(invalid, indent=2))
            print()


def main():
    """主函数 - 运行所有示例"""
    # API使用示例
    api_example = CanvaAPIExample()
    api_example.print_examples()
    
    # 数据验证示例
    validation_example = CanvaAPIValidationExamples()
    validation_example.demonstrate_validation_rules()
    
    # 工作流示例
    async def run_workflow():
        workflow = CanvaAPIWorkflow()
        await workflow.simulate_canvas_workflow()
    
    # 运行异步工作流
    asyncio.run(run_workflow())
    
    print("\n" + "=" * 60)
    print("所有示例演示完成")
    print("=" * 60)


if __name__ == "__main__":
    main()