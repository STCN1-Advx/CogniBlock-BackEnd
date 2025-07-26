#!/usr/bin/env python3
"""
社群功能测试脚本
测试标签生成、内容发布等功能
"""

import sys
import os
import asyncio
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.session import SessionLocal
from app.crud.tag import tag as tag_crud
from app.crud.content_tag import content_tag as content_tag_crud
from app.crud.content import content as content_crud
from app.services.tag_generation_service import tag_generation_service


def test_tag_crud():
    """测试标签CRUD操作"""
    print("🏷️  测试标签CRUD操作...")
    
    db = SessionLocal()
    try:
        # 创建测试标签
        tag1 = tag_crud.create(db, "数学", "数学相关内容")
        tag2 = tag_crud.create(db, "物理", "物理相关内容")
        tag3 = tag_crud.create(db, "编程", "编程相关内容")
        
        print(f"✅ 创建标签: {tag1.name}, {tag2.name}, {tag3.name}")
        
        # 测试获取标签
        all_tags = tag_crud.get_multi(db, 0, 10)
        print(f"✅ 获取标签列表: {len(all_tags)} 个标签")
        
        # 测试搜索标签
        search_results = tag_crud.search_tags(db, "数学", 0, 10)
        print(f"✅ 搜索标签 '数学': {len(search_results)} 个结果")
        
        # 测试获取或创建标签
        existing_tag = tag_crud.get_or_create(db, "数学", "数学相关内容")
        new_tag = tag_crud.get_or_create(db, "化学", "化学相关内容")
        print(f"✅ 获取或创建标签: 现有={existing_tag.name}, 新建={new_tag.name}")
        
        return True
        
    except Exception as e:
        print(f"❌ 标签CRUD测试失败: {e}")
        return False
    finally:
        db.close()


def test_content_tag_crud():
    """测试内容标签关联CRUD操作"""
    print("🔗 测试内容标签关联CRUD操作...")
    
    db = SessionLocal()
    try:
        # 假设已有content和tag
        tags = tag_crud.get_multi(db, 0, 5)
        contents = content_crud.get_multi(db, 0, 5)
        
        if not tags or not contents:
            print("⚠️  需要先有标签和内容数据")
            return False
        
        content_id = contents[0].id
        tag_ids = [tag.id for tag in tags[:3]]
        
        # 批量创建标签关联
        content_tags = content_tag_crud.bulk_create_tags_for_content(
            db, content_id, tag_ids, confidence=0.9
        )
        print(f"✅ 为内容 {content_id} 添加了 {len(content_tags)} 个标签")
        
        # 获取内容的标签
        content_tags_list = content_tag_crud.get_content_tags(db, content_id)
        print(f"✅ 内容 {content_id} 的标签: {[tag.name for tag in content_tags_list]}")
        
        # 获取标签的内容
        tag_contents = content_tag_crud.get_tag_contents(db, tag_ids[0], public_only=False, skip=0, limit=10)
        print(f"✅ 标签 {tags[0].name} 的内容: {len(tag_contents)} 个")
        
        return True
        
    except Exception as e:
        print(f"❌ 内容标签关联测试失败: {e}")
        return False
    finally:
        db.close()


def test_content_publish():
    """测试内容发布功能"""
    print("📢 测试内容发布功能...")
    
    db = SessionLocal()
    try:
        # 获取一个测试内容
        contents = content_crud.get_multi(db, 0, 5)
        if not contents:
            print("⚠️  需要先有内容数据")
            return False
        
        content = contents[0]
        
        # 发布内容
        published_content = content_crud.publish_content(
            db, content.id, "测试公开标题", "这是一个测试的公开描述"
        )
        
        if published_content:
            print(f"✅ 内容 {content.id} 发布成功")
            print(f"   公开标题: {published_content.public_title}")
            print(f"   发布时间: {published_content.published_at}")
        
        # 测试获取公开内容
        public_contents = content_crud.get_public_contents(db, 0, 10)
        print(f"✅ 获取公开内容: {len(public_contents)} 个")
        
        # 测试搜索公开内容
        search_results = content_crud.search_public_contents(db, "测试", 0, 10)
        print(f"✅ 搜索公开内容 '测试': {len(search_results)} 个结果")
        
        # 取消发布
        unpublished_content = content_crud.unpublish_content(db, content.id)
        if unpublished_content:
            print(f"✅ 内容 {content.id} 取消发布成功")
        
        return True
        
    except Exception as e:
        print(f"❌ 内容发布测试失败: {e}")
        return False
    finally:
        db.close()


