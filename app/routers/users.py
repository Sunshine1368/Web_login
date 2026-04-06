"""
app/routers/users.py - 用户资料 & 设置路由
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db, get_current_user
from app.models.user import User
from app.schemas.user import (
    UserOut, UpdateProfileRequest, ChangePasswordRequest,
    UserSettingsOut, UpdateSettingsRequest,
)
from app.services.user_service import UserService, UserServiceError
from app.utils.response import ok, fail

router = APIRouter(prefix="/api/users", tags=["Users"])


@router.get("/me", summary="获取个人信息")
async def get_me(current_user: User = Depends(get_current_user)):
    return ok(UserOut.model_validate(current_user))


@router.put("/me", summary="更新个人资料")
async def update_me(
    req: UpdateProfileRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = UserService(db)
    try:
        user = await svc.update_profile(current_user, req)
    except UserServiceError as e:
        return fail(e.code, e.message)
    return ok(UserOut.model_validate(user))


@router.put("/me/password", summary="修改密码")
async def change_password(
    req: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = UserService(db)
    try:
        await svc.change_password(current_user, req)
    except UserServiceError as e:
        return fail(e.code, e.message)
    return ok(message="Password updated successfully")


@router.get("/me/settings", summary="获取用户设置")
async def get_settings(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = UserService(db)
    s = await svc.get_settings(current_user.id)
    return ok(UserSettingsOut.model_validate(s))


@router.put("/me/settings", summary="更新用户设置（支持部分更新）")
async def update_settings(
    req: UpdateSettingsRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = UserService(db)
    s = await svc.update_settings(current_user.id, req)
    return ok(UserSettingsOut.model_validate(s))
