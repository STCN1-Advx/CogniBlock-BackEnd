"""
画布API认证中间件
提供用户认证和权限验证功能
"""
from typing import Optional, Callable, Any
from functools import wraps
from uuid import UUID
from fastapi import Depends, HTTPException, status, Header
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.crud import user
from app.models.user import User
from app.services.canva_service import PermissionDeniedError, CanvaNotFoundError


class AuthenticationError(HTTPException):
    """认证错误异常"""
    def __init__(self, detail: str = "认证失败"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"}
        )


class AuthorizationError(HTTPException):
    """授权错误异常"""
    def __init__(self, detail: str = "权限不足"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail
        )


async def get_current_user(
    user_id: Optional[str] = Header(None, alias="X-User-ID"),
    db: Session = Depends(get_db)
) -> User:
    """
    获取当前认证用户
    
    Args:
        user_id: 从请求头中获取的用户ID
        db: 数据库会话
        
    Returns:
        User: 当前用户对象
        
    Raises:
        AuthenticationError: 当用户ID无效或用户不存在时
    """
    if not user_id:
        raise AuthenticationError("缺少用户认证信息")
    
    try:
        # 将字符串转换为UUID
        user_uuid = UUID(user_id)
    except ValueError:
        raise AuthenticationError("无效的用户ID格式")
    
    # 查询用户
    current_user = user.get(db, id=user_uuid)
    if not current_user:
        raise AuthenticationError("用户不存在")
    
    return current_user


async def get_optional_user(
    user_id: Optional[str] = Header(None, alias="X-User-ID"),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """
    获取可选的当前用户（允许匿名访问）

    Args:
        user_id: 从请求头中获取的用户ID
        db: 数据库会话

    Returns:
        Optional[User]: 当前用户对象或None
    """
    if not user_id:
        return None

    try:
        user_uuid = UUID(user_id)
        return user.get(db, id=user_uuid)
    except (ValueError, Exception):
        return None


# 为了兼容性，创建一个别名
get_current_user_optional = get_optional_user


def require_canvas_owner(func: Callable) -> Callable:
    """
    装饰器：要求用户是画布的所有者
    
    使用方法:
    @require_canvas_owner
    async def some_endpoint(canvas_id: int, current_user: User = Depends(get_current_user)):
        pass
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        # 从kwargs中获取必要的参数
        canvas_id = kwargs.get('canvas_id')
        current_user = None
        db = None
        
        # 查找current_user和db参数
        for arg in args:
            if isinstance(arg, User):
                current_user = arg
            elif isinstance(arg, Session):
                db = arg
        
        for key, value in kwargs.items():
            if isinstance(value, User) and 'user' in key.lower():
                current_user = value
            elif isinstance(value, Session) and 'db' in key.lower():
                db = value
        
        if not current_user or not db or canvas_id is None:
            raise AuthorizationError("权限验证失败：缺少必要参数")
        
        # 验证画布所有权
        from app.crud.canvas import canvas as canvas_crud
        canvas_obj = canvas_crud.get(db, id=canvas_id)
        
        if not canvas_obj:
            raise CanvaNotFoundError(f"画布 {canvas_id} 不存在")
        
        if canvas_obj.owner_id != current_user.id:
            raise PermissionDeniedError(f"用户无权访问画布 {canvas_id}")
        
        return await func(*args, **kwargs)
    
    return wrapper


def require_canvas_access(func: Callable) -> Callable:
    """
    装饰器：要求用户有画布访问权限（所有者或被授权用户）
    
    使用方法:
    @require_canvas_access
    async def some_endpoint(canvas_id: int, current_user: User = Depends(get_current_user)):
        pass
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        # 从kwargs中获取必要的参数
        canvas_id = kwargs.get('canvas_id')
        current_user = None
        db = None
        
        # 查找current_user和db参数
        for arg in args:
            if isinstance(arg, User):
                current_user = arg
            elif isinstance(arg, Session):
                db = arg
        
        for key, value in kwargs.items():
            if isinstance(value, User) and 'user' in key.lower():
                current_user = value
            elif isinstance(value, Session) and 'db' in key.lower():
                db = value
        
        if not current_user or not db or canvas_id is None:
            raise AuthorizationError("权限验证失败：缺少必要参数")
        
        # 验证画布访问权限
        from app.crud.canvas import canvas as canvas_crud
        has_access = canvas_crud.check_ownership(db, canvas_id=canvas_id, user_id=current_user.id)
        
        if not has_access:
            raise PermissionDeniedError(f"用户无权访问画布 {canvas_id}")
        
        return await func(*args, **kwargs)
    
    return wrapper


def require_content_access(func: Callable) -> Callable:
    """
    装饰器：要求用户有内容访问权限
    
    使用方法:
    @require_content_access
    async def some_endpoint(content_id: int, current_user: User = Depends(get_current_user)):
        pass
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        # 从kwargs中获取必要的参数
        content_id = kwargs.get('content_id')
        current_user = None
        db = None
        
        # 查找current_user和db参数
        for arg in args:
            if isinstance(arg, User):
                current_user = arg
            elif isinstance(arg, Session):
                db = arg
        
        for key, value in kwargs.items():
            if isinstance(value, User) and 'user' in key.lower():
                current_user = value
            elif isinstance(value, Session) and 'db' in key.lower():
                db = value
        
        if not current_user or not db or content_id is None:
            raise AuthorizationError("权限验证失败：缺少必要参数")
        
        # 验证内容访问权限
        from app.crud.content import content as content_crud
        has_access = content_crud.check_user_access(db, content_id=content_id, user_id=current_user.id)
        
        if not has_access:
            raise PermissionDeniedError(f"用户无权访问内容 {content_id}")
        
        return await func(*args, **kwargs)
    
    return wrapper


class CanvaAuthService:
    """画布认证服务类"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def verify_user_exists(self, user_id: UUID) -> User:
        """验证用户是否存在"""
        current_user = user.get(self.db, id=user_id)
        if not current_user:
            raise AuthenticationError("用户不存在")
        return current_user
    
    def verify_canvas_ownership(self, canvas_id: int, user_id: UUID) -> bool:
        """验证用户是否拥有画布"""
        from app.crud.canvas import canvas as canvas_crud
        return canvas_crud.check_ownership(self.db, canvas_id=canvas_id, user_id=user_id)
    
    def verify_content_access(self, content_id: int, user_id: UUID) -> bool:
        """验证用户是否有内容访问权限"""
        from app.crud.content import content as content_crud
        return content_crud.check_user_access(self.db, content_id=content_id, user_id=user_id)
    
    def get_user_permissions(self, user_id: UUID) -> dict:
        """获取用户权限信息"""
        current_user = self.verify_user_exists(user_id)
        
        # 获取用户拥有的画布数量
        from app.crud.canvas import canvas as canvas_crud
        canvas_count = len(canvas_crud.get_by_owner(self.db, owner_id=user_id))
        
        # 获取用户可访问的内容数量
        from app.crud.content import content as content_crud
        content_count = len(content_crud.get_user_contents(self.db, user_id=user_id))
        
        return {
            "user_id": str(user_id),
            "user_name": current_user.name,
            "canvas_count": canvas_count,
            "content_count": content_count,
            "permissions": {
                "can_create_canvas": True,
                "can_create_content": True,
                "can_share_content": True
            }
        }


# 创建认证服务实例工厂
def get_auth_service(db: Session = Depends(get_db)) -> CanvaAuthService:
    """获取认证服务实例"""
    return CanvaAuthService(db)