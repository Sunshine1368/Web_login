"""
app/routers/auth_ext.py - 前端兼容格式的扩展认证路由

与前端约定的响应格式：
  - 成功：{"success": true, "token": "...", "user": {...}}
  - 失败：{"success": false, "message": "..."}
  - check-email: {"exists": true/false}

涵盖：
  POST /api/auth/check-email     检查邮箱是否已注册
  POST /api/auth/register        发送 OTP 邮件（暂存注册信息）
  POST /api/auth/verify-otp      验证 OTP，完成注册，返回 token
  POST /api/auth/login           登录（前端格式）
  GET  /api/auth/google/redirect  跳转 Google 授权页
  GET  /api/auth/google/callback  Google 回调，弹窗 postMessage token
  GET  /api/auth/wechat/redirect  跳转微信授权页
  GET  /api/auth/wechat/callback  微信回调，弹窗 postMessage token
"""
import logging
import re
from typing import Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import AsyncSessionLocal
from app.dependencies import get_db
from app.models.otp import OAuthAccount
from app.models.user import User, UserSettings
from app.models.wallet import Wallet
from app.services.otp_service import OTPService
from app.services.user_service import UserService, UserServiceError
from app.utils.email import send_otp_email
from app.utils.oauth_google import (
    exchange_code_for_token as google_exchange,
    get_google_auth_url,
    get_google_user_info,
)
from app.utils.oauth_wechat import (
    exchange_code_for_token as wechat_exchange,
    get_wechat_auth_url,
    get_wechat_user_info,
)
from app.utils.security import create_access_token, hash_password, verify_password

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/auth", tags=["Auth-Frontend"])

# ── 注册信息暂存（内存，Key=email）──────────────────────────────────────────────
# 结构：{email: {firstName, lastName, password_hash}}
_pending_registrations: dict[str, dict] = {}


# ── 工具函数 ───────────────────────────────────────────────────────────────────
def _user_to_dict(user: User) -> dict:
    return {
        "id": user.id,
        "email": user.email,
        "username": user.username,
        "avatar_url": user.avatar_url,
    }


def _ok(data: dict | None = None, **extra) -> dict:
    return {"success": True, **(data or {}), **extra}


def _fail(message: str) -> dict:
    return {"success": False, "message": message}


def _oauth_result_html(token: str, user: dict, error: str = "") -> str:
    """OAuth 弹窗回调页：postMessage 给父窗口后自动关闭"""
    if error:
        payload = f'{{"type":"oauth_error","message":"{error}"}}'
    else:
        import json
        payload = json.dumps({"type": "oauth_success", "token": token, "user": user})
    return f"""<!DOCTYPE html><html><head><meta charset="UTF-8">
<title>登录中...</title>
<style>body{{font-family:sans-serif;display:flex;align-items:center;justify-content:center;
height:100vh;margin:0;background:#f1f3f4;color:#444746;}}
.box{{text-align:center;}}.spinner{{width:40px;height:40px;border:4px solid #e8f0fe;
border-top:4px solid #0b57d0;border-radius:50%;animation:spin 0.8s linear infinite;margin:0 auto 16px;}}
@keyframes spin{{to{{transform:rotate(360deg)}}}}</style></head>
<body><div class="box"><div class="spinner"></div><p>{'正在跳转...' if not error else error}</p></div>
<script>
try {{
  window.opener && window.opener.postMessage({payload}, '*');
}} catch(e) {{}}
setTimeout(function(){{ window.close(); }}, 800);
</script></body></html>"""


