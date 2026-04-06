"""
app/schemas/wallet.py - 钱包与充值相关 Pydantic 模型
"""
from datetime import datetime
from pydantic import BaseModel, Field


class WalletOut(BaseModel):
    balance: int
    balance_yuan: float

    model_config = {"from_attributes": True}


class CreateOrderRequest(BaseModel):
    amount: int = Field(..., ge=100, description="充值金额（单位：分），最低 1 元 = 100 分")
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
