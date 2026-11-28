"""
Module: app.services.chatbot_service (Chatbot Service)
Nhiệm vụ: Điều phối hội thoại với Google Gemini (`google-genai`) kết hợp Function Calling,
          Streaming SSE, nhận diện hình ảnh (Multimodal Vision), ngữ cảnh trang đang mở,
          dự phòng model khi gặp 429 và lưu lịch sử chat vào `fruitstore_chatbot_db`.
"""

import asyncio
import base64
import binascii
import json
from collections.abc import AsyncGenerator
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
from app.schemas.chat import ChatMessageResponse, ChatResponse, RecommendedProduct
from app.services.tool_executor import INTERNAL_INVENTORY_ROLES, ToolExecutor

SYSTEM_INSTRUCTION = (
    "Bạn là Trợ lý AI chính thức của cửa hàng trái cây tươi FruitStore. "
    "Hãy trả lời bằng tiếng Việt thân thiện, ngắn gọn, có cấu trúc (gạch đầu dòng, in đậm tên sản phẩm/giá). "
    "Khi người dùng hỏi về sản phẩm, giá bán, xuất xứ, bảo quản hoặc tồn kho, "
    "BẮT BUỘC gọi các tool (search_products, get_product_detail, check_stock, get_expiring_lots) "
    "để lấy dữ liệu thực tế trước khi trả lời; tuyệt đối không tự bịa giá hoặc số lượng tồn kho. "
    "Nếu người dùng gửi kèm ảnh trái cây, hãy nhận diện loại quả, gợi ý độ chín/cách bảo quản và gọi search_products để kiểm tra cửa hàng có bán hay không."
)

ALLOWED_VISION_MIMES = {"image/jpeg", "image/png", "image/webp"}
MAX_VISION_BYTES = 4 * 1024 * 1024  # 4 MB

GeminiClientFactory = Callable[[str], Any]


def _default_client_factory(api_key: str) -> genai.Client:
    return genai.Client(api_key=api_key)


def _model_candidates() -> List[str]:
    raw = [settings.GEMINI_MODEL] + [
        m.strip() for m in settings.GEMINI_FALLBACK_MODELS.split(",") if m.strip()
    ]
    seen: List[str] = []
    for m in raw:
        if m not in seen:
            seen.append(m)
    return seen


def _is_retryable_model_error(exc: Exception) -> bool:
    msg = str(exc)
    return (
        "429" in msg
        or "RESOURCE_EXHAUSTED" in msg
        or "404" in msg
        or "NOT_FOUND" in msg
    )


