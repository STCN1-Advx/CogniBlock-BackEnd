from fastapi import HTTPException, Request, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional, Callable
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.crud import user
from app.models.user import User
from app.utils.session_manager import session_manager


security = HTTPBearer(auto_error=False)


def get_session_from_cookies(request: Request) -> Optional[str]:
    """从cookies中获取session-id
    
    Args:
        request: FastAPI请求对象
        
    Returns:
        session_id或None
    """
    return request.cookies.get("session-id")


def get_user_id_from_cookies(request: Request) -> Optional[str]:
    """从cookies中获取x-user-id
    
    Args:
        request: FastAPI请求对象
        
    Returns:
        user_id或None
    """
    return request.cookies.get("x-user-id")


def validate_session_auth(request: Request, db: Session = Depends(get_db)) -> User:
    """验证session认证并返回用户对象
    
    这个函数用作FastAPI的依赖项，验证用户的session认证。
    如果认证失败，会抛出HTTPException。
    
    Args:
        request: FastAPI请求对象
        db: 数据库session
        
    Returns:
        User对象
        
    Raises:
        HTTPException: 认证失败时抛出403错误
    """
    # 从cookies获取认证信息
    session_id = get_session_from_cookies(request)
    user_id = get_user_id_from_cookies(request)
    
    print(f"🔐 [Auth Middleware] 验证请求: {request.url.path}")
    print(f"🔐 [Auth Middleware] session-id: {session_id[:8] + '...' if session_id else 'None'}")
    print(f"🔐 [Auth Middleware] x-user-id: {user_id}")
    
    # 检查必要的认证信息是否存在
    if not session_id or not user_id:
        print(f"❌ [Auth Middleware] 缺少认证信息")
        raise HTTPException(
            status_code=403,
            detail="Forbidden: 缺少认证信息"
        )
    
    # 验证session
    validated_user_id = session_manager.validate_session(session_id)
    if not validated_user_id:
        print(f"❌ [Auth Middleware] Session无效或已过期")
        raise HTTPException(
            status_code=403,
            detail="Forbidden: Session无效或已过期"
        )
    
    # 验证user_id是否匹配
    if validated_user_id != user_id:
        print(f"❌ [Auth Middleware] 用户ID不匹配: session={validated_user_id}, cookie={user_id}")
        raise HTTPException(
            status_code=403,
            detail="Forbidden: 用户认证信息不匹配"
        )
    
    # 从数据库获取用户信息
    db_user = user.get(db, id=user_id)
    if not db_user:
        print(f"❌ [Auth Middleware] 用户不存在: {user_id}")
        raise HTTPException(
            status_code=403,
            detail="Forbidden: 用户不存在"
        )
    
    print(f"✅ [Auth Middleware] 认证成功: {db_user.name} ({user_id})")
    
    # 刷新session（可选，延长session有效期）
    session_manager.refresh_session(session_id)
    
    return db_user


def optional_session_auth(request: Request, db: Session = Depends(get_db)) -> Optional[User]:
    """可选的session认证
    
    这个函数用于那些可以选择性认证的接口。
    如果提供了认证信息且有效，返回用户对象；否则返回None。
    
    Args:
        request: FastAPI请求对象
        db: 数据库session
        
    Returns:
        User对象或None
    """
    try:
        return validate_session_auth(request, db)
    except HTTPException:
        return None


def require_session_auth(request: Request, db: Session = Depends(get_db)) -> User:
    """必需的session认证
    
    这是validate_session_auth的别名，用于更明确地表示这是必需的认证。
    
    Args:
        request: FastAPI请求对象
        db: 数据库session
        
    Returns:
        User对象
        
    Raises:
        HTTPException: 认证失败时抛出403错误
    """
    return validate_session_auth(request, db)


def get_current_user_id(request: Request) -> Optional[str]:
    """获取当前用户ID（仅从cookies，不验证session）
    
    Args:
        request: FastAPI请求对象
        
    Returns:
        用户ID或None
    """
    return get_user_id_from_cookies(request)


def create_auth_dependency(required: bool = True) -> Callable:
    """创建认证依赖项的工厂函数
    
    Args:
        required: 是否必需认证
        
    Returns:
        认证依赖项函数
    """
    if required:
        return require_session_auth
    else:
        return optional_session_auth