import httpx
import secrets
import urllib.parse
import base64
import json
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.crud import user
from app.schemas.user import UserCreate
from app.core.config import settings

router = APIRouter()

# OAuth状态存储（简化版，生产环境应使用Redis）
_state_store = {}


@router.get("/login")
async def login():
    """重定向到OAuth授权页面"""
    # 生成随机state防止CSRF攻击
    state = secrets.token_urlsafe(32)

    # 存储state
    _state_store[state] = {
        "created_at": datetime.now(),
        "expires_at": datetime.now() + timedelta(minutes=10)
    }

    # 构建授权URL
    params = {
        "client_id": settings.OAUTH_CLIENT_ID,
        "response_type": "code",
        "redirect_uri": settings.OAUTH_REDIRECT_URI,
        "state": state,
        "scope": "read:user"
    }

    auth_url = f"{settings.OAUTH_AUTHORIZE_URL}?" + urllib.parse.urlencode(params)
    return RedirectResponse(url=auth_url)


def verify_state(state: str) -> bool:
    """验证OAuth state参数"""
    if state not in _state_store:
        return False

    state_info = _state_store[state]

    # 检查是否过期
    if datetime.now() > state_info["expires_at"]:
        del _state_store[state]
        return False

    # 验证成功后删除state
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
    try:
        # 验证state（如果提供了）
        if state and not verify_state(state):
            raise HTTPException(status_code=400, detail="无效的state参数")

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

        # 5. 重定向到测试页面，带上用户信息
        user_data = {
            "id": db_user.id,
            "oauth_id": db_user.oauth_id,
            "name": db_user.name,
            "email": db_user.email,
            "avatar": db_user.avatar
        }

        # 将用户信息编码到URL参数中
        user_param = urllib.parse.quote(json.dumps(user_data))
        redirect_url = f"/static/oauth_test.html?login=success&user={user_param}"

        return RedirectResponse(url=redirect_url)

    except Exception as e:
        # 重定向到测试页面显示错误
        error_msg = f"登录失败: {str(e)}"
        redirect_url = f"/static/oauth_test.html?login=error&error={urllib.parse.quote(error_msg)}"
        return RedirectResponse(url=redirect_url)


@router.post("/logout")
async def logout():
    """登出"""
    return {"message": "Logged out successfully"}
