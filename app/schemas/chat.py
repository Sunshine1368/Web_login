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
    by_user: list[dict]
