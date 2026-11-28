"""
Module: app.schemas.chat (Chatbot Service)
Nhiệm vụ: Định nghĩa schema Pydantic v2 cho yêu cầu/phản hồi trò chuyện,
          bảo vệ phiên khách (`guest_token`), ảnh đa phương thức (Vision),
          ngữ cảnh trang, thẻ sản phẩm gợi ý và lịch sử phiên.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class ChatRequest(BaseModel):
    """Payload gửi tin nhắn tới Trợ lý AI (hỗ trợ văn bản, ảnh và ngữ cảnh trang)."""

    message: str = Field(..., min_length=1, max_length=2000, description="Nội dung câu hỏi")
    session_id: Optional[UUID] = Field(default=None, description="ID phiên chat hiện tại")
    guest_token: Optional[str] = Field(default=None, max_length=64, description="Token xác thực phiên khách vãng lai")
    current_route: Optional[str] = Field(default=None, max_length=200, description="Đường dẫn trang đang xem")
    product_id: Optional[UUID] = Field(default=None, description="ID sản phẩm đang xem (nếu có)")
    image_base64: Optional[str] = Field(default=None, description="Ảnh trái cây mã hóa base64")
    image_mime_type: Optional[str] = Field(default=None, max_length=64, description="MIME ảnh (image/jpeg, image/png, image/webp)")


class RecommendedProduct(BaseModel):
    """Thẻ sản phẩm tóm tắt kèm ảnh & tồn kho để render trực tiếp trong khung chat."""

    id: str
    sku: Optional[str] = None
    name: str
    unit: Optional[str] = None
    price: Optional[str] = None
    image_url: Optional[str] = None
    available_quantity: Optional[str] = None


class ChatMessageResponse(BaseModel):
    """Thông tin một tin nhắn trong phiên hội thoại."""

    id: UUID
    role: str
    content: str
    tools_used: List[str] = Field(default_factory=list)
    token_usage: Optional[Dict[str, Any]] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ChatResponse(BaseModel):
    """Phản hồi sau một lượt hỏi đáp với Trợ lý AI."""

    session_id: UUID
    guest_token: Optional[str] = None
    reply: str
    tools_used: List[str] = Field(default_factory=list)
    recommended_products: List[RecommendedProduct] = Field(default_factory=list)
    suggestions: List[str] = Field(default_factory=list)


class ChatSessionResponse(BaseModel):
    """Thông tin tóm tắt một phiên trò chuyện."""

    id: UUID
    title: str
    user_role: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
