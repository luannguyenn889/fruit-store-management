"""
Module: app.services.chatbot_service (Chatbot Service)
Nhiệm vụ: Điều phối hội thoại với Google Gemini (`google-genai`) kết hợp Function Calling
          và lưu lịch sử chat vào `fruitstore_chatbot_db`.
"""

import asyncio
import json
from typing import Any, Callable, Dict, List, Optional, Tuple
from uuid import UUID

from google import genai
from google.genai import types
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.deps import ChatActor
from app.core.exceptions import AppError
from app.models.chat import ChatMessage, ChatSession
from app.repositories.chat_repository import ChatRepository
from app.schemas.chat import ChatMessageResponse, ChatResponse
from app.services.tool_executor import INTERNAL_INVENTORY_ROLES, ToolExecutor

SYSTEM_INSTRUCTION = (
    "Bạn là Trợ lý AI chính thức của cửa hàng trái cây tươi FruitStore. "
    "Hãy trả lời bằng tiếng Việt thân thiện, ngắn gọn, rõ ràng. "
    "Khi người dùng hỏi về sản phẩm, giá bán, xuất xứ, bảo quản hoặc tồn kho, "
    "BẮT BUỘC gọi các tool (search_products, get_product_detail, check_stock, get_expiring_lots) "
    "để lấy dữ liệu thực tế trước khi trả lời; tuyệt đối không tự bịa giá hoặc số lượng tồn kho. "
    "Nếu hệ thống đang thiếu dữ liệu hoặc hết hàng, hãy nói trung thực."
)


def _build_gemini_tools(user_role: str) -> List[types.Tool]:
    """Khai báo danh sách Function Declarations gửi cho Gemini theo vai trò."""
    declarations = [
        types.FunctionDeclaration(
            name="search_products",
            description="Tìm kiếm trái cây đang mở bán theo tên hoặc mã SKU, trả về giá bán, đơn vị tính, xuất xứ và hướng dẫn bảo quản.",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "query": types.Schema(type=types.Type.STRING, description="Từ khóa tên trái cây hoặc SKU (để rỗng nếu muốn liệt kê)"),
                    "limit": types.Schema(type=types.Type.INTEGER, description="Số lượng kết quả tối đa (mặc định 10)"),
                },
            ),
        ),
        types.FunctionDeclaration(
            name="get_product_detail",
            description="Xem thông tin chi tiết một sản phẩm trái cây theo UUID.",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "product_id": types.Schema(type=types.Type.STRING, description="UUID của sản phẩm"),
                },
                required=["product_id"],
            ),
        ),
        types.FunctionDeclaration(
            name="check_stock",
            description="Kiểm tra số lượng tồn kho khả dụng thực tế tại cửa hàng theo product_id hoặc từ khóa tên/SKU.",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "product_id": types.Schema(type=types.Type.STRING, description="UUID sản phẩm cần kiểm tra"),
                    "keyword": types.Schema(type=types.Type.STRING, description="Tên trái cây hoặc SKU nếu chưa biết UUID"),
                },
            ),
        ),
    ]

    if user_role.upper() in INTERNAL_INVENTORY_ROLES:
        declarations.append(
            types.FunctionDeclaration(
                name="get_expiring_lots",
                description="Tra cứu danh sách các lô hàng trái cây sắp hết hạn hoặc đã hết hạn trong kho FEFO (chỉ dành cho nhân viên kho/quản lý).",
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "days": types.Schema(type=types.Type.INTEGER, description="Số ngày cảnh báo sắp hết hạn (mặc định 3)"),
                    },
                ),
            )
        )

    return [types.Tool(function_declarations=declarations)]


def _default_suggestions(user_role: str) -> List[str]:
    if user_role.upper() in INTERNAL_INVENTORY_ROLES:
        return [
            "Có lô trái cây nào sắp hết hạn không?",
            "Kiểm tra tồn kho Xoài cát Hòa Lộc",
            "Liệt kê các sản phẩm đang mở bán",
        ]
    return [
        "Xoài cát Hòa Lộc giá bao nhiêu và còn hàng không?",
        "Cửa hàng đang có những loại trái cây nào?",
        "Cách bảo quản dâu tây tươi lâu?",
    ]


# Factory mặc định để dễ mock trong unit test
GeminiClientFactory = Callable[[str], Any]


def _default_client_factory(api_key: str) -> genai.Client:
    return genai.Client(api_key=api_key)


