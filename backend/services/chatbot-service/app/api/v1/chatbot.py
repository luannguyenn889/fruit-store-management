"""
Module: app.api.v1.chatbot (Chatbot Service)
Nhiệm vụ: Cung cấp các REST & SSE endpoint cho Trợ lý AI FruitStore (`/api/v1/chatbot/*`).
"""

from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Header, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import (
    ChatActor,
    get_authenticated_actor,
    get_optional_actor,
    verify_internal_key,
)
from app.db.session import get_db
from app.schemas.chat import (
    ChatMessageResponse,
    ChatRequest,
    ChatResponse,
    ChatSessionResponse,
)
from app.services import chatbot_service

router = APIRouter(
    prefix="/chatbot",
    tags=["Chatbot AI"],
    dependencies=[Depends(verify_internal_key)],
)


@router.post(
    "/chat",
    response_model=ChatResponse,
    summary="Gửi tin nhắn trò chuyện với Trợ lý AI Gemini (JSON)",
)
async def send_chat_message(
    payload: ChatRequest,
    actor: ChatActor = Depends(get_optional_actor),
    x_request_id: Optional[str] = Header(default=None, alias="X-Request-ID"),
    db: AsyncSession = Depends(get_db),
) -> ChatResponse:
    """Tiếp nhận câu hỏi/ảnh/ngữ cảnh, gọi Gemini + Tool và trả JSON đầy đủ."""
    return await chatbot_service.handle_chat(
        db=db,
        actor=actor,
        message=payload.message,
        session_id=payload.session_id,
        request_id=x_request_id or "chatbot-req",
        current_route=payload.current_route,
        product_id=payload.product_id,
        image_base64=payload.image_base64,
        image_mime_type=payload.image_mime_type,
    )


@router.post(
    "/chat/stream",
    summary="Gửi tin nhắn trò chuyện với Trợ lý AI Gemini (SSE Streaming)",
)
async def stream_chat_message(
    payload: ChatRequest,
    actor: ChatActor = Depends(get_optional_actor),
    x_request_id: Optional[str] = Header(default=None, alias="X-Request-ID"),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """Streaming phản hồi theo thời gian thực qua Server-Sent Events (`text/event-stream`)."""
    generator = chatbot_service.stream_chat(
        db=db,
        actor=actor,
        message=payload.message,
        session_id=payload.session_id,
        request_id=x_request_id or "chatbot-req",
        current_route=payload.current_route,
        product_id=payload.product_id,
        image_base64=payload.image_base64,
        image_mime_type=payload.image_mime_type,
    )
    return StreamingResponse(
        generator,
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.get(
    "/sessions",
    response_model=List[ChatSessionResponse],
    summary="Danh sách phiên hội thoại của người dùng",
)
async def get_my_sessions(
    actor: ChatActor = Depends(get_authenticated_actor),
    db: AsyncSession = Depends(get_db),
) -> List[ChatSessionResponse]:
    rows = await chatbot_service.list_sessions(db=db, actor=actor)
    return [ChatSessionResponse.model_validate(r) for r in rows]


@router.get(
    "/sessions/{session_id}/messages",
    response_model=List[ChatMessageResponse],
    summary="Xem lịch sử tin nhắn trong một phiên hội thoại",
)
async def get_session_messages(
    session_id: UUID,
    actor: ChatActor = Depends(get_authenticated_actor),
    db: AsyncSession = Depends(get_db),
) -> List[ChatMessageResponse]:
    return await chatbot_service.get_session_messages(
        db=db, actor=actor, session_id=session_id
    )


@router.delete(
    "/sessions/{session_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Xóa một phiên hội thoại cá nhân",
)
async def delete_my_session(
    session_id: UUID,
    actor: ChatActor = Depends(get_authenticated_actor),
    db: AsyncSession = Depends(get_db),
) -> None:
    await chatbot_service.delete_session(db=db, actor=actor, session_id=session_id)
