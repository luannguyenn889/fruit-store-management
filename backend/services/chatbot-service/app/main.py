"""
Module: app.main (Chatbot Service)
Nhiệm vụ: Điểm khởi chạy FastAPI cho Chatbot Service (:8007), gắn middleware `X-Request-ID`,
          router `/api/v1/chatbot/*` và endpoint `GET /health` kiểm tra PostgreSQL.
"""

import logging
from typing import Dict
from uuid import uuid4

from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.chatbot import router as chatbot_router
from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.db.session import get_db

logger = logging.getLogger("chatbot-service")

app = FastAPI(
    title=settings.SERVICE_NAME,
    version="1.0.0",
    description="Dịch vụ Trợ lý AI (Gemini Function Calling) cho FruitStore SOA.",
)

register_exception_handlers(app)


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or str(uuid4())
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


@app.get("/health", tags=["Health"], summary="Kiểm tra sức khỏe Chatbot Service & DB")
@app.get(
    f"{settings.API_V1_STR}/chatbot/health",
    tags=["Health"],
    summary="Kiểm tra sức khỏe Chatbot Service qua API Gateway",
)
async def health_check(db: AsyncSession = Depends(get_db)) -> JSONResponse:
    try:
        await db.execute(text("SELECT 1"))
        payload: Dict[str, str] = {
            "status": "ok",
            "service": "chatbot-service",
            "database": "connected",
        }
        return JSONResponse(status_code=200, content=payload)
    except Exception as exc:
        logger.error("Chatbot DB health check failed: %s", exc)
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "service": "chatbot-service",
                "database": "disconnected",
            },
        )


app.include_router(chatbot_router, prefix=settings.API_V1_STR)
