"""
app/websocket/chat_ws.py - WebSocket 实时聊天：连接管理、消息路由、离线消息推送
"""
import json
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.models.user import User
from app.services.chat_service import ChatService
from app.utils.security import decode_access_token

logger = logging.getLogger(__name__)

ws_router = APIRouter()

# ── 全局在线连接表：user_id -> WebSocket ──────────────────────────────────────
active_connections: dict[int, WebSocket] = {}


class ConnectionManager:
    """管理 WebSocket 生命周期与消息发送"""

    def connect(self, user_id: int, ws: WebSocket) -> None:
        active_connections[user_id] = ws
        logger.info(f"[WS] User {user_id} connected. Online: {list(active_connections.keys())}")

    def disconnect(self, user_id: int) -> None:
        active_connections.pop(user_id, None)
        logger.info(f"[WS] User {user_id} disconnected. Online: {list(active_connections.keys())}")

    def is_online(self, user_id: int) -> bool:
        return user_id in active_connections

    async def send_to(self, user_id: int, payload: dict) -> bool:
        """定向推送给指定用户，返回是否成功（即对方是否在线）"""
        ws = active_connections.get(user_id)
        if ws:
            try:
                await ws.send_text(json.dumps(payload, ensure_ascii=False, default=str))
                return True
            except Exception as e:
                logger.warning(f"[WS] Failed to send to user {user_id}: {e}")
                self.disconnect(user_id)
        return False


manager = ConnectionManager()


async def _authenticate_ws(token: str) -> int | None:
    """从 JWT token 提取 user_id，验证失败返回 None"""
    try:
        payload = decode_access_token(token)
        user_id_str = payload.get("sub")
        return int(user_id_str) if user_id_str else None
    except (JWTError, ValueError, TypeError):
        return None


@ws_router.websocket("/ws/chat")
async def chat_websocket(
    websocket: WebSocket,
    token: str = Query(..., description="JWT access token"),
):
    """
    WebSocket 聊天端点：
    - 连接时通过 ?token=<jwt> 验证身份
    - 连接成功后推送离线消息
    - 监听客户端消息并转发

    消息协议（JSON）：
    发送：{"type":"chat","to_user_id":123,"message":"hello"}
    接收：{"type":"message","from_user_id":1,"message":"hi","created_at":"..."}
    已读回执：{"type":"read","from_user_id":1}
    错误：{"type":"error","message":"..."}
    """
    # ── 1. 验证 token ──────────────────────────────────────────────────────────
    user_id = await _authenticate_ws(token)
    if user_id is None:
        await websocket.close(code=4001, reason="Invalid or expired token")
        return

    await websocket.accept()
    manager.connect(user_id, websocket)

    # ── 2. 推送离线消息 ────────────────────────────────────────────────────────
    async with AsyncSessionLocal() as db:
        chat_svc = ChatService(db)
        offline_msgs = await chat_svc.get_offline_messages(user_id)
        for msg in offline_msgs:
            await websocket.send_text(json.dumps({
                "type": "message",
                "from_user_id": msg.from_user_id,
                "message": msg.message,
                "message_id": msg.id,
                "created_at": msg.created_at.isoformat(),
            }, ensure_ascii=False))
        logger.info(f"[WS] Pushed {len(offline_msgs)} offline messages to user {user_id}")

    # ── 3. 消息循环 ────────────────────────────────────────────────────────────
    try:
        while True:
            raw = await websocket.receive_text()
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_text(json.dumps({"type": "error", "message": "Invalid JSON"}))
                continue

            msg_type = data.get("type")

            # ── 3a. 发送聊天消息 ─────────────────────────────────────────────
            if msg_type == "chat":
                to_user_id = data.get("to_user_id")
                message = data.get("message", "").strip()

                if not to_user_id or not message:
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "message": "to_user_id and message are required",
                    }))
                    continue

                # 持久化到数据库
                async with AsyncSessionLocal() as db:
                    chat_svc = ChatService(db)
                    saved = await chat_svc.save_message(
                        from_user_id=user_id,
                        to_user_id=to_user_id,
                        message=message,
                    )

                payload = {
                    "type": "message",
                    "from_user_id": user_id,
                    "message": message,
                    "message_id": saved.id,
                    "created_at": saved.created_at.isoformat(),
                }

                # 尝试实时推送给接收方（若不在线则作为离线消息留在 DB）
                delivered = await manager.send_to(to_user_id, payload)
                logger.info(
                    f"[WS] msg {saved.id} from {user_id} to {to_user_id}: "
                    f"{'delivered' if delivered else 'stored as offline'}"
                )

                # 给发送方一个确认回执
                await websocket.send_text(json.dumps({
                    "type": "sent",
                    "message_id": saved.id,
                    "to_user_id": to_user_id,
                    "delivered": delivered,
                    "created_at": saved.created_at.isoformat(),
                }, ensure_ascii=False))

            # ── 3b. 已读回执 ──────────────────────────────────────────────────
            elif msg_type == "read":
                from_user_id = data.get("from_user_id")
                if not from_user_id:
                    await websocket.send_text(json.dumps({
                        "type": "error", "message": "from_user_id required",
                    }))
                    continue

                # 更新数据库
                async with AsyncSessionLocal() as db:
                    chat_svc = ChatService(db)
                    count = await chat_svc.mark_read(
                        to_user_id=user_id,
                        from_user_id=from_user_id,
                    )

                # 通知原发送方已读
                await manager.send_to(from_user_id, {
                    "type": "read_receipt",
                    "by_user_id": user_id,
                    "count": count,
                })

            # ── 3c. 心跳 ping ─────────────────────────────────────────────────
            elif msg_type == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))

            else:
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": f"Unknown message type: {msg_type}",
                }))

    except WebSocketDisconnect:
        logger.info(f"[WS] User {user_id} disconnected normally")
    except Exception as e:
        logger.error(f"[WS] Unexpected error for user {user_id}: {e}")
    finally:
        manager.disconnect(user_id)
