"""
app/routers/recharge.py - 钱包 & 充值路由
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db, get_current_user
from app.models.user import User
from app.schemas.wallet import CreateOrderRequest, OrderOut, WalletOut, RechargeCallbackRequest
from app.services.wallet_service import WalletService, WalletServiceError
from app.utils.response import ok, fail

router = APIRouter(tags=["Wallet & Recharge"])


@router.get("/api/wallet/balance", summary="查询钱包余额")
async def get_balance(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = WalletService(db)
    try:
        wallet = await svc.get_balance(current_user.id)
    except WalletServiceError as e:
        return fail(e.code, e.message)
    return ok(WalletOut(
        balance=wallet.balance,
        balance_yuan=round(wallet.balance / 100, 2),
    ))


@router.post("/api/recharge/order", summary="创建充值订单")
async def create_order(
    req: CreateOrderRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = WalletService(db)
    try:
        order = await svc.create_order(current_user.id, req)
    except WalletServiceError as e:
        return fail(e.code, e.message)
    return ok(OrderOut.model_validate(order), "Order created")


@router.post("/api/recharge/callback", summary="模拟支付回调（将订单标记为成功并充值）")
async def recharge_callback(
    req: RechargeCallbackRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    ⚠️  生产环境中此接口应由支付平台异步回调，
    需验证签名并设为内部接口，不对外暴露。
    此处仅用于本地测试模拟。
    """
    svc = WalletService(db)
    try:
        order = await svc.process_callback(req.order_no)
    except WalletServiceError as e:
        return fail(e.code, e.message)
    return ok(OrderOut.model_validate(order), "Recharge successful")


@router.get("/api/recharge/orders", summary="查询充值历史")
async def get_orders(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = WalletService(db)
    orders = await svc.get_orders(current_user.id)
    return ok([OrderOut.model_validate(o) for o in orders])
