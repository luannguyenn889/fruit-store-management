"""
Module: app.core.exceptions
Nhiệm vụ: Định nghĩa lớp ngoại lệ nghiệp vụ chuẩn `AppError` và các bộ xử lý lỗi
          (Exception Handlers) trả về JSON thống nhất theo định dạng:
          `{ "code": "...", "message": "...", "details": {} }`.
"""

from typing import Any, Dict, Optional
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


class AppError(Exception):
    """Ngoại lệ nghiệp vụ chuẩn của hệ thống FruitStore."""

    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__(message)


def register_exception_handlers(app: FastAPI) -> None:
    """Đăng ký các handler chuẩn hóa phản hồi lỗi JSON cho ứng dụng FastAPI."""

    @app.exception_handler(AppError)
    async def app_error_handler(_: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "code": exc.code,
                "message": exc.message,
                "details": exc.details,
            },
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(_: Request, exc: HTTPException) -> JSONResponse:
        if isinstance(exc.detail, dict) and "code" in exc.detail:
            return JSONResponse(status_code=exc.status_code, content=exc.detail)
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "code": f"HTTP_{exc.status_code}",
                "message": str(exc.detail),
                "details": {},
            },
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        _: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={
                "code": "VALIDATION_ERROR",
                "message": "Dữ liệu đầu vào không hợp lệ. Vui lòng kiểm tra lại các trường thông tin.",
                "details": {"errors": exc.errors()},
            },
        )

