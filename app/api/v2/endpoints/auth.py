import jwt
import requests
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.crud import user
from app.schemas.user import User, UserCreate
from app.core.config import settings

router = APIRouter()


@router.get("/login")
async def login():
    """重定向到OAuth授权页面"""
    auth_url = (
        f"{settings.OAUTH_AUTHORIZE_URL}"
        f"?client_id={settings.OAUTH_CLIENT_ID}"
        f"&redirect_uri={settings.OAUTH_REDIRECT_URI}"
        f"&response_type=code"
        f"&scope=read:user"
    )
    return RedirectResponse(url=auth_url)


@router.get("/oauth/callback")
async def oauth_callback(
    code: str,
    db: Session = Depends(get_db)
):
    """OAuth回调处理"""
    try:
        # 1. 用code换取access_token
        token_data = {
            "client_id": settings.OAUTH_CLIENT_ID,
            "client_secret": settings.OAUTH_CLIENT_SECRET,
            "code": code,
            "redirect_uri": settings.OAUTH_REDIRECT_URI,
            "grant_type": "authorization_code"
        }

        # Casdoor需要使用POST请求，并设置正确的headers
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded"
        }

        token_response = requests.post(settings.OAUTH_TOKEN_URL, data=token_data, headers=headers)

        # 检查响应状态
        if not token_response.ok:
            raise HTTPException(
                status_code=400,
                detail=f"Token request failed: {token_response.status_code} - {token_response.text}"
            )

        # 尝试解析JSON响应
        try:
            tokens = token_response.json()
        except ValueError:
            # 如果不是JSON，可能是form-encoded格式
            from urllib.parse import parse_qs
            tokens = parse_qs(token_response.text)
            # 将列表值转换为单个值
            tokens = {k: v[0] if isinstance(v, list) and len(v) > 0 else v for k, v in tokens.items()}

        # 2. 从access_token中解析用户信息（JWT）
        access_token = tokens.get("access_token")
        if not access_token:
            raise HTTPException(
                status_code=400,
                detail=f"No access token received. Response: {tokens}"
            )

        # 解码JWT获取用户信息（不验证签名，因为是从可信源获取）
        try:
            user_info = jwt.decode(access_token, options={"verify_signature": False})
        except jwt.DecodeError as e:
            raise HTTPException(
                status_code=400,
                detail=f"Failed to decode JWT token: {str(e)}"
            )

        # 3. 提取用户信息
        oauth_id = user_info.get("id") or user_info.get("sub")
        name = user_info.get("displayName") or user_info.get("name", "")
        email = user_info.get("email", "")
        avatar = user_info.get("avatar", "")

        if not oauth_id:
            raise HTTPException(status_code=400, detail="No user ID in token")

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
        import urllib.parse
        import json
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

    except requests.RequestException as e:
        # 重定向到测试页面显示错误
        import urllib.parse
        error_msg = f"OAuth request failed: {str(e)}"
        redirect_url = f"/static/oauth_test.html?login=error&error={urllib.parse.quote(error_msg)}"
        return RedirectResponse(url=redirect_url)
    except jwt.DecodeError as e:
        import urllib.parse
        error_msg = f"Token decode failed: {str(e)}"
        redirect_url = f"/static/oauth_test.html?login=error&error={urllib.parse.quote(error_msg)}"
        return RedirectResponse(url=redirect_url)
    except Exception as e:
        import urllib.parse
        error_msg = f"Login failed: {str(e)}"
        redirect_url = f"/static/oauth_test.html?login=error&error={urllib.parse.quote(error_msg)}"
        return RedirectResponse(url=redirect_url)


@router.get("/debug/token")
async def debug_token_exchange(code: str):
    """调试token交换过程"""
    try:
        token_data = {
            "client_id": settings.OAUTH_CLIENT_ID,
            "client_secret": settings.OAUTH_CLIENT_SECRET,
            "code": code,
            "redirect_uri": settings.OAUTH_REDIRECT_URI,
            "grant_type": "authorization_code"
        }

        headers = {
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded"
        }

        token_response = requests.post(settings.OAUTH_TOKEN_URL, data=token_data, headers=headers)

        return {
            "status_code": token_response.status_code,
            "headers": dict(token_response.headers),
            "content_type": token_response.headers.get("content-type"),
            "text": token_response.text[:500],  # 限制长度
            "request_data": token_data,
            "request_url": settings.OAUTH_TOKEN_URL
        }
    except Exception as e:
        return {"error": str(e)}


@router.post("/logout")
async def logout():
    """登出"""
    return {"message": "Logged out successfully"}
