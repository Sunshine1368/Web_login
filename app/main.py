"""
app/main.py - FastAPI 应用入口：注册路由、中间件、全局异常处理
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from app.config import settings
from app.database import engine, Base
from app.routers import auth, users, friends, chat, games, recharge
from app.routers.auth_ext import router as auth_ext_router
from app.websocket.chat_ws import ws_router
from app.utils.response import ErrorCode

logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用启动时自动创建数据库表（开发便利，生产应改用 Alembic 迁移）"""
    logger.info("Starting up MiniGoogle backend...")
    async with engine.begin() as conn:
        # 导入所有模型，确保 Base.metadata 已填充
        import app.models  # noqa: F401
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables initialized.")
    yield
    logger.info("Shutting down...")
    await engine.dispose()


app = FastAPI(
    title="MiniGoogle Backend",
    description="小谷歌生态平台 API — 支持用户、好友、聊天、游戏积分、充值",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS 中间件 ───────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── 全局异常处理 ──────────────────────────────────────────────────────────────
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """参数校验失败统一格式"""
    errors = exc.errors()
    detail = "; ".join(f"{'.'.join(str(x) for x in e['loc'])}: {e['msg']}" for e in errors)
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"code": ErrorCode.VALIDATION_ERROR, "message": detail, "data": None},
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    """兜底处理未捕获异常"""
    logger.exception(f"Unhandled exception on {request.url}: {exc}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"code": ErrorCode.INTERNAL_ERROR, "message": "Internal server error", "data": None},
    )


# ── 注册路由 ──────────────────────────────────────────────────────────────────
app.include_router(auth_ext_router)   # 前端兼容格式 + OAuth + OTP（优先注册）
app.include_router(auth.router)        # 原始 API 格式（保留给程序调用）
app.include_router(users.router)
app.include_router(friends.router)
app.include_router(chat.router)
app.include_router(games.router)
app.include_router(recharge.router)
app.include_router(ws_router)  # WebSocket


@app.get("/", tags=["Health"])
async def health_check():
    return {"code": 0, "message": "MiniGoogle is running 🚀", "data": {"version": "1.0.0"}}
