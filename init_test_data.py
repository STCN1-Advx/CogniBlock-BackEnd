#!/usr/bin/env python3
"""
数据库测试数据初始化脚本

该脚本用于为 Canvas 卡片管理 API 初始化必要的测试数据。
"""

import sys
import os
from datetime import datetime

# 添加项目根目录到 Python 路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
from app.models.canvas import Canvas
from app.models.card import Card
from app.models.content import Content
from app.models.user_content import UserContent


def init_test_data():
    """
    初始化测试数据
    """
    # 创建数据库连接
    engine = create_engine(settings.DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    try:
        print("开始初始化测试数据...")
        
        # 修复序列问题
        print("修复数据库序列...")
        db.execute(text("SELECT setval('canvases_id_seq', (SELECT COALESCE(MAX(id), 1) FROM canvases));"))
        db.execute(text("SELECT setval('contents_id_seq', (SELECT COALESCE(MAX(id), 1) FROM contents));"))
        db.execute(text("SELECT setval('cards_id_seq', (SELECT COALESCE(MAX(id), 1) FROM cards));"))
        db.commit()
        print("序列修复完成")
        
        # 已知的用户 ID
        user1_id = "869a8c52-1ce2-4e8e-95ec-1599922b0c9e"  # jiangyin14
        user2_id = "164924d3-bd3f-4222-8a65-fbf43e568acc"  # LaoShui
        
        # 1. 创建更多画布
        print("创建测试画布...")
        canvases_to_create = [
            {"owner_id": user2_id, "name": "测试画布1"},
            {"owner_id": user1_id, "name": "工作空间"},
            {"owner_id": user1_id, "name": "项目规划"},
            {"owner_id": user2_id, "name": "学习笔记"}
        ]
        
        created_canvases = []
        for canvas_data in canvases_to_create:
            # 检查是否已存在同名画布
            existing = db.query(Canvas).filter(
                Canvas.owner_id == canvas_data["owner_id"],
                Canvas.name == canvas_data["name"]
            ).first()
            
            if not existing:
                canvas = Canvas(
                    owner_id=canvas_data["owner_id"],
                    name=canvas_data["name"],
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                db.add(canvas)
                db.flush()  # 获取 ID
                created_canvases.append(canvas)
                print(f"  创建画布: {canvas.name} (ID: {canvas.id})")
            else:
                created_canvases.append(existing)
                print(f"  画布已存在: {existing.name} (ID: {existing.id})")
        
        # 2. 创建更多内容
        print("\n创建测试内容...")
        contents_to_create = [
            {"content_type": "text", "text_data": "这是一个文本卡片示例"},
            {"content_type": "text", "text_data": "任务：完成 API 开发"},
            {"content_type": "text", "text_data": "想法：改进用户体验"},
            {"content_type": "text", "text_data": "备注：需要进一步讨论"},
            {"content_type": "image", "image_data": "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAAYEBQYFBAYGBQYHBwYIChAKCgkJChQODwwQFxQYGBcUFhYaHSUfGhsjHBYWICwgIyYnKSopGR8tMC0oMCUoKSj/2wBDAQcHBwoIChMKChMoGhYaKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCj/wAARCAABAAEDASIAAhEBAxEB/8QAFQABAQAAAAAAAAAAAAAAAAAAAAv/xAAUEAEAAAAAAAAAAAAAAAAAAAAA/8QAFQEBAQAAAAAAAAAAAAAAAAAAAAX/xAAUEQEAAAAAAAAAAAAAAAAAAAAA/9oADAMBAAIRAxEAPwCdABmX/9k="},
            {"content_type": "image", "image_data": "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAAYEBQYFBAYGBQYHBwYIChAKCgkJChQODwwQFxQYGBcUFhYaHSUfGhsjHBYWICwgIyYnKSopGR8tMC0oMCUoKSj/2wBDAQcHBwoIChMKChMoGhYaKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCj/wAARCAABAAEDASIAAhEBAxEB/8QAFQABAQAAAAAAAAAAAAAAAAAAAAv/xAAUEAEAAAAAAAAAAAAAAAAAAAAA/8QAFQEBAQAAAAAAAAAAAAAAAAAAAAX/xAAUEQEAAAAAAAAAAAAAAAAAAAAA/9oADAMBAAIRAxEAPwCdABmX/9k="}
        ]
        
        created_contents = []
        for content_data in contents_to_create:
            content = Content(
                content_type=content_data["content_type"],
                text_data=content_data.get("text_data"),
                image_data=content_data.get("image_data"),
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            db.add(content)
            db.flush()  # 获取 ID
            created_contents.append(content)
            print(f"  创建内容: {content.content_type} (ID: {content.id})")
            
            # 为内容创建用户关联（随机分配给用户）
            user_id = user1_id if len(created_contents) % 2 == 1 else user2_id
            
            # 检查是否已存在关联
            existing_relation = db.query(UserContent).filter(
                UserContent.user_id == user_id,
                UserContent.content_id == content.id
            ).first()
            
            if not existing_relation:
                user_content = UserContent(
                    user_id=user_id,
                    content_id=content.id,
                    permission="owner"
                )
                db.add(user_content)
                print(f"    关联用户: {user_id}")
        
        # 3. 创建卡片
        print("\n创建测试卡片...")
        cards_to_create = [
            # 为第一个新画布创建卡片
            {"canvas_id": created_canvases[0].id, "content_id": created_contents[0].id, "position_x": 10, "position_y": 10},
            {"canvas_id": created_canvases[0].id, "content_id": created_contents[1].id, "position_x": 200, "position_y": 50},
            {"canvas_id": created_canvases[0].id, "content_id": created_contents[4].id, "position_x": 400, "position_y": 100},
            
            # 为第二个新画布创建卡片
            {"canvas_id": created_canvases[1].id, "content_id": created_contents[2].id, "position_x": 50, "position_y": 30},
            {"canvas_id": created_canvases[1].id, "content_id": created_contents[3].id, "position_x": 250, "position_y": 80},
            {"canvas_id": created_canvases[1].id, "content_id": created_contents[5].id, "position_x": 450, "position_y": 120},
            
            # 为第三个新画布创建卡片
            {"canvas_id": created_canvases[2].id, "content_id": created_contents[0].id, "position_x": 100, "position_y": 60},
            {"canvas_id": created_canvases[2].id, "content_id": created_contents[2].id, "position_x": 300, "position_y": 90}
        ]
        
        for card_data in cards_to_create:
            # 检查是否已存在相同的卡片
            existing_card = db.query(Card).filter(
                Card.canvas_id == card_data["canvas_id"],
                Card.content_id == card_data["content_id"]
            ).first()
            
            if not existing_card:
                card = Card(
                    canvas_id=card_data["canvas_id"],
                    content_id=card_data["content_id"],
                    position_x=card_data["position_x"],
                    position_y=card_data["position_y"],
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                db.add(card)
                db.flush()  # 获取 ID
                print(f"  创建卡片: Canvas {card.canvas_id}, Content {card.content_id} (ID: {card.id})")
            else:
                print(f"  卡片已存在: Canvas {existing_card.canvas_id}, Content {existing_card.content_id} (ID: {existing_card.id})")
        
        # 提交所有更改
        db.commit()
        print("\n✅ 测试数据初始化完成！")
        
        # 显示统计信息
        canvas_count = db.query(Canvas).count()
        content_count = db.query(Content).count()
        card_count = db.query(Card).count()
        user_content_count = db.query(UserContent).count()
        
        print(f"\n📊 数据库统计:")
        print(f"  画布总数: {canvas_count}")
        print(f"  内容总数: {content_count}")
        print(f"  卡片总数: {card_count}")
        print(f"  用户内容关联总数: {user_content_count}")
        
    except Exception as e:
        print(f"❌ 初始化失败: {str(e)}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    init_test_data()