async def _find_or_create_oauth_user(
    db: AsyncSession,
    provider: str,
    provider_uid: str,
    email: str,
    username: str,
    avatar_url: str = "",
) -> tuple[User, str]:
    """
    通过第三方账号查找或创建用户，返回 (user, jwt_token)
    优先按 oauth_accounts 查找；否则按邮箱匹配；否则新建用户
    """
    # 1. 查已绑定的 OAuth 账号
    result = await db.execute(
        select(OAuthAccount).where(
            OAuthAccount.provider == provider,
            OAuthAccount.provider_uid == provider_uid,
        )
    )
    oauth = result.scalar_one_or_none()
    if oauth:
        user_result = await db.execute(select(User).where(User.id == oauth.user_id))
        user = user_result.scalar_one()
        token = create_access_token(user.id)
        return user, token

    # 2. 按邮箱查已有用户
    if email:
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        if user:
            # 绑定 OAuth 账号
            db.add(OAuthAccount(user_id=user.id, provider=provider, provider_uid=provider_uid))
            await db.commit()
            token = create_access_token(user.id)
            return user, token

    # 3. 新建用户
    # 确保用户名唯一：若冲突则追加随机后缀
    import random, string
    base_username = re.sub(r"[^\w\-]", "", username)[:40] or "user"
    final_username = base_username
    for _ in range(5):
        exists = await db.execute(select(User).where(User.username == final_username))
        if not exists.scalar_one_or_none():
            break
        final_username = f"{base_username}{''.join(random.choices(string.digits, k=4))}"

    new_user = User(
        email=email or f"{provider}_{provider_uid[:12]}@oauth.local",
        username=final_username,
        password_hash=hash_password(f"oauth_{provider}_{provider_uid}"),  # 不可用于密码登录
        avatar_url=avatar_url or None,
        email_verified=True,  # OAuth 用户视为已验证
    )
    db.add(new_user)
    await db.flush()

    db.add(UserSettings(user_id=new_user.id))
    db.add(Wallet(user_id=new_user.id))
    db.add(OAuthAccount(user_id=new_user.id, provider=provider, provider_uid=provider_uid))
    await db.commit()
    await db.refresh(new_user)
    token = create_access_token(new_user.id)
    return new_user, token


# ══════════════════════════════════════════════════════════════════════════════
# REST 接口
# ══════════════════════════════════════════════════════════════════════════════

class CheckEmailReq(BaseModel):
    email: EmailStr


class RegisterReq(BaseModel):
    firstName: str = Field(..., min_length=1, max_length=50)
    lastName: str = Field(..., min_length=1, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=128)


class VerifyOtpReq(BaseModel):
    email: EmailStr
    otp: str = Field(..., min_length=6, max_length=6)


class LoginReq(BaseModel):
    email: EmailStr
    password: str


@router.post("/check-email", summary="检查邮箱是否已注册（前端用）")
async def check_email(req: CheckEmailReq, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == req.email))
    exists = result.scalar_one_or_none() is not None
    return {"exists": exists}


@router.post("/register", summary="注册第一步：发送 OTP 验证码")
async def register(req: RegisterReq, db: AsyncSession = Depends(get_db)):
    # 检查邮箱是否已被注册
    result = await db.execute(select(User).where(User.email == req.email))
    if result.scalar_one_or_none():
        return _fail("该邮箱已被注册，请直接登录")

    # 暂存注册信息（内存）
    username = f"{req.firstName}{req.lastName}"
    # 检查用户名唯一性（简单去重）
    name_check = await db.execute(select(User).where(User.username == username))
    if name_check.scalar_one_or_none():
        import random, string
        username = f"{username}{''.join(random.choices(string.digits, k=4))}"

    _pending_registrations[req.email] = {
        "username": username,
        "password_hash": hash_password(req.password),
    }

    # 生成并发送 OTP
    otp_svc = OTPService(db)
    code = await otp_svc.create_otp(req.email, purpose="register")
    sent = await send_otp_email(req.email, code, purpose="register")

    if not sent:
        return _fail("验证码发送失败，请稍后重试")

    return _ok({"message": f"验证码已发送至 {req.email}"})


@router.post("/verify-otp", summary="注册第二步：验证 OTP，完成注册")
async def verify_otp(req: VerifyOtpReq, db: AsyncSession = Depends(get_db)):
    otp_svc = OTPService(db)
    valid = await otp_svc.verify_otp(req.email, req.otp, purpose="register")

    if not valid:
        return _fail("验证码无效或已过期，请重新获取")

    # 取出暂存的注册信息
    pending = _pending_registrations.pop(req.email, None)
    if not pending:
        return _fail("注册信息已过期，请重新填写")

    # 创建用户
    user = User(
        email=req.email,
        username=pending["username"],
        password_hash=pending["password_hash"],
        email_verified=True,
    )
    db.add(user)
    await db.flush()
    db.add(UserSettings(user_id=user.id))
    db.add(Wallet(user_id=user.id))
    await db.commit()
    await db.refresh(user)

    token = create_access_token(user.id)
    return _ok({"token": token, "user": _user_to_dict(user)})


