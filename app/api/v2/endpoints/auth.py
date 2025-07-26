import httpx
import secrets
import urllib.parse
import base64
import json
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse, JSONResponse
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.crud import user
from app.schemas.user import UserCreate
from app.models.user import User
from app.core.config import settings
from app.utils.session_manager import session_manager
from app.middleware.auth_middleware import require_session_auth, get_current_user_id

router = APIRouter()

# OAuth状态存储（简化版，生产环境应使用Redis）
_state_store = {}


@router.get("/login")
async def login():
    """重定向到OAuth授权页面"""
    # 生成随机state防止CSRF攻击
    state = secrets.token_urlsafe(32)
    
    print(f"🔐 [OAuth Login] 生成新的state: {state}")
    print(f"🔐 [OAuth Login] 当前state存储数量: {len(_state_store)}")

    # 存储state
    _state_store[state] = {
        "created_at": datetime.now(),
        "expires_at": datetime.now() + timedelta(minutes=10)
    }
    
    print(f"🔐 [OAuth Login] state已存储，过期时间: {_state_store[state]['expires_at']}")

    # 构建授权URL
    params = {
        "client_id": settings.OAUTH_CLIENT_ID,
        "response_type": "code",
        "redirect_uri": settings.OAUTH_REDIRECT_URI,
        "state": state,
        "scope": "read:user"
    }

    auth_url = f"{settings.OAUTH_AUTHORIZE_URL}?" + urllib.parse.urlencode(params)
    print(f"🔐 [OAuth Login] 重定向到授权URL: {auth_url}")
    return RedirectResponse(url=auth_url)


def verify_state(state: str) -> bool:
    """验证OAuth state参数"""
    print(f"🔍 [State Verify] 开始验证state: {state}")
    print(f"🔍 [State Verify] 当前存储的state数量: {len(_state_store)}")
    print(f"🔍 [State Verify] 存储的state列表: {list(_state_store.keys())}")
    
    if state not in _state_store:
        print(f"❌ [State Verify] state不存在于存储中: {state}")
        return False

    state_info = _state_store[state]
    current_time = datetime.now()
    print(f"🔍 [State Verify] 找到state信息: {state_info}")
    print(f"🔍 [State Verify] 当前时间: {current_time}")
    print(f"🔍 [State Verify] state过期时间: {state_info['expires_at']}")

    # 检查是否过期
    if current_time > state_info["expires_at"]:
        print(f"❌ [State Verify] state已过期，删除: {state}")
        del _state_store[state]
        return False

    # 验证成功后删除state
    print(f"✅ [State Verify] state验证成功，删除: {state}")
    del _state_store[state]
    return True


