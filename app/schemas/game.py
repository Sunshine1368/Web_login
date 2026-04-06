"""
app/schemas/game.py - 游戏积分相关 Pydantic 模型
"""
from datetime import datetime
from pydantic import BaseModel, Field


class SubmitScoreRequest(BaseModel):
    game_name: str = Field(..., min_length=1, max_length=50)
    score: int = Field(..., ge=0)
    extra_data: dict = {}


class GameScoreOut(BaseModel):
    id: int
    user_id: int
    game_name: str
    score: int
    extra_data: dict
    created_at: datetime

    model_config = {"from_attributes": True}


class LeaderboardEntry(BaseModel):
    rank: int
    user_id: int
    username: str
    score: int
    created_at: datetime
