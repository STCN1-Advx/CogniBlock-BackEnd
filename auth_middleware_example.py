"""
认证中间件使用示例
展示如何在画布API端点中使用认证功能
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.db.session import get_db
from app.api.v2.auth import (
    get_current_user, get_optional_user, 
    require_canvas_owner, require_canvas_access,
    CanvaAuthService, get_auth_service
)
from app.models.user import User
from app.schemas.canva import CanvaPullRequest, CanvaPushRequest, CardResponse

router = APIRouter()


@router.get("/user/info")
async def get_user_info(
    current_user: User = Depends(get_current_user),
    auth_service: CanvaAuthService = Depends(get_auth_service)
):
    """
    获取当前用户信息和权限
    需要用户认证
    """
    permissions = auth_service.get_user_permissions(current_user.id)
    
    return {
        "user": {
            "id": str(current_user.id),
            "name": current_user.name,
            "email": current_user.email,
            "avatar": current_user.avatar
        },
        "permissions": permissions
    }


@router.get("/user/optional")
async def get_optional_user_info(
    current_user: User = Depends(get_optional_user)
):
    """
    获取可选用户信息
    支持匿名访问
    """
    if current_user:
        return {
            "authenticated": True,
            "user": {
                "id": str(current_user.id),
                "name": current_user.name,
                "email": current_user.email
            }
        }
    else:
        return {
            "authenticated": False,
            "message": "匿名用户"
        }


@router.post("/canva/{canvas_id}/pull")
@require_canvas_access
async def pull_canvas_with_auth(
    canvas_id: int,
    request: CanvaPullRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> List[CardResponse]:
    """
    拉取画布数据（带权限检查）
    使用 @require_canvas_access 装饰器自动验证权限
    """
    # 权限已经通过装饰器验证，直接执行业务逻辑
    from app.services.canva_service import canva_service
    
    try:
        cards = await canva_service.pull_canva(
            db=db,
            canvas_id=canvas_id,
            user_id=current_user.id
        )
        return cards
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"拉取画布失败: {str(e)}"
        )


@router.post("/canva/{canvas_id}/push")
@require_canvas_owner
async def push_canvas_with_auth(
    canvas_id: int,
    request: CanvaPushRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    推送画布数据（仅所有者）
    使用 @require_canvas_owner 装饰器确保只有所有者可以修改
    """
    # 权限已经通过装饰器验证，直接执行业务逻辑
    from app.services.canva_service import canva_service
    
    try:
        await canva_service.push_canva(
            db=db,
            canvas_id=canvas_id,
            cards_data=request.cards,
            user_id=current_user.id
        )
        return {"message": "画布更新成功"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"推送画布失败: {str(e)}"
        )


@router.get("/canva/{canvas_id}/info")
async def get_canvas_info_manual_auth(
    canvas_id: int,
    current_user: User = Depends(get_current_user),
    auth_service: CanvaAuthService = Depends(get_auth_service),
    db: Session = Depends(get_db)
):
    """
    获取画布信息（手动权限检查）
    展示如何手动进行权限验证
    """
    # 手动验证画布访问权限
    has_access = auth_service.verify_canvas_ownership(canvas_id, current_user.id)
    if not has_access:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权访问该画布"
        )
    
    # 执行业务逻辑
    from app.services.canva_service import canva_service
    
    try:
        canvas_info = await canva_service.get_canva_info(
            db=db,
            canvas_id=canvas_id,
            user_id=current_user.id
        )
        return canvas_info
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取画布信息失败: {str(e)}"
        )


@router.get("/content/{content_id}/access")
async def check_content_access(
    content_id: int,
    current_user: User = Depends(get_current_user),
    auth_service: CanvaAuthService = Depends(get_auth_service)
):
    """
    检查内容访问权限
    """
    has_access = auth_service.verify_content_access(content_id, current_user.id)
    
    return {
        "content_id": content_id,
        "user_id": str(current_user.id),
        "has_access": has_access,
        "message": "有权访问" if has_access else "无权访问"
    }


@router.get("/auth/test")
async def test_auth_middleware():
    """
    测试认证中间件功能
    无需认证的测试端点
    """
    return {
        "message": "认证中间件测试端点",
        "features": [
            "基于UUID的用户认证",
            "请求头认证支持",
            "多层级权限检查",
            "装饰器权限控制",
            "可选用户认证",
            "详细错误处理"
        ],
        "usage": {
            "authentication": "在请求头中添加 X-User-ID",
            "authorization": "使用装饰器或手动权限检查",
            "error_handling": "自动返回401/403状态码"
        }
    }


# 错误处理示例
@router.get("/auth/error-demo")
async def auth_error_demo(
    error_type: str = "auth",
    current_user: User = Depends(get_current_user)
):
    """
    认证错误演示
    用于测试不同类型的认证错误
    """
    from app.api.v2.auth import AuthenticationError, AuthorizationError
    
    if error_type == "auth":
        raise AuthenticationError("演示认证错误")
    elif error_type == "authz":
        raise AuthorizationError("演示授权错误")
    else:
        return {
            "message": "认证成功",
            "user": current_user.name,
            "available_errors": ["auth", "authz"]
        }


# 权限级别演示
@router.get("/permission-levels")
async def permission_levels_demo(
    current_user: User = Depends(get_current_user),
    auth_service: CanvaAuthService = Depends(get_auth_service)
):
    """
    权限级别演示
    展示不同级别的权限检查
    """
    permissions = auth_service.get_user_permissions(current_user.id)
    
    return {
        "user_info": {
            "id": str(current_user.id),
            "name": current_user.name
        },
        "permission_levels": {
            "level_1": "用户认证 - 验证用户身份",
            "level_2": "画布访问 - 验证画布访问权限",
            "level_3": "画布所有权 - 验证画布所有者权限",
            "level_4": "内容访问 - 验证内容访问权限"
        },
        "current_permissions": permissions
    }