async def exchange_code_for_token(code: str) -> dict:
    """用授权码换取访问令牌"""
    token_url = f"{settings.OAUTH_AUTHORIZE_URL.replace('/login/oauth/authorize', '/api/login/oauth/access_token')}"

    data = {
        "client_id": settings.OAUTH_CLIENT_ID,
        "client_secret": settings.OAUTH_CLIENT_SECRET,
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": settings.OAUTH_REDIRECT_URI
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(
            token_url,
            data=data,
            headers={"Accept": "application/json"}
        )

        if response.status_code != 200:
            raise HTTPException(status_code=400, detail="Token交换失败")

        # 尝试解析JSON
        try:
            return response.json()
        except ValueError:
            # 如果不是JSON，尝试解析为form-encoded
            content_type = response.headers.get('content-type', '')
            if 'application/x-www-form-urlencoded' in content_type:
                parsed = urllib.parse.parse_qs(response.text)
                result = {}
                for key, value_list in parsed.items():
                    result[key] = value_list[0] if value_list else None
                return result
            else:
                raise HTTPException(status_code=400, detail="无法解析Token响应")


async def parse_user_info_from_token(access_token: str) -> dict:
    """从JWT access_token中解析用户信息"""
    try:
        # JWT格式: header.payload.signature
        parts = access_token.split('.')
        if len(parts) != 3:
            raise HTTPException(status_code=400, detail="无效的JWT格式")

        # 解码payload部分
        payload = parts[1]
        # 添加必要的padding
        payload += '=' * (4 - len(payload) % 4)

        # Base64解码
        decoded_bytes = base64.urlsafe_b64decode(payload)
        user_data = json.loads(decoded_bytes.decode('utf-8'))

        # 适配Casdoor的字段映射
        return {
            "id": user_data.get("id") or user_data.get("sub"),
            "username": user_data.get("name"),
            "display_name": user_data.get("displayName"),
            "email": user_data.get("email"),
            "avatar_url": user_data.get("avatar")
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail="解析用户信息失败")


@router.get("/oauth/callback")
async def oauth_callback(
    code: str,
    state: str = None,
    db: Session = Depends(get_db)
):
    """OAuth回调处理"""
    print(f"🔄 [OAuth Callback] 收到回调请求")
    print(f"🔄 [OAuth Callback] code: {code[:20]}..." if code else "🔄 [OAuth Callback] code: None")
    print(f"🔄 [OAuth Callback] state: {state}")
    
    try:
        # 验证state（如果提供了）
        if state:
            print(f"🔄 [OAuth Callback] 开始验证state参数")
            if not verify_state(state):
                print(f"❌ [OAuth Callback] state验证失败: {state}")
                raise HTTPException(status_code=400, detail="无效的state参数")
            print(f"✅ [OAuth Callback] state验证成功")
        else:
            print(f"⚠️ [OAuth Callback] 未提供state参数，跳过验证")

        # 1. 交换访问令牌
        token_info = await exchange_code_for_token(code)
        access_token = token_info.get("access_token")

        if not access_token:
            raise HTTPException(status_code=400, detail="未获取到访问令牌")

        # 2. 从access_token中解析用户信息
        oauth_user_info = await parse_user_info_from_token(access_token)

        # 3. 提取用户信息
        oauth_id = oauth_user_info.get("id")
        name = oauth_user_info.get("display_name") or oauth_user_info.get("username", "")
        email = oauth_user_info.get("email", "")
        avatar = oauth_user_info.get("avatar_url", "")

        if not oauth_id:
            raise HTTPException(status_code=400, detail="OAuth用户信息不完整")

        # 4. 查找或创建用户
        existing_user = user.get_by_oauth_id(db, oauth_id=str(oauth_id))

        if existing_user:
            # 更新用户信息
            user_update = {"name": name, "email": email, "avatar": avatar}
            db_user = user.update(db, db_obj=existing_user, obj_in=user_update)
        else:
            # 创建新用户
            user_create = UserCreate(
                oauth_id=str(oauth_id),
                name=name,
                email=email,
                avatar=avatar
            )
            db_user = user.create(db, obj_in=user_create)

        # 5. 创建session并设置cookie
        user_id = str(db_user.id)
        session_id = session_manager.create_session(user_id, session_duration_hours=24)
        
        # 准备用户数据
        user_data = {
            "id": user_id,
            "oauth_id": db_user.oauth_id,
            "name": db_user.name,
            "email": db_user.email,
            "avatar": db_user.avatar,
            "login_time": datetime.now().isoformat()
        }
        
        # 创建响应并设置cookie
        response = JSONResponse(
            content={
                "success": True,
                "message": "登录成功",
                "user": user_data
            }
        )
        
        # 设置认证cookie
        response.set_cookie(
            key="x-user-id",
            value=user_id,
            max_age=24 * 60 * 60,  # 24小时
            httponly=True,
            secure=False,  # 开发环境设为False，生产环境应设为True
            samesite="lax"
        )
        
        response.set_cookie(
            key="session-id",
            value=session_id,
            max_age=24 * 60 * 60,  # 24小时
            httponly=True,
            secure=False,  # 开发环境设为False，生产环境应设为True
            samesite="lax"
        )
        
        print(f"✅ [OAuth Callback] 登录成功，已设置cookie: user_id={user_id}, session_id={session_id[:8]}...")
        
        return response

    except Exception as e:
        # 记录详细的错误信息
        print(f"❌ [OAuth Callback] 发生异常: {type(e).__name__}: {str(e)}")
        print(f"❌ [OAuth Callback] 异常详情: {repr(e)}")
        
        # 返回JSON错误响应
        error_msg = f"登录失败: {str(e)}"
        print(f"❌ [OAuth Callback] 返回错误响应: {error_msg}")
        
        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "message": error_msg,
                "error_type": type(e).__name__
            }
        )


@router.get("/me")
async def get_current_user(current_user: User = Depends(require_session_auth)):
    """获取当前用户信息
    
    需要有效的session认证
    """
    return {
        "success": True,
        "id": str(current_user.id),
        "oauth_id": current_user.oauth_id,
        "username": current_user.name,
        "name": current_user.name,
        "email": current_user.email,
        "avatar": current_user.avatar,
        "created_at": current_user.created_at.isoformat() if current_user.created_at else None,
        "updated_at": current_user.updated_at.isoformat() if current_user.updated_at else None
    }


@router.get("/session/status")
async def get_session_status(user_id: str = Depends(get_current_user_id)):
    """获取session状态
    
    可选认证，如果有session则返回用户ID，否则返回未认证状态
    """
    if user_id:
        return {
            "authenticated": True,
            "user_id": user_id
        }
    else:
        return {
            "authenticated": False,
            "user_id": None
        }


@router.post("/logout")
async def logout(request: Request):
    """登出
    
    清除用户的session和cookie
    """
    # 获取session信息
    session_id = request.cookies.get("session-id")
    user_id = request.cookies.get("x-user-id")
    
    print(f"🚪 [Logout] 用户登出: user_id={user_id}, session_id={session_id[:8] + '...' if session_id else 'None'}")
    
    # 撤销session
    if session_id:
        session_manager.revoke_session(session_id)
    
    # 创建响应并清除cookie
    response = JSONResponse(
        content={
            "success": True,
            "message": "登出成功"
        }
    )
    
    # 清除认证cookie
    response.delete_cookie(key="x-user-id")
    response.delete_cookie(key="session-id")
    
    print(f"✅ [Logout] 登出完成，已清除cookie")
    
    return response
