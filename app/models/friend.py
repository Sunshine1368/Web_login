"""
app/models/friend.py - 好友关系表
"""
from datetime import datetime
from sqlalchemy import Integer, String, DateTime, ForeignKey, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class Friend(Base):
    __tablename__ = "friends"
    __table_args__ = (
        UniqueConstraint("user_id", "friend_id", name="uq_friends_pair"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    friend_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    # pending / accepted / blocked / rejected
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    action_user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    # 关联
    requester: Mapped["User"] = relationship("User", foreign_keys=[user_id])
    receiver: Mapped["User"] = relationship("User", foreign_keys=[friend_id])
