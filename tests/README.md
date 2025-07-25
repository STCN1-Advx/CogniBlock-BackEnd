# CogniBlock 测试套件说明

## 测试结构概览

```
tests/
├── __init__.py                 # 测试包初始化
├── conftest.py                 # pytest配置文件
├── run_tests.py                # 统一测试运行器
├── unit/                       # 单元测试
│   ├── __init__.py
│   ├── models/                 # 数据模型测试
│   │   ├── __init__.py
│   │   ├── test_models.py      # 完整模型测试
│   │   └── test_models_simple.py  # 简化模型测试
│   ├── crud/                   # CRUD操作测试
│   │   ├── __init__.py
│   │   ├── test_crud.py        # CRUD单元测试
│   │   └── test_crud_operations.py  # CRUD操作测试
│   ├── services/               # 服务层测试
│   │   ├── __init__.py
│   │   └── test_canva_service_alt.py  # 画布服务测试
│   └── test_canva_schemas.py   # 数据模式测试
├── integration/                # 集成测试
│   ├── __init__.py
│   └── test_auth_middleware.py # 认证中间件集成测试
├── api/                        # API测试
│   ├── __init__.py
│   ├── test_canva_api.py       # 画布API测试
│   └── test_canva_endpoints.py # API端点测试
└── utils/                      # 测试工具
    ├── __init__.py
    ├── basic_test.py           # 基础功能测试
    ├── simple_test.py          # 简单测试脚本
    ├── quick_test.py           # 快速测试
    ├── start_check.py          # 启动检查
    ├── run_tests.py            # 测试运行器（旧版）
    └── run_all_tests.py        # 完整测试运行器
```

## 测试类型说明

### 1. 单元测试 (unit/)
测试单个组件的功能，不依赖外部系统。

- **models/**: 测试数据模型的定义、验证和关系
- **crud/**: 测试数据库操作的正确性
- **services/**: 测试业务逻辑的实现

### 2. 集成测试 (integration/)
测试多个组件之间的交互。

- **test_auth_middleware.py**: 测试认证中间件与其他组件的集成

### 3. API测试 (api/)
测试HTTP API端点的功能。

- **test_canva_api.py**: 测试画布相关API
- **test_canva_endpoints.py**: 测试具体的API端点

### 4. 测试工具 (utils/)
提供测试辅助功能和快速检查。

- **basic_test.py**: 基础功能快速验证
- **start_check.py**: 项目启动状态检查
- **run_all_tests.py**: 完整测试套件运行器

## 运行测试

### 使用统一测试运行器
```bash
# 快速检查（推荐）
python tests/run_tests.py --type quick

# 运行所有测试
python tests/run_tests.py --type all

# 运行特定类型测试
python tests/run_tests.py --type unit
python tests/run_tests.py --type integration
python tests/run_tests.py --type api
```

### 使用pytest直接运行
```bash
# 运行所有测试
python -m pytest tests/ -v

# 运行特定目录的测试
python -m pytest tests/unit/ -v
python -m pytest tests/api/ -v

# 运行特定测试文件
python -m pytest tests/unit/models/test_models.py -v
```

### 使用测试工具
```bash
# 项目启动检查
python tests/utils/start_check.py

# 基础功能测试
python tests/utils/basic_test.py

# 快速测试
python tests/utils/quick_test.py
```

## 测试配置

### pytest配置 (conftest.py)
- 设置测试数据库连接
- 提供测试fixtures
- 配置测试环境

### 环境要求
- Python 3.8+
- PostgreSQL数据库
- 项目依赖包（见requirements.txt）

## 最佳实践

1. **运行顺序**: 建议先运行快速检查，再运行完整测试
2. **数据库**: 使用独立的测试数据库，避免影响开发数据
3. **隔离性**: 每个测试应该独立运行，不依赖其他测试的结果
4. **覆盖率**: 确保核心功能有充分的测试覆盖

## 故障排除

### 常见问题
1. **导入错误**: 确保项目根目录在Python路径中
2. **数据库连接**: 检查数据库配置和连接状态
3. **依赖缺失**: 运行 `pip install -r requirements.txt`

### 调试技巧
- 使用 `-v` 参数获得详细输出
- 使用 `--tb=short` 获得简化的错误信息
- 单独运行失败的测试文件进行调试