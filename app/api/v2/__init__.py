from fastapi import APIRouter
from app.api.v2.endpoints import auth, users, ocr, canva

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(ocr.router, prefix="/ocr", tags=["ocr"])
api_router.include_router(canva.router, prefix="/canva", tags=["canvas"])
