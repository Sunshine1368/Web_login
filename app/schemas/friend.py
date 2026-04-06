"""
app/schemas/friend.py - 好友相关 Pydantic 模型
"""
from datetime import datetime
from pydantic import BaseModel


class FriendRequestCreate(BaseModel):
    friend_id: int | None = None
    email: str | None = None  # 通过邮箱搜索好友（二选一）


class FriendRequestAction(BaseModel):
    action: str  # "accept" | "reject" | "block"


class FriendOut(BaseModel):
    id: int
    user_id: int
    friend_id: int
    status: str
    action_user_id: int
    created_at: datetime
    updated_at: datetime
    # 对方信息（扁平字段，避免懒加载问题）
    requester_username: str | None = None
    requester_avatar: str | None = None
    receiver_username: str | None = None
    receiver_avatar: str | None = None

    model_config = {"from_attributes": True}
