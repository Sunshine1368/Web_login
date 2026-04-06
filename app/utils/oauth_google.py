"""
app/utils/oauth_google.py - Google OAuth2 工具函数
文档：https://developers.google.com/identity/protocols/oauth2/web-server
"""
import logging
import urllib.parse

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"

SCOPES = "openid email profile"


def get_google_auth_url(state: str = "") -> str:
    """生成 Google OAuth 授权 URL"""
    params = {
        "client_id": settings.google_client_id,
        "redirect_uri": settings.google_redirect_uri,
        "response_type": "code",
        "scope": SCOPES,
        "access_type": "offline",
        "prompt": "select_account",
        "state": state,
    }
    return f"{GOOGLE_AUTH_URL}?{urllib.parse.urlencode(params)}"


async def exchange_code_for_token(code: str) -> dict | None:
    """用 authorization_code 换取 access_token"""
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(GOOGLE_TOKEN_URL, data={
                "code": code,
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "redirect_uri": settings.google_redirect_uri,
                "grant_type": "authorization_code",
            }, timeout=10)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error(f"[Google] Token exchange failed: {e}")
            return None


async def get_google_user_info(access_token: str) -> dict | None:
    """获取 Google 用户信息"""
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(
                GOOGLE_USERINFO_URL,
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=10,
            )
            resp.raise_for_status()
            return resp.json()
            # 返回字段示例：
            # {sub, name, given_name, family_name, email, picture, email_verified}
        except Exception as e:
            logger.error(f"[Google] Userinfo failed: {e}")
            return None
