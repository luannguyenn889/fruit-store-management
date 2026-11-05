from datetime import datetime, timezone
from typing import Optional
import uuid
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.models.user import User, Role
from app.schemas.user import UserRegister


DEFAULT_ROLES = [
    ("ADMIN", "Quản trị viên", "Toàn quyền hệ thống"),
    ("MANAGER", "Quản lý cửa hàng", "Quản lý sản phẩm, giá bán, kho và báo cáo"),
    ("STAFF", "Nhân viên bán hàng", "Bán hàng POS và xử lý đơn"),
    ("WAREHOUSE_STAFF", "Nhân viên kho", "Nhập hàng theo lô, kiểm kê và hủy hàng"),
    ("CUSTOMER", "Khách hàng", "Xem sản phẩm và mua hàng"),
]


class AuthService:
    @staticmethod
    def init_roles_and_admin(db: Session):
        """Khởi tạo các Role mặc định và tài khoản Admin ban đầu nếu chưa có"""
        # 1. Tạo các roles nếu chưa có
        for code, name, desc in DEFAULT_ROLES:
            existing_role = db.query(Role).filter(Role.code == code).first()
            if not existing_role:
                db.add(Role(code=code, name=name, description=desc))
        db.commit()

        # 2. Tạo tài khoản Admin mặc định nếu chưa có
        admin_email = "admin@fruitstore.com"
        existing_admin = db.query(User).filter(User.email == admin_email).first()
        if not existing_admin:
            admin_role = db.query(Role).filter(Role.code == "ADMIN").first()
            new_admin = User(
                email=admin_email,
                full_name="System Administrator",
                phone="0901234567",
                password_hash=hash_password("admin123"),
                status="ACTIVE",
            )
            if admin_role:
                new_admin.roles.append(admin_role)
            db.add(new_admin)
            db.commit()

    @staticmethod
    def get_by_email(db: Session, email: str) -> Optional[User]:
        return db.query(User).filter(User.email == email).first()

    @staticmethod
    def get_by_id(db: Session, user_id: uuid.UUID) -> Optional[User]:
        return db.query(User).filter(User.id == user_id).first()

    @staticmethod
    def register(db: Session, user_in: UserRegister) -> User:
        """Đăng ký tài khoản người dùng mới"""
        # Kiểm tra email trùng lặp
        if AuthService.get_by_email(db, user_in.email):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email này đã được sử dụng trên hệ thống.",
            )

        # Kiểm tra số điện thoại nếu có
        if user_in.phone:
            existing_phone = db.query(User).filter(User.phone == user_in.phone).first()
            if existing_phone:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Số điện thoại này đã được sử dụng.",
                )

        # Tìm role
        role_code = user_in.role_code or "CUSTOMER"
        role = db.query(Role).filter(Role.code == role_code.upper()).first()
        if not role:
            role = db.query(Role).filter(Role.code == "CUSTOMER").first()

        user = User(
            email=user_in.email,
            full_name=user_in.full_name,
            phone=user_in.phone,
            password_hash=hash_password(user_in.password),
            status="ACTIVE",
        )
        if role:
            user.roles.append(role)

        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def authenticate(db: Session, email: str, password: str) -> User:
        """Xác thực tài khoản và mật khẩu"""
        user = AuthService.get_by_email(db, email)
        if not user or not verify_password(password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Email hoặc mật khẩu không chính xác.",
            )

        if user.status != "ACTIVE":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Tài khoản hiện đang bị khóa hoặc không kích hoạt.",
            )

        # Cập nhật thời điểm đăng nhập gần nhất
        user.last_login_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def authenticate_google(db: Session, credential: str) -> User:
        """Xác thực Google ID Token và đăng nhập hoặc tự động tạo tài khoản"""
        import jwt
        from app.core.config import settings

        try:
            # Giải mã Google ID Token
            payload = jwt.decode(credential, options={"verify_signature": False})
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Google Token không hợp lệ: {str(e)}",
            )

        # Kiểm tra Audience và Issuer
        aud = payload.get("aud")
        iss = payload.get("iss")
        if aud != settings.GOOGLE_CLIENT_ID:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Google Client ID không khớp với hệ thống.",
            )

        if iss not in ["accounts.google.com", "https://accounts.google.com"]:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Issuer của Google Token không hợp lệ.",
            )

        email = payload.get("email")
        if not email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Không tìm thấy email trong thông tin Google cung cấp.",
            )

        full_name = payload.get("name") or email.split("@")[0]

        # Kiểm tra xem user đã tồn tại chưa
        user = AuthService.get_by_email(db, email)
        if user:
            if user.status != "ACTIVE":
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Tài khoản liên kết với Google này đang bị khóa.",
                )
            user.last_login_at = datetime.now(timezone.utc)
            db.commit()
            db.refresh(user)
            return user

        # Nếu user chưa có, tự động tạo tài khoản mới từ Google
        customer_role = db.query(Role).filter(Role.code == "CUSTOMER").first()
        random_hash = hash_password(str(uuid.uuid4()))

        new_user = User(
            email=email,
            full_name=full_name,
            phone=None,
            password_hash=random_hash,
            status="ACTIVE",
        )
        if customer_role:
            new_user.roles.append(customer_role)

        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        return new_user

