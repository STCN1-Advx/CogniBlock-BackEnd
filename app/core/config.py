import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    API_V2_STR = "/api/v2"
    PROJECT_NAME = "CogniBlock"

    # Database
    DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:LaoShui666!@localhost:5432/cogniblock")

    # Security
    SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-here")

    # CORS
    BACKEND_CORS_ORIGINS = [
        "http://localhost:3000", 
        "http://localhost:3001",  # 前端地址
        "http://127.0.0.1:3001",  # 前端地址
        "http://localhost:8080", 
        "http://localhost:5173",
        "http://localhost"
    ]

    # OAuth (Casdoor)
    OAUTH_CLIENT_ID = os.getenv("OAUTH_CLIENT_ID", "")
    OAUTH_CLIENT_SECRET = os.getenv("OAUTH_CLIENT_SECRET", "")
    OAUTH_REDIRECT_URI = os.getenv("OAUTH_REDIRECT_URI", "")
    OAUTH_AUTHORIZE_URL = os.getenv("OAUTH_AUTHORIZE_URL", "")
    OAUTH_TOKEN_URL = os.getenv("OAUTH_TOKEN_URL", "")
    OAUTH_USER_URL = os.getenv("OAUTH_USER_URL", "")

    # AI Configuration
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "")

    # 笔记总结配置
    NOTE_MIN_THRESHOLD = int(os.getenv("NOTE_MIN_THRESHOLD", "1"))  # 允许单个内容总结
    NOTE_MAX_CONCURRENT_TASKS = int(os.getenv("NOTE_MAX_CONCURRENT_TASKS", "10"))
    NOTE_TASK_TIMEOUT = int(os.getenv("NOTE_TASK_TIMEOUT", "300"))  # 5分钟
    NOTE_CONFIDENCE_THRESHOLD = float(os.getenv("NOTE_CONFIDENCE_THRESHOLD", "0.6"))
    NOTE_MAX_CONTENT_LENGTH = int(os.getenv("NOTE_MAX_CONTENT_LENGTH", "2000"))
    
    # AI模型配置
    NOTE_AI_MODEL = os.getenv("NOTE_AI_MODEL", "gemini-2.0-flash-exp")
    NOTE_AI_MAX_RETRIES = int(os.getenv("NOTE_AI_MAX_RETRIES", "3"))
    NOTE_AI_RETRY_DELAY = int(os.getenv("NOTE_AI_RETRY_DELAY", "1"))  # 秒
    
    # 提示词文件路径
    NOTE_PROMPT_SINGLE = os.getenv("NOTE_PROMPT_SINGLE", "./prompts/note_summary_single.txt")
    NOTE_PROMPT_COMPREHENSIVE = os.getenv("NOTE_PROMPT_COMPREHENSIVE", "./prompts/note_summary_comprehensive.txt")
    NOTE_PROMPT_CORRECTION = os.getenv("NOTE_PROMPT_CORRECTION", "./prompts/note_summary_correction.txt")

    # Environment
    ENVIRONMENT = os.getenv("ENVIRONMENT", "development")

settings = Settings()
