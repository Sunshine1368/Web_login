"""
app/services/wallet_service.py - 钱包与充值业务逻辑（含乐观锁）
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.wallet import Wallet, RechargeOrder
from app.schemas.other import CreateOrderRequest
from app.utils.response import ErrorCode


class WalletServiceError(Exception):
    def __init__(self, code: int, message: str):
        self.code = code
        self.message = message


class WalletService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def _get_wallet(self, user_id: int) -> Wallet:
        result = await self.db.execute(select(Wallet).where(Wallet.user_id == user_id))
        wallet = result.scalar_one_or_none()
        if not wallet:
            raise WalletServiceError(ErrorCode.WALLET_NOT_FOUND, "Wallet not found")
        return wallet

    # ─── 查询余额 ──────────────────────────────────────────────────────────────
    async def get_balance(self, user_id: int) -> Wallet:
        return await self._get_wallet(user_id)

    # ─── 创建充值订单 ──────────────────────────────────────────────────────────
    async def create_order(self, user_id: int, req: CreateOrderRequest) -> RechargeOrder:
        # 生成唯一订单号：MG + 时间戳 + UUID 前8位
        order_no = f"MG{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}{uuid.uuid4().hex[:8].upper()}"

        order = RechargeOrder(
            user_id=user_id,
            order_no=order_no,
            amount=req.amount,
            payment_method=req.payment_method,
            status="pending",
        )
        self.db.add(order)
        await self.db.commit()
        await self.db.refresh(order)
        return order

    # ─── 模拟支付回调（乐观锁防并发）──────────────────────────────────────────
    async def process_callback(self, order_no: str) -> RechargeOrder:
        """
        模拟支付成功回调：
        1. 查订单，校验状态
        2. 使用乐观锁更新钱包余额（version 字段）
        3. 更新订单状态
        """
        # 查订单
        order_result = await self.db.execute(
            select(RechargeOrder).where(RechargeOrder.order_no == order_no)
        )
        order = order_result.scalar_one_or_none()
        if not order:
            raise WalletServiceError(ErrorCode.ORDER_NOT_FOUND, "Order not found")
        if order.status != "pending":
            raise WalletServiceError(ErrorCode.ORDER_ALREADY_PAID, "Order already processed")

        # 获取钱包（带版本号，用于乐观锁）
        wallet = await self._get_wallet(order.user_id)
        current_version = wallet.version

        # 乐观锁更新：只有 version 匹配时才更新
        from sqlalchemy import update
        update_result = await self.db.execute(
            update(Wallet)
            .where(Wallet.user_id == order.user_id, Wallet.version == current_version)
            .values(
                balance=Wallet.balance + order.amount,
                version=current_version + 1,
                updated_at=datetime.now(timezone.utc),
            )
        )
        if update_result.rowcount == 0:
            # 并发冲突，回滚后抛出
            await self.db.rollback()
            raise WalletServiceError(ErrorCode.INTERNAL_ERROR, "Concurrent update conflict, please retry")

        # 更新订单
        order.status = "success"
        order.paid_at = datetime.now(timezone.utc)
        await self.db.commit()
        await self.db.refresh(order)
        return order

    # ─── 充值历史 ──────────────────────────────────────────────────────────────
    async def get_orders(self, user_id: int) -> list[RechargeOrder]:
        result = await self.db.execute(
            select(RechargeOrder)
            .where(RechargeOrder.user_id == user_id)
            .order_by(RechargeOrder.created_at.desc())
        )
        return list(result.scalars().all())
