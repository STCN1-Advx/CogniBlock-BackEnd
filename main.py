#!/usr/bin/env python3
"""
CogniBlock Backend - 黑客松 MVP 版本
简单的热重载启动文件
"""

import uvicorn
import os

def main():
    """启动服务器"""
    # 基本配置
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 8000))
    
    print("🚀 CogniBlock Backend 启动中...")
    print(f"📍 服务地址: http://{host}:{port}")
    print(f"📖 API 文档: http://{host}:{port}/docs")
    print("🔄 热重载已启用")
    print("=" * 50)
    
    # 启动服务器
    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=True,
        reload_dirs=["app", "static"],
        reload_includes=["*.py", "*.html", "*.css", "*.js"],
        log_level="info"
    )

if __name__ == "__main__":
    main()