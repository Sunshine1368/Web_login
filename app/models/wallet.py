"""
app/models/wallet.py - 钱包表 & 充值订单表
"""
from datetime import datetime
from sqlalchemy import Integer, String, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class Wallet(Base):
    __tablename__ = "wallets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    # 余额以"分"为单位，避免浮点精度问题
    balance: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    # 乐观锁版本号，防止并发扣款
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    user: Mapped["User"] = relationship("User", back_populates="wallet")


class RechargeOrder(Base):
    __tablename__ = "recharge_orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    order_no: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    # 充值金额（分）
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    # pending / success / failed
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    # 预留：alipay / wechat / stripe 等
    payment_method: Mapped[str | None] = mapped_column(String(50), nullable=True)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    user: Mapped["User"] = relationship("User", back_populates="recharge_orders")
