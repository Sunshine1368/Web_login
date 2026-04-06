"""
app/services/game_service.py - 游戏积分业务逻辑
"""
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.game import GameScore
from app.models.user import User
from app.schemas.game import SubmitScoreRequest, LeaderboardEntry


class GameService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ─── 提交得分 ──────────────────────────────────────────────────────────────
    async def submit_score(self, user_id: int, req: SubmitScoreRequest) -> GameScore:
        score = GameScore(
            user_id=user_id,
            game_name=req.game_name,
            score=req.score,
            extra_data=req.extra_data,
        )
        self.db.add(score)
        await self.db.commit()
        await self.db.refresh(score)
        return score

    # ─── 用户个人得分列表 ──────────────────────────────────────────────────────
    async def get_user_scores(
        self, user_id: int, game_name: str | None = None
    ) -> list[GameScore]:
        stmt = select(GameScore).where(GameScore.user_id == user_id)
        if game_name:
            stmt = stmt.where(GameScore.game_name == game_name)
        stmt = stmt.order_by(GameScore.created_at.desc())
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    # ─── 排行榜（某游戏 Top N，取每个用户的最高分）────────────────────────────
    async def get_leaderboard(self, game_name: str, top_n: int = 20) -> list[LeaderboardEntry]:
        # 子查询：每个用户在该游戏的最高分
        subq = (
            select(
                GameScore.user_id,
                func.max(GameScore.score).label("best_score"),
                func.max(GameScore.created_at).label("best_at"),
            )
            .where(GameScore.game_name == game_name)
            .group_by(GameScore.user_id)
            .subquery()
        )

        result = await self.db.execute(
            select(
                subq.c.user_id,
                subq.c.best_score,
                subq.c.best_at,
                User.username,
            )
            .join(User, User.id == subq.c.user_id)
            .order_by(subq.c.best_score.desc())
            .limit(top_n)
        )
        rows = result.all()
        return [
            LeaderboardEntry(
                rank=i + 1,
                user_id=row.user_id,
                username=row.username,
                score=row.best_score,
                created_at=row.best_at,
            )
            for i, row in enumerate(rows)
        ]
