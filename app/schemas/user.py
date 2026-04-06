"""
app/schemas/user.py - 用户相关 Pydantic 模型（请求体 & 响应体）
"""
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field, field_validator


# ── 注册 ──────────────────────────────────────
class RegisterRequest(BaseModel):
    email: EmailStr
    username: str = Field(..., min_length=2, max_length=50)
    password: str = Field(..., min_length=6, max_length=128)

    @field_validator("username")
    @classmethod
    def username_alphanumeric(cls, v: str) -> str:
        if not all(c.isalnum() or c in "_-" for c in v):
            raise ValueError("Username may only contain letters, numbers, _ and -")
        return v


# ── 登录 ──────────────────────────────────────
class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # 秒


# ── 用户信息 ───────────────────────────────────
class UserOut(BaseModel):
    id: int
    email: str
    username: str
    avatar_url: str | None
    is_active: bool
    email_verified: bool
    created_at: datetime
    last_login: datetime | None

    model_config = {"from_attributes": True}


class LoginResponse(BaseModel):
    token: TokenResponse
    user: UserOut


# ── 更新资料 ───────────────────────────────────
class UpdateProfileRequest(BaseModel):
    username: str | None = Field(None, min_length=2, max_length=50)
    avatar_url: str | None = Field(None, max_length=500)


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str = Field(..., min_length=6, max_length=128)


# ── 用户设置 ───────────────────────────────────
class UserSettingsOut(BaseModel):
    theme: str
    language: str
    search_preferences: dict
    notification_settings: dict
    other_settings: dict

    model_config = {"from_attributes": True}


class UpdateSettingsRequest(BaseModel):
    theme: str | None = Field(None, pattern="^(light|dark|system)$")
    language: str | None = Field(None, max_length=10)
    search_preferences: dict | None = None
    notification_settings: dict | None = None
    other_settings: dict | None = None
