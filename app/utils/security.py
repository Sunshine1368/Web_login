"""
app/utils/security.py - JWT 创建/验证 & bcrypt 密码工具
"""
from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
from jose import JWTError, jwt

from app.config import settings


def hash_password(plain: str) -> str:
    """将明文密码转为 bcrypt 哈希（返回字符串）"""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(plain.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """验证明文密码与 bcrypt 哈希是否匹配"""
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


def create_access_token(subject: int | str, extra: dict[str, Any] | None = None) -> str:
    """
    生成 JWT access token
    :param subject: 通常是用户 ID
    :param extra: 额外附加到 payload 的字段
    """
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    payload: dict[str, Any] = {
        "sub": str(subject),
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict[str, Any]:
    """
    解码并验证 JWT，返回 payload
    :raises JWTError: token 无效或过期
    """
    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
