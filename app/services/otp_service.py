"""
app/services/otp_service.py - OTP 验证码生成、存储、校验
"""
import random
import string
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.otp import OTPCode

OTP_EXPIRE_MINUTES = 10


class OTPService:
    def __init__(self, db: AsyncSession):
        self.db = db

    def _generate_code(self) -> str:
        return "".join(random.choices(string.digits, k=6))

    async def create_otp(self, email: str, purpose: str = "register") -> str:
        """
        为邮箱生成新 OTP，废弃同邮箱同用途的旧码
        :returns: 6 位验证码字符串
        """
        # 废弃旧的未使用验证码
        old_result = await self.db.execute(
            select(OTPCode).where(
                OTPCode.email == email,
                OTPCode.purpose == purpose,
                OTPCode.is_used == False,
            )
        )
        for old in old_result.scalars().all():
            old.is_used = True

        code = self._generate_code()
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=OTP_EXPIRE_MINUTES)

        otp = OTPCode(
            email=email,
            code=code,
            purpose=purpose,
            is_used=False,
            expires_at=expires_at,
        )
        self.db.add(otp)
        await self.db.commit()
        return code

    async def verify_otp(self, email: str, code: str, purpose: str = "register") -> bool:
        """
        校验 OTP，通过后标记为已使用
        :returns: True 有效，False 无效/过期/已用
        """
        result = await self.db.execute(
            select(OTPCode).where(
                OTPCode.email == email,
                OTPCode.code == code,
                OTPCode.purpose == purpose,
                OTPCode.is_used == False,
            ).order_by(OTPCode.created_at.desc())
        )
        otp = result.scalars().first()

        if not otp:
            return False

        now = datetime.now(timezone.utc)
        # 兼容无时区的 datetime（SQLite）
        expires = otp.expires_at
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)

        if now > expires:
            otp.is_used = True
            await self.db.commit()
            return False

        otp.is_used = True
        await self.db.commit()
        return True
