"""
Module: app.main (API Gateway)
Nhiệm vụ: Cổng giao tiếp tập trung (Reverse Proxy & JWT Authentication Gateway) chạy tại cổng 8000:
          1. Quản lý CORS tập trung cho Angular Frontend (`http://localhost:4200`).
          2. Sinh hoặc chuyển tiếp `X-Request-ID` để truy vết log xuyên suốt các service (NFR-O01).
          3. Loại bỏ hoàn toàn mọi header `X-User-*` và `X-Internal-Key` do client tự gửi (chống giả mạo quyền).
          4. Kiểm tra chữ ký & thời hạn JWT trên các route cần bảo vệ, trích xuất `sub` -> `X-User-Id`
             và `role` -> `X-User-Role` trước khi chuyển tiếp xuống `auth-service` (:8001) hoặc `catalog-service` (:8002).
          5. Trả mã lỗi chuẩn `502 UPSTREAM_UNAVAILABLE` nếu một microservice phía sau bị dừng,
             đảm bảo lỗi được cô lập từng phần (NFR-R03).
"""

from typing import Any, Dict, Optional, Tuple
from uuid import uuid4

import httpx
import jwt
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings

app = FastAPI(
    title=settings.SERVICE_NAME,
    version="1.3.0",
    description=(
        "Cổng API Gateway trung tâm của hệ thống FruitStore SOA. "
        "Xác thực JWT, chống giả mạo header và định tuyến tới Auth Service (:8001) & Catalog Service (:8002)."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
)

# Cấu hình CORS tập trung tại Gateway (các service nội bộ không cần bật CORS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID"],
)

# Danh sách các đường dẫn công khai trong Auth Service không yêu cầu JWT
PUBLIC_AUTH_PATHS = {
    "/api/v1/auth/login",
    "/api/v1/auth/google",
    "/api/v1/auth/register",
}

# Các hop-by-hop headers không được chuyển tiếp qua proxy
HOP_BY_HOP_HEADERS = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailers",
    "transfer-encoding",
    "upgrade",
    "host",
    "content-length",
}


def is_public_route(method: str, path: str) -> bool:
    """
    Kiểm tra xem request hiện tại có thuộc nhóm công khai (không bắt buộc JWT) hay không:
    - `POST /api/v1/auth/login`, `/google`, `/register`
    - `GET /api/v1/catalog/**` (xem danh mục, sản phẩm, lịch sử giá công khai)
    - `GET /health`
    """
    normalized_path = path.rstrip("/") or "/"
    upper_method = method.upper()

    if upper_method == "OPTIONS":
        return True
    if normalized_path == "/health" and upper_method == "GET":
        return True
    if upper_method == "POST" and normalized_path in PUBLIC_AUTH_PATHS:
        return True
    if upper_method == "GET" and (
        normalized_path == "/api/v1/catalog"
        or normalized_path.startswith("/api/v1/catalog/")
    ):
        return True
    return False


def verify_jwt_from_request(
    request: Request, require_token: bool
) -> Tuple[Optional[Dict[str, Any]], Optional[JSONResponse]]:
    """
    Trích xuất và xác thực Bearer JWT từ header `Authorization`.
    Trả về `(claims, None)` nếu hợp lệ, hoặc `(None, error_response)` nếu bắt buộc mà thiếu/sai.
    """
    auth_header = request.headers.get("authorization", "")
    if not auth_header or not auth_header.lower().startswith("bearer "):
        if require_token:
            return None, JSONResponse(
                status_code=401,
                content={
                    "code": "UNAUTHORIZED",
                    "message": "Yêu cầu xác thực. Vui lòng đăng nhập và gửi kèm Bearer Token.",
                    "details": {},
                },
            )
        return None, None

    token = auth_header.split(" ", 1)[1].strip()
    try:
        claims = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
        if not claims.get("sub") or not claims.get("role"):
            raise jwt.InvalidTokenError("Token thiếu thông tin định danh sub hoặc role.")
        return claims, None
    except jwt.ExpiredSignatureError:
        if require_token:
            return None, JSONResponse(
                status_code=401,
                content={
                    "code": "TOKEN_EXPIRED",
                    "message": "Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.",
                    "details": {},
                },
            )
        return None, None
    except jwt.PyJWTError:
        if require_token:
            return None, JSONResponse(
                status_code=401,
                content={
                    "code": "INVALID_TOKEN",
                    "message": "Token xác thực không hợp lệ.",
                    "details": {},
                },
            )
        return None, None


