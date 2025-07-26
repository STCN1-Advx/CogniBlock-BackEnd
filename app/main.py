from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from app.core.config import settings
from app.api.v2 import api_router
from app.utils.task_manager import task_manager

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时初始化任务管理器
    await task_manager.start_cleanup_task()
    yield
    # 关闭时清理资源（如果需要）

app = FastAPI(
    title="CogniBlock API",
    description="CogniBlock Backend API with OCR Support",
    version="2.0.0",
    openapi_url="/openapi.json",
    lifespan=lifespan
)

# Set all CORS enabled origins
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# 添加静态文件服务
app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(api_router, prefix=settings.API_V2_STR)

@app.get("/")
async def root():
    return {"message": "CogniBlock API v2.0.0 with OCR Support"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.get("/ocr-test")
async def ocr_test():
    """重定向到OCR测试页面"""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/static/ocr_test.html")
