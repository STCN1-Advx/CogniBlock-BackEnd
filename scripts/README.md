# Scripts 目录

这个目录包含了CogniBlock项目的各种实用脚本。

## 脚本说明

### 数据库相关

- **`create_tables.py`** - 创建数据库表
  ```bash
  python scripts/create_tables.py
  ```

- **`reset_database.py`** - 重置数据库（删除所有表并重新创建）
  ```bash
  python scripts/reset_database.py
  ```

### 测试相关

- **`test_uuid_user.py`** - 测试UUID用户功能
  ```bash
  python scripts/test_uuid_user.py
  ```

- **`test_oauth.py`** - OAuth功能测试（启动服务器并打开测试页面）
  ```bash
  python scripts/test_oauth.py
  ```

## 使用说明

所有脚本都应该从项目根目录运行，脚本会自动处理导入路径。

### 快速开始

1. 重置数据库：
   ```bash
   python scripts/reset_database.py
   ```

2. 测试UUID用户功能：
   ```bash
   python scripts/test_uuid_user.py
   ```

3. 启动OAuth测试：
   ```bash
   python scripts/test_oauth.py
   ```

## 注意事项

- 确保PostgreSQL数据库正在运行
- 确保已安装所有依赖：`pip install -r requirements.txt`
- 确保环境变量配置正确（参考`.env.example`）