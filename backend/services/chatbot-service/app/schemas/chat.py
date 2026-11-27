"""
Module: app.schemas.chat (Chatbot Service)
Nhiệm vụ: Định nghĩa schema Pydantic v2 cho yêu cầu/phản hồi trò chuyện và lịch sử phiên chat.
"""

from datetime import datetime
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class ChatRequest(BaseModel):
    """Payload gửi tin nhắn tới Trợ lý AI."""

    message: str = Field(..., min_length=1, max_length=2000, description="Nội dung câu hỏi")
    session_id: Optional[UUID] = Field(default=None, description="ID phiên chat hiện tại")


class ChatMessageResponse(BaseModel):
    """Thông tin một tin nhắn trong phiên hội thoại."""

    id: UUID
    role: str
    content: str
    tools_used: List[str] = Field(default_factory=list)
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ChatResponse(BaseModel):
    """Phản hồi sau một lượt hỏi đáp với Trợ lý AI."""

    session_id: UUID
    reply: str
    tools_used: List[str] = Field(default_factory=list)
    suggestions: List[str] = Field(default_factory=list)


class ChatSessionResponse(BaseModel):
    """Thông tin tóm tắt một phiên trò chuyện."""

    id: UUID
    title: str
    user_role: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
