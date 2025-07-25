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
    BACKEND_CORS_ORIGINS = ["http://localhost:3000", "http://localhost:8080", "http://localhost:5173"]

    # OAuth (Casdoor)
    OAUTH_CLIENT_ID = os.getenv("OAUTH_CLIENT_ID", "")
    OAUTH_CLIENT_SECRET = os.getenv("OAUTH_CLIENT_SECRET", "")
    OAUTH_REDIRECT_URI = os.getenv("OAUTH_REDIRECT_URI", "")
    OAUTH_AUTHORIZE_URL = os.getenv("OAUTH_AUTHORIZE_URL", "")
    OAUTH_TOKEN_URL = os.getenv("OAUTH_TOKEN_URL", "")
    OAUTH_USER_URL = os.getenv("OAUTH_USER_URL", "")

    # OCR Configuration
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "")
    OCR_AI_MODEL_GRAYSCALE = os.getenv("OCR_AI_MODEL_GRAYSCALE", "gemini-2.0-flash")
    OCR_AI_MODEL_COLOR = os.getenv("OCR_AI_MODEL_COLOR", "gpt-4o")
    OCR_AI_MODEL_MERGE = os.getenv("OCR_AI_MODEL_MERGE", "gpt-4o")
    OCR_AI_MODEL_FINAL = os.getenv("OCR_AI_MODEL_FINAL", "gpt-4o")
    OCR_WORKER_THREADS = int(os.getenv("OCR_WORKER_THREADS", "2"))
    OCR_MAX_CONCURRENT = int(os.getenv("OCR_MAX_CONCURRENT", "5"))
    OCR_MAX_IMAGE_AREA = int(os.getenv("OCR_MAX_IMAGE_AREA", "2073600"))
    OCR_PROMPT_FILE = os.getenv("OCR_PROMPT_FILE", "./prompts/ocr_prompt.txt")
    OCR_ENABLE_MOCK = os.getenv("OCR_ENABLE_MOCK", "False").lower() == "true"

    # Environment
    ENVIRONMENT = os.getenv("ENVIRONMENT", "development")

settings = Settings()