@router.post("/login", summary="登录（前端格式）")
async def login_frontend(req: LoginReq, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == req.email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(req.password, user.password_hash):
        return _fail("邮箱或密码错误")
    if not user.is_active:
        return _fail("账号已停用")

    from datetime import datetime, timezone
    user.last_login = datetime.now(timezone.utc)
    await db.commit()

    token = create_access_token(user.id)
    return _ok({"token": token, "user": _user_to_dict(user)})


# ══════════════════════════════════════════════════════════════════════════════
# Google OAuth
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/google/redirect", summary="跳转 Google 授权页")
async def google_redirect():
    if not settings.google_client_id:
        return HTMLResponse(_oauth_result_html("", {}, "Google OAuth 未配置，请在 .env 中设置 GOOGLE_CLIENT_ID"))
    url = get_google_auth_url(state="toolkit")
    return RedirectResponse(url)


@router.get("/google/callback", summary="Google OAuth 回调", response_class=HTMLResponse)
async def google_callback(code: str = "", error: str = "", state: str = ""):
    if error or not code:
        return HTMLResponse(_oauth_result_html("", {}, f"Google 授权被拒绝：{error}"))

    # 换 token
    token_data = await google_exchange(code)
    if not token_data or "access_token" not in token_data:
        return HTMLResponse(_oauth_result_html("", {}, "获取 Google Token 失败"))

    # 获取用户信息
    user_info = await get_google_user_info(token_data["access_token"])
    if not user_info:
        return HTMLResponse(_oauth_result_html("", {}, "获取 Google 用户信息失败"))

    provider_uid = user_info.get("sub", "")
    email = user_info.get("email", "")
    name = user_info.get("name", "GoogleUser")
    avatar = user_info.get("picture", "")

    async with AsyncSessionLocal() as db:
        user, jwt = await _find_or_create_oauth_user(
            db, provider="google", provider_uid=provider_uid,
            email=email, username=name, avatar_url=avatar,
        )
    return HTMLResponse(_oauth_result_html(jwt, _user_to_dict(user)))


# ══════════════════════════════════════════════════════════════════════════════
# 微信 OAuth
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/wechat/redirect", summary="跳转微信授权页")
async def wechat_redirect():
    if not settings.wechat_appid:
        return HTMLResponse(_oauth_result_html("", {}, "微信 OAuth 未配置，请在 .env 中设置 WECHAT_APPID"))
    url = get_wechat_auth_url(state="toolkit")
    return RedirectResponse(url)


@router.get("/wechat/callback", summary="微信 OAuth 回调", response_class=HTMLResponse)
async def wechat_callback(code: str = "", state: str = "", error: str = ""):
    if error or not code:
        return HTMLResponse(_oauth_result_html("", {}, f"微信授权失败：{error or '未获取到 code'}"))

    token_data = await wechat_exchange(code)
    if not token_data:
        return HTMLResponse(_oauth_result_html("", {}, "获取微信 Token 失败"))

    openid = token_data.get("openid", "")
    access_token = token_data.get("access_token", "")

    user_info = await get_wechat_user_info(access_token, openid)
    if not user_info:
        # snsapi_base scope 只有 openid，无昵称，用 openid 作为用户名
        user_info = {"openid": openid, "nickname": f"微信用户_{openid[:6]}"}

    nickname = user_info.get("nickname", f"WeChatUser_{openid[:6]}")
    avatar = user_info.get("headimgurl", "")
    unionid = user_info.get("unionid", openid)  # 优先使用 unionid

    async with AsyncSessionLocal() as db:
        user, jwt = await _find_or_create_oauth_user(
            db, provider="wechat", provider_uid=unionid,
            email="",  # 微信不提供邮箱
            username=nickname, avatar_url=avatar,
        )
    return HTMLResponse(_oauth_result_html(jwt, _user_to_dict(user)))
