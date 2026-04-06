"""
app/models/game.py - 小游戏积分表
"""
from datetime import datetime
from sqlalchemy import Integer, String, JSON, DateTime, ForeignKey, Index, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class GameScore(Base):
    __tablename__ = "game_scores"
    __table_args__ = (
        Index("ix_game_scores_game_score", "game_name", "score"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    game_name: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    extra_data: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), nullable=False)

    user: Mapped["User"] = relationship("User", back_populates="game_scores")