def _decode_vision_image(
    image_base64: Optional[str], image_mime_type: Optional[str]
) -> Optional[Tuple[bytes, str]]:
    if not image_base64:
        return None
    mime = (image_mime_type or "image/jpeg").lower().strip()
    if mime not in ALLOWED_VISION_MIMES:
        raise AppError(
            status_code=422,
            code="INVALID_IMAGE_MIME",
            message="Chỉ hỗ trợ ảnh JPG, PNG hoặc WEBP.",
        )
    raw_b64 = image_base64.split(",", 1)[-1].strip()
    try:
        raw_bytes = base64.b64decode(raw_b64, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise AppError(
            status_code=422,
            code="INVALID_IMAGE_DATA",
            message="Dữ liệu ảnh base64 không hợp lệ.",
        ) from exc
    if len(raw_bytes) > MAX_VISION_BYTES:
        raise AppError(
            status_code=422,
            code="IMAGE_TOO_LARGE",
            message="Ảnh gửi lên vượt quá giới hạn 4 MB.",
        )
    return raw_bytes, mime


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


def _compose_user_parts(
    user_message: str,
    current_route: Optional[str],
    product_id: Optional[UUID],
    vision_image: Optional[Tuple[bytes, str]],
) -> List[types.Part]:
    context_notes: List[str] = []
    if current_route:
        context_notes.append(f"trang đang mở: {current_route}")
    if product_id:
        context_notes.append(f"product_id đang xem: {product_id}")

    prompt_text = user_message
    if context_notes:
        prompt_text = f"[Ngữ cảnh UI: {', '.join(context_notes)}]\n{user_message}"

    parts: List[types.Part] = [types.Part.from_text(text=prompt_text)]
    if vision_image:
        img_bytes, img_mime = vision_image
        parts.append(types.Part.from_bytes(data=img_bytes, mime_type=img_mime))
    return parts


async def _generate_with_fallback(
    client: Any,
    contents: List[types.Content],
    config: types.GenerateContentConfig,
) -> Any:
    candidates = _model_candidates()
    last_exc: Optional[Exception] = None
    for model_name in candidates:
        try:
            return await asyncio.to_thread(
                client.models.generate_content,
                model=model_name,
                contents=contents,
                config=config,
            )
        except Exception as exc:
            last_exc = exc
            if _is_retryable_model_error(exc):
                continue
            raise
    assert last_exc is not None
    raise last_exc


async def _run_gemini_conversation(
    history_messages: List[ChatMessage],
    user_message: str,
    executor: ToolExecutor,
    user_role: str,
    current_route: Optional[str] = None,
    product_id: Optional[UUID] = None,
    vision_image: Optional[Tuple[bytes, str]] = None,
    client_factory: Optional[GeminiClientFactory] = None,
    on_status: Optional[Callable[[str], Any]] = None,
) -> Tuple[str, List[str]]:
    """Chạy vòng lặp hỏi-đáp Gemini kèm Function Calling và Model Fallback."""
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

    user_parts = _compose_user_parts(user_message, current_route, product_id, vision_image)
    contents.append(types.Content(role="user", parts=user_parts))

    config = types.GenerateContentConfig(
        system_instruction=SYSTEM_INSTRUCTION,
        tools=tools,
        temperature=0.3,
    )

    tools_used: List[str] = []

    for _ in range(4):
        response = await _generate_with_fallback(client, contents, config)
        function_calls = getattr(response, "function_calls", None) or []
        if not function_calls:
            reply_text = (getattr(response, "text", None) or "").strip()
            if not reply_text:
                reply_text = "Xin lỗi, tôi chưa thể tổng hợp câu trả lời lúc này. Bạn vui lòng thử hỏi lại nhé."
            return reply_text, tools_used

        if response.candidates and response.candidates[0].content:
            contents.append(response.candidates[0].content)

        tool_response_parts: List[types.Part] = []
        for fc in function_calls:
            fn_name = fc.name or ""
            fn_args = dict(fc.args or {})
            tools_used.append(fn_name)
            if on_status:
                await on_status(fn_name)
            result = await executor.execute(fn_name, fn_args)
            tool_response_parts.append(
                types.Part.from_function_response(name=fn_name, response={"result": result})
            )

        contents.append(types.Content(role="user", parts=tool_response_parts))

    return "Tôi đã tra cứu nhiều bước nhưng chưa chốt được kết quả. Bạn hãy hỏi cụ thể hơn tên trái cây giúp tôi nhé.", tools_used


def _format_gemini_error(exc: Exception) -> str:
    err_str = str(exc)
    if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
        return (
            "Trợ lý AI tạm thời vượt hạn mức miễn phí (429 RESOURCE_EXHAUSTED) trên các model Gemini. "
            "Vui lòng thử lại sau ít phút hoặc đổi API key mới."
        )
    return f"Xin lỗi, Trợ lý AI đang gặp gián đoạn kết nối Gemini ({type(exc).__name__}). Vui lòng thử lại sau."


async def _prepare_session_and_history(
    db: AsyncSession,
    actor: ChatActor,
    message: str,
    session_id: Optional[UUID],
    has_image: bool,
) -> Tuple[ChatRepository, ChatSession, List[ChatMessage], str]:
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
    stored_user_text = f"[Đính kèm ảnh] {clean_message}" if has_image else clean_message
    await repo.add_message(chat_session.id, role="user", content=stored_user_text)
    return repo, chat_session, history, clean_message


async def handle_chat(
    db: AsyncSession,
    actor: ChatActor,
    message: str,
    session_id: Optional[UUID],
    request_id: str,
    current_route: Optional[str] = None,
    product_id: Optional[UUID] = None,
    image_base64: Optional[str] = None,
    image_mime_type: Optional[str] = None,
    client_factory: Optional[GeminiClientFactory] = None,
) -> ChatResponse:
    """Xử lý một lượt tin nhắn JSON chuẩn, gọi Gemini + Tools + Vision và lưu DB."""
    vision_image = _decode_vision_image(image_base64, image_mime_type)
    repo, chat_session, history, clean_message = await _prepare_session_and_history(
        db=db, actor=actor, message=message, session_id=session_id, has_image=vision_image is not None
    )

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
            current_route=current_route,
            product_id=product_id,
            vision_image=vision_image,
            client_factory=client_factory,
        )
    except Exception as exc:
        reply_text = _format_gemini_error(exc)
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
        recommended_products=executor.recommended_products,
        suggestions=_default_suggestions(actor.role),
    )