def build_upstream_headers(
    request: Request,
    request_id: str,
    claims: Optional[Dict[str, Any]],
) -> Dict[str, str]:
    """
    Xây dựng bộ headers sạch để chuyển tiếp xuống downstream service:
    - Xóa toàn bộ `X-User-*` và `X-Internal-Key` do client gửi (chống giả mạo quyền).
    - Gắn `X-Request-ID` và `X-Internal-Key` chuẩn của Gateway.
    - Gắn `X-User-Id` và `X-User-Role` từ JWT đã xác thực.
    """
    clean_headers: Dict[str, str] = {}
    for key, value in request.headers.items():
        lower_key = key.lower()
        if lower_key in HOP_BY_HOP_HEADERS:
            continue
        if lower_key.startswith("x-user-") or lower_key == "x-internal-key":
            continue
        clean_headers[key] = value

    clean_headers["X-Request-ID"] = request_id
    clean_headers["X-Internal-Key"] = settings.INTERNAL_API_KEY

    if claims:
        clean_headers["X-User-Id"] = str(claims["sub"])
        clean_headers["X-User-Role"] = str(claims["role"])

    return clean_headers


async def forward_request(
    request: Request,
    upstream_base_url: str,
    service_label: str,
) -> Response:
    """Thực hiện kiểm tra JWT, làm sạch header và proxy request tới service đích."""
    request_id = request.headers.get("x-request-id") or str(uuid4())
    require_token = not is_public_route(request.method, request.url.path)

    claims, auth_error = verify_jwt_from_request(request, require_token=require_token)
    if auth_error is not None:
        auth_error.headers["X-Request-ID"] = request_id
        return auth_error

    upstream_headers = build_upstream_headers(request, request_id, claims)
    target_url = f"{upstream_base_url.rstrip('/')}{request.url.path}"
    if request.url.query:
        target_url = f"{target_url}?{request.url.query}"

    body = await request.body()

    try:
        client: Optional[httpx.AsyncClient] = getattr(
            request.app.state, "http_client", None
        )
        if client is not None:
            upstream_resp = await client.request(
                method=request.method,
                url=target_url,
                headers=upstream_headers,
                content=body,
                timeout=15.0,
            )
        else:
            async with httpx.AsyncClient(timeout=15.0) as temp_client:
                upstream_resp = await temp_client.request(
                    method=request.method,
                    url=target_url,
                    headers=upstream_headers,
                    content=body,
                )
    except httpx.RequestError as exc:
        err_resp = JSONResponse(
            status_code=502,
            content={
                "code": "UPSTREAM_UNAVAILABLE",
                "message": f"Dịch vụ '{service_label}' hiện không phản hồi. Vui lòng thử lại sau.",
                "details": {"service": service_label, "reason": str(exc)},
            },
        )
        err_resp.headers["X-Request-ID"] = request_id
        return err_resp

    response_headers = {
        k: v
        for k, v in upstream_resp.headers.items()
        if k.lower() not in HOP_BY_HOP_HEADERS
    }
    response_headers["X-Request-ID"] = request_id

    return Response(
        content=upstream_resp.content,
        status_code=upstream_resp.status_code,
        headers=response_headers,
        media_type=upstream_resp.headers.get("content-type"),
    )


@app.get("/health", tags=["Health Check"], summary="Kiểm tra trạng thái hoạt động của API Gateway")
async def gateway_health(request: Request) -> JSONResponse:
    """Kiểm tra trạng thái Gateway tại cổng 8000."""
    request_id = request.headers.get("x-request-id") or str(uuid4())
    resp = JSONResponse(
        status_code=200,
        content={
            "status": "healthy",
            "service": "api-gateway",
            "upstreams": {
                "auth_service": settings.AUTH_SERVICE_URL,
                "catalog_service": settings.CATALOG_SERVICE_URL,
            },
        },
    )
    resp.headers["X-Request-ID"] = request_id
    return resp


@app.api_route(
    "/api/v1/auth/{path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    tags=["Auth Proxy"],
    summary="Chuyển tiếp các yêu cầu xác thực sang Auth Service (:8001)",
)
async def proxy_auth(path: str, request: Request) -> Response:  # noqa: ARG001
    """Định tuyến mọi request `/api/v1/auth/*` sang `auth-service`."""
    return await forward_request(
        request=request,
        upstream_base_url=settings.AUTH_SERVICE_URL,
        service_label="auth-service",
    )


@app.api_route(
    "/api/v1/catalog/{path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    tags=["Catalog Proxy"],
    summary="Chuyển tiếp các yêu cầu danh mục & sản phẩm sang Catalog Service (:8002)",
)
async def proxy_catalog(path: str, request: Request) -> Response:  # noqa: ARG001
    """Định tuyến mọi request `/api/v1/catalog/*` sang `catalog-service`."""
    return await forward_request(
        request=request,
        upstream_base_url=settings.CATALOG_SERVICE_URL,
        service_label="catalog-service",
    )

