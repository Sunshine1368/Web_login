"""
app/utils/oauth_wechat.py - 微信网页 OAuth2 工具函数
文档：https://developers.weixin.qq.com/doc/offiaccount/OA_Web_Apps/Wechat_webpage_authorization.html

说明：
- 需要微信公众号（服务号）并开通网页授权功能
- 回调域名需在微信后台配置白名单
- scope=snsapi_userinfo 可获取用户详细信息（需用户主动授权）
"""
import logging
import urllib.parse

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

WECHAT_AUTH_URL = "https://open.weixin.qq.com/connect/oauth2/authorize"
WECHAT_TOKEN_URL = "https://api.weixin.qq.com/sns/oauth2/access_token"
WECHAT_USERINFO_URL = "https://api.weixin.qq.com/sns/userinfo"
WECHAT_REFRESH_URL = "https://api.weixin.qq.com/sns/oauth2/refresh_token"


def get_wechat_auth_url(state: str = "") -> str:
    """生成微信 OAuth 授权 URL（网页端）"""
    params = {
        "appid": settings.wechat_appid,
        "redirect_uri": settings.wechat_redirect_uri,
        "response_type": "code",
        "scope": "snsapi_userinfo",
        "state": state or "toolkit_login",
    }
    query = urllib.parse.urlencode(params)
    return f"{WECHAT_AUTH_URL}?{query}#wechat_redirect"


async def exchange_code_for_token(code: str) -> dict | None:
    """用 code 换取 access_token 和 openid"""
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(WECHAT_TOKEN_URL, params={
                "appid": settings.wechat_appid,
                "secret": settings.wechat_secret,
                "code": code,
                "grant_type": "authorization_code",
            }, timeout=10)
            data = resp.json()
            if "errcode" in data:
                logger.error(f"[WeChat] Token error: {data}")
                return None
            return data
            # 返回字段：access_token, openid, scope, unionid 等
        except Exception as e:
            logger.error(f"[WeChat] Token exchange failed: {e}")
            return None


async def get_wechat_user_info(access_token: str, openid: str) -> dict | None:
    """获取微信用户详细信息"""
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(WECHAT_USERINFO_URL, params={
                "access_token": access_token,
                "openid": openid,
                "lang": "zh_CN",
            }, timeout=10)
            data = resp.json()
            if "errcode" in data:
                logger.error(f"[WeChat] Userinfo error: {data}")
                return None
            return data
            # 返回字段：openid, nickname, sex, headimgurl, unionid 等
        except Exception as e:
            logger.error(f"[WeChat] Userinfo failed: {e}")
            return None
