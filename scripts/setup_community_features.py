#!/usr/bin/env python3
"""
社群功能设置脚本
用于初始化社群功能相关的数据库表和基础数据
"""

import sys
import os
import asyncio
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.session import SessionLocal
from app.db.base import Base, engine
from app.crud.tag import tag as tag_crud
from app.models.tag import Tag
from app.models.content_tag import ContentTag


def create_tables():
    """创建数据库表"""
    print("📊 创建数据库表...")
    
    try:
        # 创建所有表
        Base.metadata.create_all(bind=engine)
        print("✅ 数据库表创建成功")
        return True
    except Exception as e:
        print(f"❌ 数据库表创建失败: {e}")
        return False


def create_default_tags():
    """创建默认标签"""
    print("🏷️  创建默认标签...")
    
    db = SessionLocal()
    try:
        # 定义默认标签
        default_tags = [
            # 学科分类
            ("数学", "数学相关内容，包括代数、几何、微积分等"),
            ("物理", "物理学相关内容，包括力学、电磁学、量子物理等"),
            ("化学", "化学相关内容，包括有机化学、无机化学、物理化学等"),
            ("生物", "生物学相关内容，包括分子生物学、生态学、遗传学等"),
            ("计算机科学", "计算机科学相关内容，包括算法、数据结构、软件工程等"),
            
            # 编程相关
            ("编程", "编程和软件开发相关内容"),
            ("Python", "Python编程语言相关内容"),
            ("JavaScript", "JavaScript编程语言相关内容"),
            ("机器学习", "机器学习和人工智能相关内容"),
            ("数据科学", "数据分析和数据科学相关内容"),
            
            # 工程技术
            ("工程", "工程技术相关内容"),
            ("电子工程", "电子工程和电路设计相关内容"),
            ("机械工程", "机械工程和制造相关内容"),
            ("软件工程", "软件工程和项目管理相关内容"),
            
            # 商业管理
            ("商业", "商业和管理相关内容"),
            ("经济学", "经济学理论和应用相关内容"),
            ("管理学", "管理理论和实践相关内容"),
            ("市场营销", "市场营销和品牌管理相关内容"),
            
            # 人文社科
            ("历史", "历史学相关内容"),
            ("哲学", "哲学思想和理论相关内容"),
            ("心理学", "心理学理论和应用相关内容"),
            ("社会学", "社会学理论和社会现象分析相关内容"),
            
            # 语言文学
            ("语言学", "语言学理论和语言学习相关内容"),
            ("文学", "文学作品和文学理论相关内容"),
            ("英语", "英语学习和英语文学相关内容"),
            ("中文", "中文学习和中国文学相关内容"),
            
            # 艺术设计
            ("艺术", "艺术理论和艺术作品相关内容"),
            ("设计", "设计理论和设计实践相关内容"),
            ("音乐", "音乐理论和音乐作品相关内容"),
            ("美术", "美术理论和美术作品相关内容"),
            
            # 学习方法
            ("学习方法", "学习技巧和学习策略相关内容"),
            ("笔记整理", "笔记记录和整理方法相关内容"),
            ("考试准备", "考试复习和应试技巧相关内容"),
            ("研究方法", "学术研究方法和论文写作相关内容"),
            
            # 通用标签
            ("基础知识", "基础概念和入门知识相关内容"),
            ("进阶内容", "深入和高级内容"),
            ("实践应用", "实际应用和案例分析相关内容"),
            ("理论研究", "理论分析和学术研究相关内容"),
        ]
        
        created_count = 0
        for tag_name, tag_description in default_tags:
            # 检查标签是否已存在
            existing_tag = tag_crud.get_by_name(db, tag_name)
            if not existing_tag:
                tag_crud.create(db, tag_name, tag_description)
                created_count += 1
                print(f"   ✅ 创建标签: {tag_name}")
            else:
                print(f"   ⏭️  标签已存在: {tag_name}")
        
        print(f"✅ 默认标签创建完成，新增 {created_count} 个标签")
        return True
        
    except Exception as e:
        print(f"❌ 创建默认标签失败: {e}")
        return False
    finally:
        db.close()


def verify_setup():
    """验证设置是否成功"""
    print("🔍 验证设置...")
    
    db = SessionLocal()
    try:
        # 检查标签表
        tags = tag_crud.get_multi(db, 0, 100)
        print(f"✅ 标签表: {len(tags)} 个标签")
        
        # 检查表结构
        from sqlalchemy import inspect
        inspector = inspect(engine)
        
        # 检查tags表
        if 'tags' in inspector.get_table_names():
            print("✅ tags表存在")
        else:
            print("❌ tags表不存在")
            return False
        
        # 检查content_tags表
        if 'content_tags' in inspector.get_table_names():
            print("✅ content_tags表存在")
        else:
            print("❌ content_tags表不存在")
            return False
        
        # 检查contents表的新字段
        contents_columns = [col['name'] for col in inspector.get_columns('contents')]
        required_columns = ['is_public', 'public_title', 'public_description', 'published_at']
        
        missing_columns = [col for col in required_columns if col not in contents_columns]
        if missing_columns:
            print(f"❌ contents表缺少字段: {missing_columns}")
            return False
        else:
            print("✅ contents表字段完整")
        
        print("✅ 设置验证通过")
        return True
        
    except Exception as e:
        print(f"❌ 验证设置失败: {e}")
        return False
    finally:
        db.close()


def check_dependencies():
    """检查依赖"""
    print("📦 检查依赖...")
    
    try:
        # 检查数据库连接
        with engine.connect() as conn:
            print("✅ 数据库连接正常")
        
        # 检查必要的模块
        required_modules = [
            'app.models.tag',
            'app.models.content_tag',
            'app.crud.tag',
            'app.crud.content_tag',
            'app.services.tag_generation_service',
        ]
        
        for module_name in required_modules:
            try:
                __import__(module_name)
                print(f"✅ 模块 {module_name} 可用")
            except ImportError as e:
                print(f"❌ 模块 {module_name} 不可用: {e}")
                return False
        
        return True
        
    except Exception as e:
        print(f"❌ 依赖检查失败: {e}")
        return False


def main():
    """主函数"""
    print("🚀 开始设置社群功能")
    print("=" * 50)
    
    # 检查依赖
    if not check_dependencies():
        print("❌ 依赖检查失败，请先解决依赖问题")
        return False
    
    # 创建数据库表
    if not create_tables():
        print("❌ 数据库表创建失败")
        return False
    
    # 创建默认标签
    if not create_default_tags():
        print("❌ 默认标签创建失败")
        return False
    
    # 验证设置
    if not verify_setup():
        print("❌ 设置验证失败")
        return False
    
    print("\n" + "=" * 50)
    print("🎉 社群功能设置完成！")
    print("\n📋 后续步骤:")
    print("1. 运行测试脚本验证功能: python scripts/test_community_features.py")
    print("2. 启动后端服务: python main.py")
    print("3. 在前端集成社群功能API")
    print("\n📖 更多信息请参考: docs/community-feature-implementation.md")
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
