"""
Module: app.core.exceptions (Catalog Service)
Nhiệm vụ: Định nghĩa lớp ngoại lệ nghiệp vụ `AppError` và bộ xử lý lỗi thống nhất
          trả về định dạng JSON chuẩn `{ "code": "...", "message": "...", "details": {} }`.
"""

from typing import Any, Dict, Optional
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


class AppError(Exception):
    """Ngoại lệ nghiệp vụ chuẩn dùng trong Catalog Service."""

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
    """Đăng ký các exception handler chuẩn hóa phản hồi lỗi cho Catalog Service."""

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
        # Chuyển đổi lỗi Decimal/validation sang chuỗi thân thiện để serialize JSON an toàn
        safe_errors = []
        for err in exc.errors():
            clean_err = dict(err)
            if "ctx" in clean_err and isinstance(clean_err["ctx"], dict):
                clean_err["ctx"] = {
                    k: str(v) for k, v in clean_err["ctx"].items()
                }
            safe_errors.append(clean_err)
        return JSONResponse(
            status_code=422,
            content={
                "code": "VALIDATION_ERROR",
                "message": "Dữ liệu sản phẩm/danh mục không hợp lệ. Vui lòng kiểm tra lại.",
                "details": {"errors": safe_errors},
            },
        )

