"""
app/services/user_service.py - 用户注册、登录、资料修改等业务逻辑
"""
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, UserSettings
from app.models.wallet import Wallet
from app.schemas.user import (
    RegisterRequest, UpdateProfileRequest, ChangePasswordRequest,
    UpdateSettingsRequest,
)
from app.utils.security import hash_password, verify_password, create_access_token
from app.utils.response import ErrorCode
from app.config import settings


class UserServiceError(Exception):
    def __init__(self, code: int, message: str):
        self.code = code
        self.message = message


class UserService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ─── 注册 ─────────────────────────────────────────────────────────────────
    async def register(self, req: RegisterRequest) -> User:
        # 检查邮箱唯一性
        existing = await self.db.execute(select(User).where(User.email == req.email))
        if existing.scalar_one_or_none():
            raise UserServiceError(ErrorCode.USER_ALREADY_EXISTS, "Email already registered")

        # 检查用户名唯一性
        existing_name = await self.db.execute(select(User).where(User.username == req.username))
        if existing_name.scalar_one_or_none():
            raise UserServiceError(ErrorCode.USER_ALREADY_EXISTS, "Username already taken")

        user = User(
            email=req.email,
            username=req.username,
            password_hash=hash_password(req.password),
        )
        self.db.add(user)
        await self.db.flush()  # 获取 user.id

        # 自动创建默认设置
        self.db.add(UserSettings(user_id=user.id))
        # 自动创建钱包
        self.db.add(Wallet(user_id=user.id))

        await self.db.commit()
        await self.db.refresh(user)
        return user

    # ─── 登录 ─────────────────────────────────────────────────────────────────
    async def login(self, email: str, password: str) -> tuple[User, str]:
        result = await self.db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

        if not user or not verify_password(password, user.password_hash):
            raise UserServiceError(ErrorCode.INVALID_CREDENTIALS, "Invalid email or password")
        if not user.is_active:
            raise UserServiceError(ErrorCode.USER_INACTIVE, "Account is inactive")

        # 更新最后登录时间
        user.last_login = datetime.now(timezone.utc)
        await self.db.commit()

        token = create_access_token(subject=user.id)
        return user, token

    # ─── 更新资料 ──────────────────────────────────────────────────────────────
    async def update_profile(self, user: User, req: UpdateProfileRequest) -> User:
        if req.username is not None and req.username != user.username:
            existing = await self.db.execute(
                select(User).where(User.username == req.username, User.id != user.id)
            )
            if existing.scalar_one_or_none():
                raise UserServiceError(ErrorCode.USER_ALREADY_EXISTS, "Username already taken")
            user.username = req.username

        if req.avatar_url is not None:
            user.avatar_url = req.avatar_url

        await self.db.commit()
        await self.db.refresh(user)
        return user

    # ─── 修改密码 ──────────────────────────────────────────────────────────────
    async def change_password(self, user: User, req: ChangePasswordRequest) -> None:
        if not verify_password(req.old_password, user.password_hash):
            raise UserServiceError(ErrorCode.OLD_PASSWORD_WRONG, "Old password is incorrect")
        user.password_hash = hash_password(req.new_password)
        await self.db.commit()

    # ─── 设置 ──────────────────────────────────────────────────────────────────
    async def get_settings(self, user_id: int) -> UserSettings:
        result = await self.db.execute(
            select(UserSettings).where(UserSettings.user_id == user_id)
        )
        s = result.scalar_one_or_none()
        if s is None:
            s = UserSettings(user_id=user_id)
            self.db.add(s)
            await self.db.commit()
            await self.db.refresh(s)
        return s

    async def update_settings(self, user_id: int, req: UpdateSettingsRequest) -> UserSettings:
        s = await self.get_settings(user_id)

        if req.theme is not None:
            s.theme = req.theme
        if req.language is not None:
            s.language = req.language
        # JSON 字段做合并更新（支持部分更新）
        if req.search_preferences is not None:
            s.search_preferences = {**s.search_preferences, **req.search_preferences}
        if req.notification_settings is not None:
            s.notification_settings = {**s.notification_settings, **req.notification_settings}
        if req.other_settings is not None:
            s.other_settings = {**s.other_settings, **req.other_settings}

        await self.db.commit()
        await self.db.refresh(s)
        return s
