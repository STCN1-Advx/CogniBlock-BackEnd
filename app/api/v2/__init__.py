from fastapi import APIRouter
from app.api.v2.endpoints import auth, users, canva, note_summary_single, content
from app.api.v2.endpoints import article, knowledge_base
# 暂时注释掉有问题的模块
# from app.api.v2.endpoints import ocr, smart_note, smart_note_websocket

api_router = APIRouter()

# 认证相关路由
api_router.include_router(auth.router, prefix="/auth", tags=["认证"])

# 用户相关路由
api_router.include_router(users.router, prefix="/users", tags=["用户"])

# 画布相关路由
api_router.include_router(canva.router, prefix="/canva", tags=["画布"])

# 内容相关路由（调试用）
api_router.include_router(content.router, prefix="/content", tags=["内容调试"])

# 笔记总结相关路由（单一端点版本）
api_router.include_router(note_summary_single.router, prefix="/note-summary-single", tags=["笔记总结"])

# 暂时注释掉有问题的路由
# OCR相关路由
# api_router.include_router(ocr.router, prefix="/ocr", tags=["OCR"])

# 智能笔记相关路由
# api_router.include_router(smart_note.router, prefix="/smart-note", tags=["智能笔记"])

# 智能笔记WebSocket路由
# api_router.include_router(smart_note_websocket.router, prefix="/smart-note", tags=["智能笔记WebSocket"])

# 文章相关路由
api_router.include_router(article.router, prefix="/article", tags=["文章"])

# 知识库相关路由
api_router.include_router(knowledge_base.router, prefix="/knowledge-base", tags=["知识库"])
