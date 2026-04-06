"""
app/dependencies.py - FastAPI 依赖注入：数据库会话、当前用户
"""
from typing import AsyncGenerator

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.models.user import User
from app.utils.security import decode_access_token
from app.utils.response import ErrorCode

bearer_scheme = HTTPBearer()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """提供异步数据库会话，请求结束后自动关闭"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    从 Authorization: Bearer <token> 中解析并验证 JWT，
    返回当前登录用户。
    """
    token = credentials.credentials
    try:
        payload = decode_access_token(token)
        user_id: str | None = payload.get("sub")
        if user_id is None:
            raise ValueError("Missing sub claim")
    except (JWTError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": ErrorCode.UNAUTHORIZED, "message": "Invalid or expired token"},
        )

    from sqlalchemy import select
    result = await db.execute(select(User).where(User.id == int(user_id)))
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": ErrorCode.USER_NOT_FOUND, "message": "User not found"},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": ErrorCode.USER_INACTIVE, "message": "User account is inactive"},
        )
    return user
