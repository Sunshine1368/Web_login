"""
app/schemas/chat.py - 聊天消息相关 Pydantic 模型
"""
from datetime import datetime
from pydantic import BaseModel


class ChatMessageOut(BaseModel):
    id: int
    from_user_id: int
    to_user_id: int
    message: str
    is_read: bool
    read_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class UnreadCountOut(BaseModel):
    total: int
    by_user: list[dict]  # [{"from_user_id": 1, "count": 5}]


# ──────────────────────────────────────────────────────────────────────────────
"""
app/schemas/game.py - 游戏积分相关 Pydantic 模型
"""
from pydantic import BaseModel, Field


class SubmitScoreRequest(BaseModel):
    game_name: str = Field(..., min_length=1, max_length=50)
    score: int = Field(..., ge=0)
    extra_data: dict = {}


class GameScoreOut(BaseModel):
    id: int
    user_id: int
    game_name: str
    score: int
    extra_data: dict
    created_at: datetime

    model_config = {"from_attributes": True}


class LeaderboardEntry(BaseModel):
    rank: int
    user_id: int
    username: str
    score: int
    created_at: datetime


# ──────────────────────────────────────────────────────────────────────────────
"""
app/schemas/wallet.py - 钱包与充值相关 Pydantic 模型
"""
from pydantic import BaseModel, Field


class WalletOut(BaseModel):
    balance: int  # 分
    balance_yuan: float  # 元（方便展示）

    model_config = {"from_attributes": True}


class CreateOrderRequest(BaseModel):
    amount: int = Field(..., ge=100, description="充值金额（单位：分），最低 1 元")
    payment_method: str | None = Field(None, max_length=50)


class OrderOut(BaseModel):
    id: int
    order_no: str
    amount: int
    status: str
    payment_method: str | None
    paid_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class RechargeCallbackRequest(BaseModel):
    order_no: str