def _sse_event(event: str, data: Dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


async def stream_chat(
    db: AsyncSession,
    actor: ChatActor,
    message: str,
    session_id: Optional[UUID],
    request_id: str,
    current_route: Optional[str] = None,
    product_id: Optional[UUID] = None,
    image_base64: Optional[str] = None,
    image_mime_type: Optional[str] = None,
    client_factory: Optional[GeminiClientFactory] = None,
) -> AsyncGenerator[str, None]:
    """Streaming phản hồi dạng SSE (`status` -> `delta` -> `done`)."""
    vision_image = _decode_vision_image(image_base64, image_mime_type)
    repo, chat_session, history, clean_message = await _prepare_session_and_history(
        db=db, actor=actor, message=message, session_id=session_id, has_image=vision_image is not None
    )

    executor = ToolExecutor(
        user_role=actor.role,
        user_id=str(actor.user_id) if actor.user_id else None,
        request_id=request_id,
    )

    status_queue: asyncio.Queue[str] = asyncio.Queue()

    async def on_status(tool_name: str) -> None:
        await status_queue.put(tool_name)

    yield _sse_event("status", {"message": "Đang phân tích câu hỏi..."})

    task = asyncio.create_task(
        _run_gemini_conversation(
            history_messages=history,
            user_message=clean_message,
            executor=executor,
            user_role=actor.role,
            current_route=current_route,
            product_id=product_id,
            vision_image=vision_image,
            client_factory=client_factory,
            on_status=on_status,
        )
    )

    while not task.done():
        try:
            tool_name = await asyncio.wait_for(status_queue.get(), timeout=0.15)
            yield _sse_event("status", {"message": f"Đang chạy {tool_name}..."})
        except asyncio.TimeoutError:
            continue

    try:
        reply_text, tools_used = await task
    except Exception as exc:
        reply_text = _format_gemini_error(exc)
        tools_used = []

    await repo.add_message(
        chat_session.id,
        role="assistant",
        content=reply_text,
        tool_calls_json=json.dumps(tools_used) if tools_used else None,
    )
    await db.commit()

    # Phát từng đoạn văn bản nhỏ để UI hiển thị hiệu ứng streaming mượt mà
    chunk_size = 24
    for idx in range(0, len(reply_text), chunk_size):
        yield _sse_event("delta", {"text": reply_text[idx : idx + chunk_size]})
        await asyncio.sleep(0.015)

    yield _sse_event(
        "done",
        {
            "session_id": str(chat_session.id),
            "tools_used": tools_used,
            "recommended_products": [p.model_dump() for p in executor.recommended_products],
            "suggestions": _default_suggestions(actor.role),
        },
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
