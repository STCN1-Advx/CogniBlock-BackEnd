# 社群功能后端设计文档

## 功能概述

社群功能允许用户将自己的知识库内容公开分享，其他用户可以通过标签浏览和使用这些公开的内容。

### 核心功能
1. **AI自动标签生成**: 在生成content后自动为内容打标签
2. **内容公开机制**: 用户可以将自己的content设为公开
3. **标签浏览**: 用户可以浏览所有标签并查看对应的公开内容
4. **权限控制**: 确保只有登录用户可以访问content，公开内容对所有用户可见

## 数据库设计

### 1. Tags表
```sql
CREATE TABLE tags (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### 2. Content_Tags关联表
```sql
CREATE TABLE content_tags (
    id SERIAL PRIMARY KEY,
    content_id INTEGER REFERENCES contents(id) ON DELETE CASCADE,
    tag_id INTEGER REFERENCES tags(id) ON DELETE CASCADE,
    confidence FLOAT DEFAULT 1.0,  -- AI标签的置信度
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(content_id, tag_id)
);
```

### 3. Contents表扩展
需要在现有的contents表中添加以下字段：
```sql
ALTER TABLE contents ADD COLUMN is_public BOOLEAN DEFAULT FALSE;
ALTER TABLE contents ADD COLUMN public_title VARCHAR(255);
ALTER TABLE contents ADD COLUMN public_description TEXT;
ALTER TABLE contents ADD COLUMN published_at TIMESTAMP WITH TIME ZONE;
```

## API接口设计

### 1. 标签管理接口

#### GET /api/v2/community/tags
获取所有标签列表
```json
{
  "tags": [
    {
      "id": 1,
      "name": "数学",
      "description": "数学相关内容",
      "content_count": 15
    }
  ]
}
```

#### GET /api/v2/community/tags/{tag_id}/contents
根据标签获取公开内容
```json
{
  "contents": [
    {
      "id": 123,
      "public_title": "线性代数基础",
      "public_description": "线性代数的基本概念和运算",
      "preview": "内容预览...",
      "author": "用户名",
      "published_at": "2024-01-01T00:00:00Z",
      "tags": ["数学", "线性代数"]
    }
  ],
  "pagination": {
    "page": 1,
    "size": 20,
    "total": 100
  }
}
```

### 2. 内容公开接口

#### POST /api/v2/content/{content_id}/publish
将内容设为公开
```json
{
  "public_title": "线性代数基础",
  "public_description": "线性代数的基本概念和运算"
}
```

#### DELETE /api/v2/content/{content_id}/publish
取消内容公开

#### GET /api/v2/content/{content_id}/public
获取公开内容详情（无需登录）

### 3. 用户内容管理接口

#### GET /api/v2/user/contents/public
获取当前用户的公开内容列表

#### GET /api/v2/user/contents/{content_id}/tags
获取内容的标签

#### POST /api/v2/user/contents/{content_id}/tags
为内容添加标签

## AI标签生成流程

### 集成点
在现有的SmartNoteService中的`_save_to_database`方法后添加标签生成步骤：

1. **内容分析**: 分析生成的summary_content和knowledge_record
2. **标签匹配**: 使用AI模型匹配现有标签
3. **新标签生成**: 如果没有合适的现有标签，生成新标签
4. **标签关联**: 将标签与content关联

### AI提示词设计
```python
TAG_GENERATION_PROMPT = """
基于以下内容，为其生成3-5个最相关的标签。

内容摘要：{summary_content}
知识库记录：{knowledge_record}

现有标签列表：{existing_tags}

请按以下格式返回：
1. 优先从现有标签中选择最匹配的标签
2. 如果现有标签不够准确，可以生成新的标签
3. 标签应该简洁、准确、有代表性
4. 返回JSON格式：{"existing_tags": ["标签1", "标签2"], "new_tags": ["新标签1"]}
"""
```

## 权限控制机制

### 访问规则
1. **私有内容**: 只有内容所有者可以访问
2. **公开内容**: 所有登录用户可以访问
3. **标签浏览**: 所有登录用户可以浏览标签和公开内容列表
4. **内容管理**: 只有内容所有者可以设置公开/私有状态

### 实现方式
- 在现有的`check_user_access`基础上扩展
- 添加`check_public_access`方法
- 在API路由中添加相应的权限检查

## 实现优先级

1. **Phase 1**: 创建数据库表和基础模型
2. **Phase 2**: 实现AI标签生成功能
3. **Phase 3**: 实现内容公开功能和API
4. **Phase 4**: 实现社群浏览API
5. **Phase 5**: 前端集成和测试

## 技术考虑

### 性能优化
- 标签查询使用索引优化
- 公开内容列表使用分页
- 考虑添加缓存机制

### 安全考虑
- 防止恶意标签注入
- 内容审核机制（可选）
- 用户隐私保护

### 扩展性
- 标签层次结构（可选）
- 内容评分和推荐（可选）
- 用户关注和订阅（可选）