async def test_tag_generation():
    """测试AI标签生成功能"""
    print("🤖 测试AI标签生成功能...")
    
    db = SessionLocal()
    try:
        # 测试文本标签生成
        test_text = """
        线性代数是数学的一个分支，它研究向量、向量空间、线性变换和有限维线性方程组。
        向量空间是现代数学的中心主题；因此，线性代数被广泛地应用于抽象代数和泛函分析中。
        """
        
        result = tag_generation_service.generate_tags_for_text(db, test_text)
        
        if result.get("success"):
            print("✅ AI标签生成成功")
            print(f"   使用现有标签: {result.get('existing_tags', [])}")
            print(f"   创建新标签: {result.get('new_tags', [])}")
            print(f"   生成的标签ID: {result.get('tag_ids', [])}")
        else:
            print(f"⚠️  AI标签生成失败: {result.get('error', '未知错误')}")
        
        return result.get("success", False)
        
    except Exception as e:
        print(f"❌ AI标签生成测试失败: {e}")
        return False
    finally:
        db.close()


def test_tag_statistics():
    """测试标签统计功能"""
    print("📊 测试标签统计功能...")
    
    db = SessionLocal()
    try:
        # 获取标签及内容数量
        tags_with_count = tag_crud.get_tags_with_content_count(db, 0, 10)
        print(f"✅ 标签统计: {len(tags_with_count)} 个标签")
        
        for tag_data in tags_with_count[:5]:
            print(f"   {tag_data['name']}: {tag_data['content_count']} 个内容")
        
        # 获取热门标签
        popular_tags = tag_crud.get_popular_tags(db, 5)
        print(f"✅ 热门标签: {len(popular_tags)} 个")
        
        for tag_data in popular_tags:
            print(f"   {tag_data['name']}: {tag_data['content_count']} 个公开内容")
        
        return True
        
    except Exception as e:
        print(f"❌ 标签统计测试失败: {e}")
        return False
    finally:
        db.close()


async def main():
    """主测试函数"""
    print("🚀 开始社群功能测试")
    print("=" * 50)
    
    # 检查数据库连接
    try:
        from app.db.base import engine
        with engine.connect() as conn:
            print("✅ 数据库连接正常")
    except Exception as e:
        print(f"❌ 数据库连接失败: {e}")
        return
    
    # 运行测试
    tests = [
        ("标签CRUD", test_tag_crud),
        ("内容标签关联", test_content_tag_crud),
        ("内容发布", test_content_publish),
        ("AI标签生成", test_tag_generation),
        ("标签统计", test_tag_statistics),
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n📋 运行测试: {test_name}")
        print("-" * 30)
        
        try:
            if asyncio.iscoroutinefunction(test_func):
                result = await test_func()
            else:
                result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ 测试 {test_name} 异常: {e}")
            results.append((test_name, False))
    
    # 输出测试结果
    print("\n" + "=" * 50)
    print("📊 测试结果汇总")
    print("=" * 50)
    
    passed = 0
    for test_name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\n总计: {passed}/{len(results)} 个测试通过")
    
    if passed == len(results):
        print("🎉 所有测试通过！社群功能基本可用。")
    else:
        print("⚠️  部分测试失败，请检查相关功能。")


if __name__ == "__main__":
    asyncio.run(main())
