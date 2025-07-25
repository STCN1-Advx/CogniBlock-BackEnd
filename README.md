# CogniBlock Backend

CogniBlock后端API服务，基于FastAPI + PostgreSQL构建。

## 功能特性

- FastAPI框架，支持自动API文档生成
- PostgreSQL数据库
- OAuth用户认证
- RESTful API设计
- 数据库迁移管理（Alembic）
- 标准化的项目结构

## 项目结构

```
CogniBlock-BackEnd/
├── app/
│   ├── api/
│   │   └── v2/
│   │       ├── endpoints/
│   │       │   ├── auth.py      # 认证相关API
│   │       │   └── users.py     # 用户管理API
│   │       └── __init__.py
│   ├── core/
│   │   └── config.py            # 配置管理
│   ├── crud/
│   │   └── user.py              # 用户CRUD操作
│   ├── db/
│   │   ├── base.py              # 数据库基础配置
│   │   └── session.py           # 数据库会话管理
│   ├── models/
│   │   └── user.py              # 用户数据模型
│   ├── schemas/
│   │   └── user.py              # Pydantic模型
│   └── main.py                  # FastAPI应用入口
├── alembic/                     # 数据库迁移文件
├── .env                         # 环境变量配置
├── requirements.txt             # Python依赖
├── alembic.ini                  # Alembic配置
└── run.py                       # 应用启动脚本
```

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

复制并编辑 `.env` 文件，配置数据库连接和其他设置。

### 3. 初始化数据库

```bash
# 初始化Alembic
alembic init alembic

# 创建初始迁移
alembic revision --autogenerate -m "Create users table"

# 执行迁移
alembic upgrade head
```

### 4. 启动服务

```bash
python run.py
```

或使用uvicorn直接启动：

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 5. 访问API文档

启动后访问：
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## API版本

当前API版本：v2
- 基础路径：`/api/v2`
- 认证端点：`/api/v2/auth`
- 用户端点：`/api/v2/users`

## 数据库模型

### User表

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer | 主键，自增 |
| oauth_id | String | OAuth提供商的用户ID |
| name | String | 用户显示名称 |
| email | String | 用户邮箱地址 |
| avatar | Text | 用户头像URL |
| created_at | DateTime | 创建时间 |
| updated_at | DateTime | 更新时间 |

## 🧪 OAuth测试

### 快速测试
```bash
python test_oauth.py
```

这会自动启动服务器并打开测试页面。

### 手动测试
1. 启动服务器：
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

2. 打开测试页面：http://localhost:8000/static/oauth_test.html

3. 点击"开始 OAuth 登录"按钮

4. 在Casdoor页面完成登录

5. 登录成功后会自动回调并显示用户信息

### OAuth配置
- **Provider**: Casdoor (auth.smart-teach.cn)
- **Client ID**: 6692de80065402b4a9ec
- **回调地址**: http://localhost:8000/api/v2/auth/oauth/callback

## 🎯 已完成功能

- ✅ PostgreSQL数据库集成
- ✅ 用户表模型（id、oauth_id、name、email、avatar）
- ✅ Casdoor OAuth认证
- ✅ JWT token解析
- ✅ 用户自动创建/更新
- ✅ 简化的API端点
- ✅ 测试页面

## 📝 API端点

### 认证相关
- `GET /api/v2/auth/login` - 重定向到OAuth登录页面
- `GET /api/v2/auth/oauth/callback` - OAuth回调处理（自动创建/更新用户）
- `POST /api/v2/auth/logout` - 登出

### 用户相关
- `GET /api/v2/users/{user_id}` - 获取用户信息

### 系统相关
- `GET /` - API根路径
- `GET /health` - 健康检查
- `GET /docs` - API文档（Swagger UI）
- `GET /static/oauth_test.html` - OAuth测试页面

## 🔧 开发说明

项目采用简化的MVP架构，专注于核心OAuth功能。所有复杂的管理功能都已移除，只保留必要的用户认证和基本信息管理。
