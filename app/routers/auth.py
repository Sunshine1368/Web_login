"""
app/routers/auth.py - 注册 / 登录路由
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.schemas.user import RegisterRequest, LoginRequest, LoginResponse, UserOut, TokenResponse
from app.services.user_service import UserService, UserServiceError
from app.utils.response import ok, fail
from app.config import settings

router = APIRouter(prefix="/api/auth", tags=["Auth"])


@router.post("/register", summary="用户注册")
async def register(req: RegisterRequest, db: AsyncSession = Depends(get_db)):
    svc = UserService(db)
    try:
        user = await svc.register(req)
    except UserServiceError as e:
        return fail(e.code, e.message)
    return ok(UserOut.model_validate(user), "Registration successful")


@router.post("/login", summary="用户登录")
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    svc = UserService(db)
    try:
        user, token = await svc.login(req.email, req.password)
    except UserServiceError as e:
        return fail(e.code, e.message, http_status=401)

    return ok(
        LoginResponse(
            token=TokenResponse(
                access_token=token,
                token_type="bearer",
                expires_in=settings.access_token_expire_minutes * 60,
            ),
            user=UserOut.model_validate(user),
        ),
        "Login successful",
    )
