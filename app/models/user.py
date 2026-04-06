"""
app/models/user.py - 用户表 & 用户设置表
"""
from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, Integer, JSON, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    last_login: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # 关联关系
    settings: Mapped["UserSettings"] = relationship("UserSettings", back_populates="user", uselist=False, cascade="all, delete-orphan")
    wallet: Mapped["Wallet"] = relationship("Wallet", back_populates="user", uselist=False, cascade="all, delete-orphan")
    game_scores: Mapped[list["GameScore"]] = relationship("GameScore", back_populates="user", cascade="all, delete-orphan")
    sent_messages: Mapped[list["ChatMessage"]] = relationship("ChatMessage", foreign_keys="ChatMessage.from_user_id", back_populates="sender")
    received_messages: Mapped[list["ChatMessage"]] = relationship("ChatMessage", foreign_keys="ChatMessage.to_user_id", back_populates="receiver")
    recharge_orders: Mapped[list["RechargeOrder"]] = relationship("RechargeOrder", back_populates="user")

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email}>"


class UserSettings(Base):
    __tablename__ = "user_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    theme: Mapped[str] = mapped_column(String(20), default="light", nullable=False)
    language: Mapped[str] = mapped_column(String(10), default="en", nullable=False)
    search_preferences: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    notification_settings: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    other_settings: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    user: Mapped["User"] = relationship("User", back_populates="settings")
