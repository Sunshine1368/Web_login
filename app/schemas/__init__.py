"""
app/schemas/__init__.py - 统一导出所有 Pydantic 模型
"""
from app.schemas.user import (
    RegisterRequest,
    LoginRequest,
    TokenResponse,
    UserOut,
    LoginResponse,
    UpdateProfileRequest,
    ChangePasswordRequest,
    UserSettingsOut,
    UpdateSettingsRequest,
)
from app.schemas.friend import FriendRequestCreate, FriendRequestAction, FriendOut
from app.schemas.chat import ChatMessageOut, UnreadCountOut
from app.schemas.game import SubmitScoreRequest, GameScoreOut, LeaderboardEntry
from app.schemas.wallet import WalletOut, CreateOrderRequest, OrderOut, RechargeCallbackRequest
