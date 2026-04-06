"""
app/routers/chat.py - 聊天 REST 接口（历史消息、未读数、标记已读）
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db, get_current_user
from app.models.user import User
from app.schemas.chat import ChatMessageOut, UnreadCountOut
from app.services.chat_service import ChatService
from app.utils.response import ok

router = APIRouter(prefix="/api/chat", tags=["Chat"])


@router.get("/messages/{user_id}", summary="获取与某用户的历史消息（分页）")
async def get_history(
    user_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = ChatService(db)
    messages, total = await svc.get_history(current_user.id, user_id, page, page_size)
    return ok({
        "total": total,
        "page": page,
        "page_size": page_size,
        "messages": [ChatMessageOut.model_validate(m) for m in messages],
    })


@router.get("/unread/count", summary="获取未读消息总数")
async def unread_count(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = ChatService(db)
    result = await svc.get_unread_count(current_user.id)
    return ok(result)


@router.put("/messages/read/{user_id}", summary="标记与某用户的所有消息为已读")
async def mark_read(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = ChatService(db)
    count = await svc.mark_read(to_user_id=current_user.id, from_user_id=user_id)
    return ok({"marked": count}, "Messages marked as read")
