"""
app/models/__init__.py - 统一导出所有模型，供 Alembic 自动检测
"""
from app.models.user import User, UserSettings
from app.models.friend import Friend
from app.models.chat import ChatMessage
from app.models.game import GameScore
from app.models.wallet import Wallet, RechargeOrder
from app.models.otp import OTPCode, OAuthAccount

__all__ = [
    "User", "UserSettings",
    "Friend",
    "ChatMessage",
    "GameScore",
    "Wallet", "RechargeOrder",
    "OTPCode", "OAuthAccount",
]
