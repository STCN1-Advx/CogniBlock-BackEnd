# CogniBlock Backend

CogniBlock后端API服务，基于FastAPI + PostgreSQL构建，提供画布管理和用户认证功能。

## 功能特性

- FastAPI框架，支持自动API文档生成
- PostgreSQL数据库，使用UUID作为主键
- OAuth用户认证
- 画布(Canvas)管理系统
- 卡片(Card)和内容(Content)管理
- RESTful API设计
- 完整的测试套件
- 标准化的项目结构
- 实用脚本集合

## 项目结构

```
CogniBlock-BackEnd/
├── app/
│   ├── api/
│   │   └── v2/
│   │       ├── endpoints/
│   │       │   ├── auth.py      # 认证相关API
│   │       │   ├── users.py     # 用户管理API
│   │       │   └── canva.py     # 画布管理API
│   │       └── __init__.py
│   ├── core/
│   │   └── config.py            # 配置管理
│   ├── crud/
│   │   ├── user.py              # 用户CRUD操作
│   │   ├── canvas.py            # 画布CRUD操作
│   │   ├── card.py              # 卡片CRUD操作
│   │   └── content.py           # 内容CRUD操作
│   ├── db/
│   │   ├── base.py              # 数据库基础配置
│   │   └── session.py           # 数据库会话管理
│   ├── models/
│   │   ├── user.py              # 用户数据模型
│   │   ├── canvas.py            # 画布数据模型
│   │   ├── card.py              # 卡片数据模型
│   │   ├── content.py           # 内容数据模型
│   │   └── user_content.py      # 用户内容关联模型
│   ├── schemas/
│   │   ├── user.py              # 用户Pydantic模型
│   │   └── canva.py             # 画布Pydantic模型
│   ├── services/
│   │   ├── canva_service.py     # 画布业务逻辑
│   │   └── ocr_service.py       # OCR服务
│   ├── utils/
│   │   ├── image_processing.py  # 图像处理工具
│   │   └── markdown_utils.py    # Markdown工具
│   └── main.py                  # FastAPI应用入口
├── tests/                       # 测试套件
│   ├── unit/                    # 单元测试
│   │   ├── models/              # 模型测试
│   │   ├── crud/                # CRUD测试
│   │   └── services/            # 服务测试
│   ├── integration/             # 集成测试
│   ├── api/                     # API测试
│   ├── utils/                   # 测试工具
│   ├── conftest.py              # pytest配置
│   └── run_tests.py             # 测试运行器
├── scripts/                     # 实用脚本
│   ├── README.md                # 脚本说明文档
│   ├── create_tables.py         # 创建数据库表
│   ├── reset_database.py        # 重置数据库
│   ├── test_uuid_user.py        # UUID用户功能测试
│   └── test_oauth.py            # OAuth功能测试
├── static/                      # 静态文件
│   ├── oauth_test.html          # OAuth测试页面
│   └── ocr_test.html            # OCR测试页面
├── alembic/                     # 数据库迁移文件
├── .env.example                 # 环境变量示例
├── requirements.txt             # Python依赖
├── alembic.ini                  # Alembic配置
├── reset_db.py                  # 数据库重置工具
└── main.py                      # 应用启动脚本
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
# 快速重置数据库（推荐用于开发）
python scripts/reset_database.py

# 或者只创建表
python scripts/create_tables.py
```

### 5. 运行测试

```bash
# 快速检查（推荐）
python tests/run_tests.py --type quick

# 运行所有测试
python tests/run_tests.py --type all

# 运行特定类型的测试
python tests/run_tests.py --type unit      # 单元测试
python tests/run_tests.py --type api       # API测试
python tests/run_tests.py --type integration  # 集成测试

# 使用pytest直接运行
python -m pytest tests/ -v
```

### 6. 启动服务

```bash
python main.py
```

### 7. 访问API文档

启动后访问：
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 实用脚本

项目包含多个实用脚本，位于 `scripts/` 目录：

- **`reset_database.py`** - 重置数据库（删除所有表并重新创建）
- **`create_tables.py`** - 创建数据库表
- **`test_uuid_user.py`** - 测试UUID用户功能
- **`test_oauth.py`** - OAuth功能测试

详细说明请查看 [scripts/README.md](scripts/README.md)

## 测试套件

项目包含完整的测试套件，按功能分类组织：

### 测试结构
- **`tests/unit/`** - 单元测试
  - `models/` - 数据模型测试
  - `crud/` - CRUD操作测试  
  - `services/` - 业务逻辑测试
- **`tests/integration/`** - 集成测试
- **`tests/api/`** - API端点测试
- **`tests/utils/`** - 测试工具和辅助脚本

