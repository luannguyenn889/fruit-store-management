"""
Module: app.repositories.chat_repository (Chatbot Service)
Nhiệm vụ: Truy vấn và lưu trữ `ChatSession` & `ChatMessage` trong `fruitstore_chatbot_db`.
"""

from typing import List, Optional
from uuid import UUID
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chat import ChatMessage, ChatSession


class ChatRepository:
    """Repository thao tác bảng `chat_sessions` và `chat_messages`."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_session(self, session_id: UUID) -> Optional[ChatSession]:
        result = await self.session.execute(
            select(ChatSession).where(ChatSession.id == session_id)
        )
        return result.scalar_one_or_none()

    async def create_session(
        self, user_id: Optional[UUID], user_role: str, title: str
    ) -> ChatSession:
        chat_session = ChatSession(
            user_id=user_id,
            user_role=user_role,
            title=title[:180],
        )
        self.session.add(chat_session)
        await self.session.flush()
        return chat_session

    async def list_user_sessions(
        self, user_id: UUID, limit: int = 20
    ) -> List[ChatSession]:
        result = await self.session.execute(
            select(ChatSession)
            .where(ChatSession.user_id == user_id)
            .order_by(desc(ChatSession.updated_at))
            .limit(limit)
        )
        return list(result.scalars().all())

    async def list_messages(
        self, session_id: UUID, limit: int = 30
    ) -> List[ChatMessage]:
        result = await self.session.execute(
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at.asc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def add_message(
        self,
        session_id: UUID,
        role: str,
        content: str,
        tool_calls_json: Optional[str] = None,
    ) -> ChatMessage:
        msg = ChatMessage(
            session_id=session_id,
            role=role,
            content=content,
            tool_calls_json=tool_calls_json,
        )
        self.session.add(msg)
        await self.session.flush()
        return msg

    async def delete_session(self, chat_session: ChatSession) -> None:
        await self.session.delete(chat_session)
