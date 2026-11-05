from datetime import datetime
from typing import List, Optional
import uuid
from pydantic import BaseModel, EmailStr, Field


class RoleResponse(BaseModel):
    id: int
    code: str
    name: str
    description: Optional[str] = None

    class Config:
        from_attributes = True


class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6, description="Mật khẩu ít nhất 6 ký tự")
    full_name: str = Field(..., min_length=2, max_length=150)
    phone: Optional[str] = Field(None, max_length=20)
    role_code: Optional[str] = Field("CUSTOMER", description="ADMIN, MANAGER, STAFF, WAREHOUSE_STAFF, CUSTOMER")


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class GoogleLoginRequest(BaseModel):
    credential: str = Field(..., description="Google ID Token (credential) trả về từ Google Identity Services")


class UserResponse(BaseModel):
    id: uuid.UUID
    email: str
    phone: Optional[str] = None
    full_name: str
    status: str
    roles: List[str] = []
    created_at: datetime
    last_login_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse

