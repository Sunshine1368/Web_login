"""
app/services/friend_service.py - 好友系统业务逻辑
"""
from datetime import datetime, timezone

from sqlalchemy import select, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.friend import Friend
from app.models.user import User
from app.utils.response import ErrorCode


class FriendServiceError(Exception):
    def __init__(self, code: int, message: str):
        self.code = code
        self.message = message


def _friend_to_dict(record: Friend) -> dict:
    """在 session 内将 Friend ORM 对象转为 dict（避免懒加载问题）"""
    d = {
        "id": record.id,
        "user_id": record.user_id,
        "friend_id": record.friend_id,
        "status": record.status,
        "action_user_id": record.action_user_id,
        "created_at": record.created_at,
        "updated_at": record.updated_at,
        "requester_username": None,
        "requester_avatar": None,
        "receiver_username": None,
        "receiver_avatar": None,
    }
    # 只有在 selectinload 已加载时才访问
    try:
        if record.requester:
            d["requester_username"] = record.requester.username
            d["requester_avatar"] = record.requester.avatar_url
    except Exception:
        pass
    try:
        if record.receiver:
            d["receiver_username"] = record.receiver.username
            d["receiver_avatar"] = record.receiver.avatar_url
    except Exception:
        pass
    return d


class FriendService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ─── 查找用户（通过 ID 或邮箱）─────────────────────────────────────────────
    async def _get_target_user(self, friend_id: int | None, email: str | None) -> User:
        if friend_id:
            result = await self.db.execute(select(User).where(User.id == friend_id))
        elif email:
            result = await self.db.execute(select(User).where(User.email == email))
        else:
            raise FriendServiceError(ErrorCode.USER_NOT_FOUND, "Provide friend_id or email")
        user = result.scalar_one_or_none()
        if not user:
            raise FriendServiceError(ErrorCode.USER_NOT_FOUND, "Target user not found")
        return user

    # ─── 发送好友请求 ──────────────────────────────────────────────────────────
    async def send_request(self, requester: User, friend_id: int | None, email: str | None) -> Friend:
        target = await self._get_target_user(friend_id, email)

        if target.id == requester.id:
            raise FriendServiceError(ErrorCode.FRIEND_CANNOT_ADD_SELF, "Cannot add yourself")

        # 检查双向是否已存在关系
        existing = await self.db.execute(
            select(Friend).where(
                or_(
                    and_(Friend.user_id == requester.id, Friend.friend_id == target.id),
                    and_(Friend.user_id == target.id, Friend.friend_id == requester.id),
                )
            )
        )
        record = existing.scalar_one_or_none()
        if record:
            if record.status == "accepted":
                raise FriendServiceError(ErrorCode.FRIEND_ALREADY_EXISTS, "Already friends")
            if record.status == "pending":
                raise FriendServiceError(ErrorCode.FRIEND_ALREADY_EXISTS, "Request already pending")

        friend = Friend(
            user_id=requester.id,
            friend_id=target.id,
            status="pending",
            action_user_id=requester.id,
        )
        self.db.add(friend)
        await self.db.commit()
        await self.db.refresh(friend)
        return _friend_to_dict(friend)

    # ─── 处理好友请求（accept / reject / block）────────────────────────────────
    async def handle_request(self, current_user: User, request_id: int, action: str) -> dict:
        result = await self.db.execute(
            select(Friend).where(
                Friend.id == request_id,
                Friend.friend_id == current_user.id,  # 只有接收方可以操作
                Friend.status == "pending",
            )
        )
        record = result.scalar_one_or_none()
        if not record:
            raise FriendServiceError(ErrorCode.FRIEND_REQUEST_NOT_FOUND, "Friend request not found")

        if action == "accept":
            record.status = "accepted"
        elif action == "reject":
            record.status = "rejected"
        elif action == "block":
            record.status = "blocked"
        else:
            raise FriendServiceError(ErrorCode.VALIDATION_ERROR, "Invalid action")

        record.action_user_id = current_user.id
        record.updated_at = datetime.now(timezone.utc)
        await self.db.commit()
        await self.db.refresh(record)
        return _friend_to_dict(record)

    # ─── 获取好友列表（status=accepted）────────────────────────────────────────
    async def get_friends(self, user_id: int) -> list[dict]:
        result = await self.db.execute(
            select(Friend)
            .options(selectinload(Friend.requester), selectinload(Friend.receiver))
            .where(
                or_(
                    and_(Friend.user_id == user_id, Friend.status == "accepted"),
                    and_(Friend.friend_id == user_id, Friend.status == "accepted"),
                )
            )
        )
        return [_friend_to_dict(r) for r in result.scalars().all()]

    # ─── 收到的待处理申请 ──────────────────────────────────────────────────────
    async def get_pending_requests(self, user_id: int) -> list[dict]:
        result = await self.db.execute(
            select(Friend)
            .options(selectinload(Friend.requester), selectinload(Friend.receiver))
            .where(Friend.friend_id == user_id, Friend.status == "pending")
        )
        return [_friend_to_dict(r) for r in result.scalars().all()]

    # ─── 删除好友 ──────────────────────────────────────────────────────────────
    async def delete_friend(self, user_id: int, friend_id: int) -> None:
        result = await self.db.execute(
            select(Friend).where(
                or_(
                    and_(Friend.user_id == user_id, Friend.friend_id == friend_id),
                    and_(Friend.user_id == friend_id, Friend.friend_id == user_id),
                ),
                Friend.status == "accepted",
            )
        )
        record = result.scalar_one_or_none()
        if not record:
            raise FriendServiceError(ErrorCode.FRIEND_NOT_FOUND, "Friend relationship not found")

        await self.db.delete(record)
        await self.db.commit()

    # ─── 校验是否为好友（供聊天鉴权用）────────────────────────────────────────
    async def are_friends(self, user_id: int, other_id: int) -> bool:
        result = await self.db.execute(
            select(Friend).where(
                or_(
                    and_(Friend.user_id == user_id, Friend.friend_id == other_id),
                    and_(Friend.user_id == other_id, Friend.friend_id == user_id),
                ),
                Friend.status == "accepted",
            )
        )
        return result.scalar_one_or_none() is not None