### 测试工具
- **`tests/run_tests.py`** - 统一测试运行器
- **`tests/utils/basic_test.py`** - 基础功能快速检查
- **`tests/utils/start_check.py`** - 项目启动检查
- **`tests/conftest.py`** - pytest配置文件

### 运行测试
```bash
# 快速检查项目状态
python tests/utils/start_check.py

# 运行基础测试
python tests/utils/basic_test.py

# 使用统一测试运行器
python tests/run_tests.py --type [quick|unit|api|integration|all]
```

## API版本

当前API版本：v2
- 基础路径：`/api/v2`
- 认证端点：`/api/v2/auth`
- 用户端点：`/api/v2/users`
- 画布端点：`/api/v2/canva`

## 数据库模型

### User表

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键，UUID格式 |
| oauth_id | String | OAuth提供商的用户ID |
| name | String | 用户显示名称 |
| email | String | 用户邮箱地址 |
| avatar | Text | 用户头像URL |
| created_at | DateTime | 创建时间 |
| updated_at | DateTime | 更新时间 |

### Canvas表

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键，UUID格式 |
| title | String | 画布标题 |
| description | Text | 画布描述 |
| user_id | UUID | 创建者用户ID |
| is_public | Boolean | 是否公开 |
| created_at | DateTime | 创建时间 |
| updated_at | DateTime | 更新时间 |

### Card表

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键，UUID格式 |
| canvas_id | UUID | 所属画布ID |
| title | String | 卡片标题 |
| position_x | Float | X坐标位置 |
| position_y | Float | Y坐标位置 |
| width | Float | 卡片宽度 |
| height | Float | 卡片高度 |
| created_at | DateTime | 创建时间 |
| updated_at | DateTime | 更新时间 |

### Content表

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键，UUID格式 |
| card_id | UUID | 所属卡片ID |
| content_type | String | 内容类型 |
| content_data | JSON | 内容数据 |
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

### 用户认证系统
- ✅ PostgreSQL数据库集成
- ✅ 用户表模型（id、oauth_id、name、email、avatar）
- ✅ Casdoor OAuth认证
- ✅ JWT token解析
- ✅ 用户自动创建/更新

### 画布管理系统
- ✅ 画布(Canvas)数据模型和CRUD操作
- ✅ 卡片(Card)数据模型和CRUD操作
- ✅ 内容(Content)数据模型和CRUD操作
- ✅ 画布权限验证和业务逻辑
- ✅ RESTful API端点
- ✅ 数据验证和错误处理

### 开发工具
- ✅ 完整的测试套件
- ✅ 数据库管理工具
- ✅ API文档和测试页面

## 📝 API端点

### 认证相关
- `GET /api/v2/auth/login` - 重定向到OAuth登录页面
- `GET /api/v2/auth/oauth/callback` - OAuth回调处理（自动创建/更新用户）
- `POST /api/v2/auth/logout` - 登出

### 用户相关
- `GET /api/v2/users/{user_id}` - 获取用户信息

### 画布相关
- `GET /api/v2/canva/` - 获取用户画布列表
- `POST /api/v2/canva/` - 创建新画布
- `GET /api/v2/canva/{canvas_id}` - 获取画布详情
- `PUT /api/v2/canva/{canvas_id}` - 更新画布信息
- `DELETE /api/v2/canva/{canvas_id}` - 删除画布
- `POST /api/v2/canva/{canvas_id}/cards` - 在画布中创建卡片
- `PUT /api/v2/canva/cards/{card_id}` - 更新卡片信息
- `DELETE /api/v2/canva/cards/{card_id}` - 删除卡片
- `POST /api/v2/canva/cards/{card_id}/content` - 为卡片添加内容
- `PUT /api/v2/canva/content/{content_id}` - 更新内容
- `DELETE /api/v2/canva/content/{content_id}` - 删除内容

### 系统相关
- `GET /` - API根路径
- `GET /health` - 健康检查
- `GET /docs` - API文档（Swagger UI）
- `GET /static/oauth_test.html` - OAuth测试页面

## 🔧 开发说明

项目采用标准的FastAPI架构，包含完整的画布管理功能和用户认证系统。主要特点：

- **模块化设计**：清晰的分层架构，便于维护和扩展
- **完整的CRUD操作**：支持画布、卡片、内容的完整生命周期管理
- **权限控制**：基于用户的画布访问权限验证
- **数据验证**：使用Pydantic进行严格的数据验证
- **测试覆盖**：包含单元测试、集成测试和API测试
- **开发工具**：提供数据库管理、测试运行等实用工具

### 开发流程
1. 使用 `python tests/utils/start_check.py` 检查项目状态
2. 使用 `python reset_db.py` 管理数据库
3. 使用 `python tests/run_tests.py` 运行测试
4. 使用 `python main.py` 启动开发服务器
