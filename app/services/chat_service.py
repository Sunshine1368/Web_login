"""
app/services/chat_service.py - 聊天消息业务逻辑（持久化、查询、标记已读）
"""
from datetime import datetime, timezone

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chat import ChatMessage


class ChatService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ─── 保存消息到数据库 ──────────────────────────────────────────────────────
    async def save_message(self, from_user_id: int, to_user_id: int, message: str) -> ChatMessage:
        msg = ChatMessage(
            from_user_id=from_user_id,
            to_user_id=to_user_id,
            message=message,
        )
        self.db.add(msg)
        await self.db.commit()
        await self.db.refresh(msg)
        return msg

    # ─── 获取与某用户的历史消息（分页，按时间倒序）────────────────────────────
    async def get_history(
        self, user_id: int, other_user_id: int, page: int = 1, page_size: int = 50
    ) -> tuple[list[ChatMessage], int]:
        base_cond = and_(
            # 双向消息都要查出
            (
                (ChatMessage.from_user_id == user_id) & (ChatMessage.to_user_id == other_user_id)
            )
            | (
                (ChatMessage.from_user_id == other_user_id) & (ChatMessage.to_user_id == user_id)
            )
        )

        # 总数
        count_result = await self.db.execute(
            select(func.count()).where(base_cond)
        )
        total = count_result.scalar_one()

        # 分页
        offset = (page - 1) * page_size
        result = await self.db.execute(
            select(ChatMessage)
            .where(base_cond)
            .order_by(ChatMessage.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        messages = list(result.scalars().all())
        return messages, total

    # ─── 未读消息总数 ──────────────────────────────────────────────────────────
    async def get_unread_count(self, user_id: int) -> dict:
        # 按发送人分组统计
        result = await self.db.execute(
            select(ChatMessage.from_user_id, func.count().label("cnt"))
            .where(ChatMessage.to_user_id == user_id, ChatMessage.is_read == False)
            .group_by(ChatMessage.from_user_id)
        )
        rows = result.all()
        by_user = [{"from_user_id": r.from_user_id, "count": r.cnt} for r in rows]
        total = sum(r["count"] for r in by_user)
        return {"total": total, "by_user": by_user}

    # ─── 标记与某人的所有消息为已读 ────────────────────────────────────────────
    async def mark_read(self, to_user_id: int, from_user_id: int) -> int:
        """返回实际标记的消息数量"""
        result = await self.db.execute(
            select(ChatMessage).where(
                ChatMessage.to_user_id == to_user_id,
                ChatMessage.from_user_id == from_user_id,
                ChatMessage.is_read == False,
            )
        )
        msgs = result.scalars().all()
        now = datetime.now(timezone.utc)
        for msg in msgs:
            msg.is_read = True
            msg.read_at = now
        await self.db.commit()
        return len(msgs)

    # ─── 获取所有未读的离线消息（用于上线后推送）──────────────────────────────
    async def get_offline_messages(self, user_id: int) -> list[ChatMessage]:
        result = await self.db.execute(
            select(ChatMessage)
            .where(ChatMessage.to_user_id == user_id, ChatMessage.is_read == False)
            .order_by(ChatMessage.created_at.asc())
        )
        return list(result.scalars().all())
