# 社群功能实现文档

## 概述

本文档描述了CogniBlock社群功能的完整实现，包括AI自动标签生成、内容公开分享、标签浏览等核心功能。

## 功能特性

### 1. AI自动标签生成
- **智能标签匹配**: 优先使用现有标签，避免重复创建
- **新标签创建**: 当现有标签不匹配时，智能生成新标签
- **置信度评估**: 为AI生成的标签提供置信度评分
- **集成到工作流**: 自动在内容生成后进行标签生成

### 2. 内容公开分享
- **发布控制**: 用户可以选择将内容设为公开或私有
- **公开信息**: 支持自定义公开标题和描述
- **权限管理**: 只有内容所有者可以控制发布状态
- **发布时间**: 记录内容的发布时间

### 3. 社群浏览
- **标签浏览**: 按标签分类浏览公开内容
- **内容搜索**: 支持全文搜索公开内容
- **热门标签**: 显示最受欢迎的标签
- **最新内容**: 展示最近发布的内容

### 4. 标签管理
- **标签统计**: 显示每个标签关联的内容数量
- **标签搜索**: 支持按名称搜索标签
- **标签描述**: 为标签添加详细描述

## 技术架构

### 数据库设计

#### 新增表结构

1. **tags表**
```sql
CREATE TABLE tags (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

2. **content_tags表**
```sql
CREATE TABLE content_tags (
    id SERIAL PRIMARY KEY,
    content_id INTEGER REFERENCES contents(id) ON DELETE CASCADE,
    tag_id INTEGER REFERENCES tags(id) ON DELETE CASCADE,
    confidence FLOAT DEFAULT 1.0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(content_id, tag_id)
);
```

#### 扩展现有表

**contents表新增字段**:
- `is_public`: 是否公开
- `public_title`: 公开标题
- `public_description`: 公开描述
- `published_at`: 发布时间

### API接口

#### 社群浏览接口
- `GET /api/v2/community/tags` - 获取标签列表
- `GET /api/v2/community/tags/popular` - 获取热门标签
- `GET /api/v2/community/tags/{tag_id}/contents` - 获取标签下的内容
- `GET /api/v2/community/contents` - 获取公开内容列表
- `GET /api/v2/community/contents/{content_id}` - 获取公开内容详情
- `GET /api/v2/community/stats` - 获取社群统计信息

#### 内容发布接口
- `POST /api/v2/content/{content_id}/publish` - 发布内容
- `DELETE /api/v2/content/{content_id}/publish` - 取消发布
- `GET /api/v2/content/user/public` - 获取用户的公开内容

#### 标签管理接口
- `GET /api/v2/content/{content_id}/tags` - 获取内容标签
- `POST /api/v2/content/{content_id}/tags` - 添加内容标签
- `DELETE /api/v2/content/{content_id}/tags/{tag_id}` - 移除内容标签
- `POST /api/v2/community/generate-tags` - AI生成标签

### 核心服务

#### TagGenerationService
负责AI标签生成的核心服务：
- 使用Kimi-K2模型进行标签生成
- 智能匹配现有标签
- 生成新标签并评估置信度
- 集成到SmartNoteService工作流

#### CRUD操作
- **TagCRUD**: 标签的增删改查操作
- **ContentTagCRUD**: 内容标签关联的管理
- **ContentCRUD扩展**: 添加公开功能相关操作

## 部署说明

### 1. 数据库迁移
```bash
# 运行数据库迁移
alembic upgrade head
```

### 2. 环境变量配置
确保以下环境变量已配置：
```bash
# AI服务配置
PPINFRA_API_KEY=your_ppinfra_api_key
PPINFRA_BASE_URL=https://api.ppinfra.com/v3/openai
```

### 3. 测试验证
```bash
# 运行社群功能测试
python scripts/test_community_features.py
```

## 使用示例

### 前端集成

```typescript
import { CommunityAPI } from '@/lib/community-api';

// 获取标签列表
const tags = await CommunityAPI.getTags({ limit: 20 });

// 发布内容
await CommunityAPI.publishContent(contentId, {
  public_title: "我的学习笔记",
  public_description: "关于线性代数的学习总结"
});

// 生成标签
const result = await CommunityAPI.generateTags({
  content: "这是一篇关于机器学习的文章..."
});
```

### 后端使用

```python
from app.services.tag_generation_service import tag_generation_service
from app.crud.content import content as content_crud

# 生成标签
result = await tag_generation_service.generate_tags_for_content(db, content)

# 发布内容
published_content = content_crud.publish_content(
    db, content_id, "公开标题", "公开描述"
)
```

## 权限控制

### 访问权限
- **公开内容**: 所有登录用户可访问
- **私有内容**: 仅内容所有者可访问
- **内容管理**: 仅内容所有者可发布/取消发布
- **标签管理**: 仅内容所有者可为自己的内容添加/移除标签

### 安全考虑
- 防止恶意标签注入
- 内容审核机制（可选）
- 用户隐私保护
- API访问频率限制

## 性能优化

### 数据库优化
- 为标签名称添加唯一索引
- 为content_tags表添加复合索引
- 公开内容查询使用索引优化

### 缓存策略
- 热门标签缓存
- 公开内容列表缓存
- 标签统计信息缓存

### 分页支持
- 所有列表接口支持分页
- 合理的默认分页大小
- 总数统计优化

## 扩展功能

### 未来可能的扩展
1. **标签层次结构**: 支持父子标签关系
2. **内容评分**: 用户可以为公开内容评分
3. **用户关注**: 关注特定标签或用户
4. **内容推荐**: 基于用户兴趣推荐内容
5. **社群互动**: 评论、点赞等社交功能

### 集成建议
1. **搜索引擎**: 集成Elasticsearch提升搜索体验
2. **推荐系统**: 使用机器学习算法推荐相关内容
3. **内容审核**: 集成AI内容审核服务
4. **统计分析**: 添加详细的使用统计和分析

## 故障排除

### 常见问题
1. **标签生成失败**: 检查AI服务配置和网络连接
2. **权限错误**: 确认用户认证和权限设置
3. **数据库错误**: 检查数据库连接和表结构
4. **性能问题**: 检查索引和查询优化

### 日志监控
- 标签生成过程日志
- API访问日志
- 错误和异常日志
- 性能监控指标

## 总结

社群功能为CogniBlock平台增加了强大的内容分享和发现能力，通过AI自动标签生成和智能分类，用户可以轻松分享和发现有价值的学习内容。该功能的实现遵循了良好的软件工程实践，具有良好的扩展性和维护性。
