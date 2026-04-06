"""
app/models/chat.py - 聊天消息表
"""
from datetime import datetime
from sqlalchemy import Integer, Text, Boolean, DateTime, ForeignKey, Index, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class ChatMessage(Base):
    __tablename__ = "chat_messages"
    __table_args__ = (
        # 优化未读消息查询的复合索引
        Index("ix_chat_messages_to_unread", "to_user_id", "is_read", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    from_user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    to_user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    read_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), nullable=False)

    sender: Mapped["User"] = relationship("User", foreign_keys=[from_user_id], back_populates="sent_messages")
    receiver: Mapped["User"] = relationship("User", foreign_keys=[to_user_id], back_populates="received_messages")
