# CogniBlock Backend

🧠 CogniBlock 是一个智能知识管理平台的后端服务，基于 FastAPI + PostgreSQL 构建，提供画布管理、智能笔记生成、OCR识别和社群功能。

<img width="2560" height="1440" alt="banner" src="https://github.com/user-attachments/assets/efe4bf2d-0c6e-4532-abe3-583271b22b59" />

## ✨ 功能特性

- 🎨 **画布管理** - 可视化知识组织，支持卡片和内容管理
- 🤖 **智能笔记** - AI驱动的笔记总结和知识提取
- 📷 **OCR识别** - 图片文字识别和内容提取
- 🏷️ **标签系统** - 自动标签生成和内容分类
- 👥 **社群功能** - 内容分享和协作
- 🔐 **OAuth认证** - 安全的用户认证系统
- 📊 **知识库** - 结构化知识存储和检索

## 🚀 快速开始

### 环境要求

- Python 3.8+
- PostgreSQL 12+

### 安装步骤

1. **克隆项目**
   ```bash
   git clone https://github.com/STCN1-Advx/CogniBlock-BackEnd.git
   cd CogniBlock-BackEnd
   ```

2. **安装依赖**
   ```bash
   pip install -r requirements.txt
   ```

3. **配置环境变量**
   ```bash
   cp .env.example .env
   # 编辑 .env 文件，配置数据库连接等信息
   ```

4. **初始化数据库**
   ```bash
   # 创建数据库表
   python scripts/create_tables.py
   
   # 或者重置数据库（开发环境）
   python scripts/reset_database.py
   ```

5. **启动服务**
   ```bash
   python main.py
   ```

6. **访问API文档**
   - Swagger UI: http://localhost:8000/docs
   - ReDoc: http://localhost:8000/redoc

## 📁 项目结构

```
CogniBlock-BackEnd/
├── app/                    # 应用核心代码
│   ├── api/               # API路由
│   ├── core/              # 核心配置
│   ├── crud/              # 数据库操作
│   ├── db/                # 数据库配置
│   ├── models/            # 数据模型
│   ├── schemas/           # API数据模式
│   ├── services/          # 业务逻辑
│   └── utils/             # 工具函数
├── scripts/               # 实用脚本
├── tests/                 # 测试套件
├── static/                # 静态文件
├── prompts/               # AI提示词
└── alembic/               # 数据库迁移
├── .env.example                 # 环境变量示例
├── requirements.txt             # Python依赖
├── alembic.ini                  # Alembic配置
└── main.py                      # 应用启动脚本
```

## 🔧 开发工具

项目提供了丰富的开发工具脚本：

```bash
# 数据库管理
python scripts/create_tables.py      # 创建数据库表
python scripts/reset_database.py     # 重置数据库
python scripts/setup_test_db.py      # 设置测试数据库

# 功能测试
python scripts/test_oauth.py         # OAuth功能测试
python scripts/test_uuid_user.py     # 用户功能测试

# 社群功能
python scripts/setup_community_features.py    # 初始化社群功能
python scripts/test_community_features.py     # 社群功能测试
python scripts/test_smart_note_with_tags.py   # 智能笔记测试
```

## 🧪 测试

```bash
# 运行所有测试
python tests/run_tests.py --type all

# 运行特定类型测试
python tests/run_tests.py --type unit         # 单元测试
python tests/run_tests.py --type api          # API测试
python tests/run_tests.py --type integration  # 集成测试

# 快速检查
python tests/run_tests.py --type quick
```

## 📚 API文档

### 核心端点

#### 认证相关
- `GET /api/v2/auth/login` - OAuth登录
- `GET /api/v2/auth/oauth/callback` - OAuth回调
- `POST /api/v2/auth/logout` - 登出

#### 画布管理
- `GET /api/v2/canva/` - 获取画布列表
- `POST /api/v2/canva/` - 创建画布
- `GET /api/v2/canva/{canvas_id}` - 获取画布详情
- `PUT /api/v2/canva/{canvas_id}` - 更新画布
- `DELETE /api/v2/canva/{canvas_id}` - 删除画布

#### 智能笔记
- `POST /api/v2/note-summary/create` - 创建总结任务
- `GET /api/v2/note-summary/task/{task_id}` - 获取任务状态
- `GET /api/v2/note-summary/tasks` - 获取任务列表

#### OCR识别
- `POST /api/v2/ocr/recognize` - 图片文字识别
- `POST /api/v2/ocr/batch` - 批量识别

## 🗄️ 数据模型

### 核心实体

- **User** - 用户信息（UUID主键，OAuth集成）
- **Canvas** - 画布（标题、描述、权限）
- **Card** - 卡片（位置、尺寸、内容关联）
- **Content** - 内容（文本、图片、类型）
- **Tag** - 标签（分类、描述）
- **Article** - 文章（知识库条目）

## 🔗 相关链接

- [前端仓库](https://github.com/STCN1-Advx/CogniBlock-FrontEnd)

## 📄 许可证

本项目采用 GPL-3.0 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

---

<div align="center">
  <p>用 ❤️ 构建，为了更好的知识管理体验</p>
</div>
