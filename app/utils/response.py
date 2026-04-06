"""
app/utils/response.py - 统一响应格式 & 业务错误码
"""
from typing import Any
from fastapi.responses import JSONResponse


# ─────────────────────────────────────────────
# 业务错误码定义
# 0   = 成功
# 1xxx = 用户相关
# 2xxx = 好友相关
# 3xxx = 聊天相关
# 4xxx = 游戏相关
# 5xxx = 钱包/充值相关
# 9xxx = 通用/系统错误
# ─────────────────────────────────────────────
class ErrorCode:
    SUCCESS = 0

    # 用户
    USER_NOT_FOUND = 1001
    USER_ALREADY_EXISTS = 1002
    INVALID_CREDENTIALS = 1003
    USER_INACTIVE = 1004
    OLD_PASSWORD_WRONG = 1005

    # 好友
    FRIEND_ALREADY_EXISTS = 2001
    FRIEND_REQUEST_NOT_FOUND = 2002
    FRIEND_CANNOT_ADD_SELF = 2003
    FRIEND_NOT_FOUND = 2004

    # 聊天
    CHAT_MESSAGE_NOT_FOUND = 3001

    # 游戏
    GAME_SCORE_NOT_FOUND = 4001

    # 钱包
    WALLET_NOT_FOUND = 5001
    ORDER_NOT_FOUND = 5002
    ORDER_ALREADY_PAID = 5003
    INSUFFICIENT_BALANCE = 5004

    # 通用
    UNAUTHORIZED = 9001
    FORBIDDEN = 9002
    VALIDATION_ERROR = 9003
    INTERNAL_ERROR = 9999


def ok(data: Any = None, message: str = "success") -> dict:
    """成功响应"""
    return {"code": ErrorCode.SUCCESS, "message": message, "data": data}


def fail(code: int, message: str, http_status: int = 400) -> JSONResponse:
    """失败响应"""
    return JSONResponse(
        status_code=http_status,
        content={"code": code, "message": message, "data": None},
    )
