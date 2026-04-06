"""
app/models/otp.py - OTP 验证码表 & 待注册用户暂存表
"""
from datetime import datetime
from sqlalchemy import Integer, String, DateTime, Boolean, Text, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class OTPCode(Base):
    """邮箱验证码，10 分钟有效，使用后标记 is_used"""
    __tablename__ = "otp_codes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(6), nullable=False)
    purpose: Mapped[str] = mapped_column(String(20), default="register", nullable=False)
    # register / reset_password
    is_used: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), nullable=False)


class OAuthAccount(Base):
    """第三方 OAuth 账号绑定（Google / WeChat）"""
    __tablename__ = "oauth_accounts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    provider: Mapped[str] = mapped_column(String(20), nullable=False)   # google / wechat
    provider_uid: Mapped[str] = mapped_column(String(128), nullable=False)  # Google sub / WeChat openid
    access_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), nullable=False)
