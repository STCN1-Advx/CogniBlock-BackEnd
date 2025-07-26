# Scripts 目录

这个目录包含了CogniBlock项目的各种实用脚本。

## 🗄️ 数据库管理

- **`create_tables.py`** - 创建数据库表
  ```bash
  python scripts/create_tables.py
  ```

- **`reset_database.py`** - 重置数据库（删除所有表并重新创建）
  ```bash
  python scripts/reset_database.py
  ```

- **`setup_test_db.py`** - 设置测试数据库
  ```bash
  python scripts/setup_test_db.py
  ```

## 🧪 功能测试

- **`test_uuid_user.py`** - 测试UUID用户功能
  ```bash
  python scripts/test_uuid_user.py
  ```

- **`test_oauth.py`** - OAuth功能测试（启动服务器并打开测试页面）
  ```bash
  python scripts/test_oauth.py
  ```

- **`create_test_user.py`** - 创建测试用户
  ```bash
  python scripts/create_test_user.py
  ```

## 🏷️ 社群功能

- **`setup_community_features.py`** - 初始化社群功能和标签系统
  ```bash
  python scripts/setup_community_features.py
  ```

- **`test_community_features.py`** - 测试社群功能
  ```bash
  python scripts/test_community_features.py
  ```

- **`test_smart_note_with_tags.py`** - 测试智能笔记和标签功能
  ```bash
  python scripts/test_smart_note_with_tags.py
  ```

## 使用说明

所有脚本都应该从项目根目录运行，脚本会自动处理导入路径。

### 快速开始

1. **初始化数据库**：
   ```bash
   python scripts/reset_database.py
   ```

2. **设置社群功能**：
   ```bash
   python scripts/setup_community_features.py
   ```

3. **测试核心功能**：
   ```bash
   python scripts/test_uuid_user.py
   python scripts/test_oauth.py
   ```

## 注意事项

- 确保PostgreSQL数据库正在运行
- 确保已安装所有依赖：`pip install -r requirements.txt`
- 确保环境变量配置正确（参考`.env.example`）