async def _run_gemini_conversation(
    history_messages: List[ChatMessage],
    user_message: str,
    executor: ToolExecutor,
    user_role: str,
    client_factory: Optional[GeminiClientFactory] = None,
) -> Tuple[str, List[str]]:
    """Chạy vòng lặp hỏi-đáp Gemini kèm Function Calling."""
    if not settings.GEMINI_API_KEY.strip():
        return (
            "Trợ lý AI chưa được cấu hình `GEMINI_API_KEY` ở máy chủ. "
            "Vui lòng thêm `GEMINI_API_KEY` vào file `.env` của `chatbot-service` để kích hoạt hội thoại thông minh.",
            [],
        )

    factory = client_factory or _default_client_factory
    client = factory(settings.GEMINI_API_KEY.strip())
    tools = _build_gemini_tools(user_role)

    contents: List[types.Content] = []
    for m in history_messages[-12:]:
        role = "model" if m.role == "assistant" else "user"
        contents.append(types.Content(role=role, parts=[types.Part.from_text(text=m.content)]))
    contents.append(types.Content(role="user", parts=[types.Part.from_text(text=user_message)]))

    config = types.GenerateContentConfig(
        system_instruction=SYSTEM_INSTRUCTION,
        tools=tools,
        temperature=0.3,
    )

    tools_used: List[str] = []

    for _ in range(4):
        response = await asyncio.to_thread(
            client.models.generate_content,
            model=settings.GEMINI_MODEL,
            contents=contents,
            config=config,
        )

        function_calls = getattr(response, "function_calls", None) or []
        if not function_calls:
            reply_text = (getattr(response, "text", None) or "").strip()
            if not reply_text:
                reply_text = "Xin lỗi, tôi chưa thể tổng hợp câu trả lời lúc này. Bạn vui lòng thử hỏi lại nhé."
            return reply_text, tools_used

        # Lưu lượt model gọi tool vào ngữ cảnh
        if response.candidates and response.candidates[0].content:
            contents.append(response.candidates[0].content)

        tool_response_parts: List[types.Part] = []
        for fc in function_calls:
            fn_name = fc.name or ""
            fn_args = dict(fc.args or {})
            tools_used.append(fn_name)
            result = await executor.execute(fn_name, fn_args)
            tool_response_parts.append(
                types.Part.from_function_response(name=fn_name, response={"result": result})
            )

        contents.append(types.Content(role="user", parts=tool_response_parts))

    return "Tôi đã tra cứu nhiều bước nhưng chưa chốt được kết quả. Bạn hãy hỏi cụ thể hơn tên trái cây giúp tôi nhé.", tools_used


async def handle_chat(
    db: AsyncSession,
    actor: ChatActor,
    message: str,
    session_id: Optional[UUID],
    request_id: str,
    client_factory: Optional[GeminiClientFactory] = None,
) -> ChatResponse:
    """Xử lý một lượt tin nhắn của người dùng, gọi Gemini + Tools và lưu DB."""
    repo = ChatRepository(db)
    clean_message = message.strip()
    if not clean_message:
        raise AppError(status_code=422, code="EMPTY_MESSAGE", message="Tin nhắn không được để trống.")

    chat_session: Optional[ChatSession] = None
    if session_id is not None:
        chat_session = await repo.get_session(session_id)
        if not chat_session:
            raise AppError(status_code=404, code="SESSION_NOT_FOUND", message="Không tìm thấy phiên hội thoại.")
        if chat_session.user_id is not None and actor.user_id != chat_session.user_id:
            raise AppError(status_code=403, code="FORBIDDEN", message="Bạn không có quyền truy cập phiên chat này.")
    else:
        title = clean_message[:60] + ("..." if len(clean_message) > 60 else "")
        chat_session = await repo.create_session(
            user_id=actor.user_id,
            user_role=actor.role,
            title=title,
        )

    history = await repo.list_messages(chat_session.id, limit=20)
    await repo.add_message(chat_session.id, role="user", content=clean_message)

    executor = ToolExecutor(
        user_role=actor.role,
        user_id=str(actor.user_id) if actor.user_id else None,
        request_id=request_id,
    )

    try:
        reply_text, tools_used = await _run_gemini_conversation(
            history_messages=history,
            user_message=clean_message,
            executor=executor,
            user_role=actor.role,
            client_factory=client_factory,
        )
    except Exception as exc:
        err_str = str(exc)
        if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
            reply_text = (
                "Trợ lý AI tạm thời vượt hạn mức miễn phí (429 RESOURCE_EXHAUSTED) của Gemini. "
                "Vui lòng thử lại sau ít phút hoặc đổi `GEMINI_MODEL` / API key mới."
            )
        else:
            reply_text = f"Xin lỗi, Trợ lý AI đang gặp gián đoạn kết nối Gemini ({type(exc).__name__}). Vui lòng thử lại sau."
        tools_used = []

    await repo.add_message(
        chat_session.id,
        role="assistant",
        content=reply_text,
        tool_calls_json=json.dumps(tools_used) if tools_used else None,
    )
    await db.commit()

    return ChatResponse(
        session_id=chat_session.id,
        reply=reply_text,
        tools_used=tools_used,
        suggestions=_default_suggestions(actor.role),
    )


async def list_sessions(db: AsyncSession, actor: ChatActor) -> List[ChatSession]:
    repo = ChatRepository(db)
    assert actor.user_id is not None
    return await repo.list_user_sessions(actor.user_id)


async def get_session_messages(
    db: AsyncSession, actor: ChatActor, session_id: UUID
) -> List[ChatMessageResponse]:
    repo = ChatRepository(db)
    chat_session = await repo.get_session(session_id)
    if not chat_session:
        raise AppError(status_code=404, code="SESSION_NOT_FOUND", message="Không tìm thấy phiên hội thoại.")
    if chat_session.user_id != actor.user_id:
        raise AppError(status_code=403, code="FORBIDDEN", message="Bạn không có quyền xem phiên chat này.")

    rows = await repo.list_messages(session_id, limit=50)
    result: List[ChatMessageResponse] = []
    for row in rows:
        tools: List[str] = []
        if row.tool_calls_json:
            try:
                tools = json.loads(row.tool_calls_json)
            except json.JSONDecodeError:
                tools = []
        result.append(
            ChatMessageResponse(
                id=row.id,
                role=row.role,
                content=row.content,
                tools_used=tools,
                created_at=row.created_at,
            )
        )
    return result


async def delete_session(db: AsyncSession, actor: ChatActor, session_id: UUID) -> None:
    repo = ChatRepository(db)
    chat_session = await repo.get_session(session_id)
    if not chat_session:
        raise AppError(status_code=404, code="SESSION_NOT_FOUND", message="Không tìm thấy phiên hội thoại.")
    if chat_session.user_id != actor.user_id:
        raise AppError(status_code=403, code="FORBIDDEN", message="Bạn không có quyền xóa phiên chat này.")
    await repo.delete_session(chat_session)
    await db.commit()
