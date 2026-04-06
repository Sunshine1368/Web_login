"""
app/routers/games.py - 游戏积分路由
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db, get_current_user
from app.models.user import User
from app.schemas.game import SubmitScoreRequest, GameScoreOut, LeaderboardEntry
from app.services.game_service import GameService
from app.utils.response import ok

router = APIRouter(prefix="/api/games", tags=["Games"])


@router.post("/score", summary="提交游戏得分")
async def submit_score(
    req: SubmitScoreRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = GameService(db)
    score = await svc.submit_score(current_user.id, req)
    return ok(GameScoreOut.model_validate(score), "Score submitted")


@router.get("/scores", summary="获取个人游戏得分记录")
async def get_scores(
    game_name: str | None = Query(None, description="按游戏名过滤"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = GameService(db)
    scores = await svc.get_user_scores(current_user.id, game_name)
    return ok([GameScoreOut.model_validate(s) for s in scores])


@router.get("/leaderboard/{game_name}", summary="获取某游戏排行榜")
async def leaderboard(
    game_name: str,
    top_n: int = Query(20, ge=1, le=100, description="显示前 N 名"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = GameService(db)
    board = await svc.get_leaderboard(game_name, top_n)
    return ok(board)
