"""Nạp các ORM models của Chatbot Service vào Base.metadata."""

from app.models.chat import ChatMessage, ChatSession

__all__ = ["ChatSession", "ChatMessage"]
