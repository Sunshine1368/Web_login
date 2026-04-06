"""
app/routers/friends.py - 好友系统路由
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db, get_current_user
from app.models.user import User
from app.schemas.friend import FriendRequestCreate, FriendRequestAction, FriendOut
from app.services.friend_service import FriendService, FriendServiceError
from app.utils.response import ok, fail

router = APIRouter(prefix="/api/friends", tags=["Friends"])


@router.post("/request", summary="发送好友请求")
async def send_request(
    req: FriendRequestCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = FriendService(db)
    try:
        data = await svc.send_request(current_user, req.friend_id, req.email)
    except FriendServiceError as e:
        return fail(e.code, e.message)
    return ok(FriendOut(**data), "Friend request sent")


@router.put("/request/{request_id}", summary="处理好友申请（accept/reject/block）")
async def handle_request(
    request_id: int,
    req: FriendRequestAction,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = FriendService(db)
    try:
        data = await svc.handle_request(current_user, request_id, req.action)
    except FriendServiceError as e:
        return fail(e.code, e.message)
    return ok(FriendOut(**data))


@router.get("", summary="获取好友列表")
async def get_friends(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = FriendService(db)
    records = await svc.get_friends(current_user.id)
    return ok([FriendOut(**r) for r in records])


@router.get("/pending", summary="收到的好友申请")
async def get_pending(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = FriendService(db)
    records = await svc.get_pending_requests(current_user.id)
    return ok([FriendOut(**r) for r in records])


@router.delete("/{friend_id}", summary="删除好友")
async def delete_friend(
    friend_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = FriendService(db)
    try:
        await svc.delete_friend(current_user.id, friend_id)
    except FriendServiceError as e:
        return fail(e.code, e.message)
    return ok(message="Friend removed")
