"""
Module: app.core.email (Auth Service)
Nhiệm vụ: Gửi email mã xác nhận OTP 6 chữ số qua Gmail SMTP (TLS cổng 587, App Password)
          phục vụ tính năng Quên mật khẩu (FR-A10).
"""

from email.message import EmailMessage
import logging
import smtplib

from app.core.config import settings

logger = logging.getLogger("auth-service.email")


def send_password_reset_email(to_email: str, full_name: str, otp_code: str) -> None:
    """
    Gửi email chứa mã OTP 6 chữ số (TTL 15 phút) qua Gmail SMTP.
    Nếu chưa cấu hình `SMTP_USER` / `SMTP_PASSWORD` (ví dụ môi trường test), chỉ ghi log cảnh báo.
    """
    if not settings.SMTP_USER or not settings.SMTP_PASSWORD:
        logger.warning(
            "Chưa cấu hình SMTP_USER/SMTP_PASSWORD. Bỏ qua gửi email OTP tới %s.",
            to_email,
        )
        return

    msg = EmailMessage()
    msg["Subject"] = f"[Fresh Orchard] Mã xác nhận đặt lại mật khẩu: {otp_code}"
    msg["From"] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_USER}>"
    msg["To"] = to_email

    plain_body = (
        f"Xin chào {full_name},\n\n"
        f"Mã xác nhận (OTP) để đặt lại mật khẩu tài khoản Fresh Orchard của bạn là:\n\n"
        f"    {otp_code}\n\n"
        f"Mã có hiệu lực trong {settings.RESET_TOKEN_EXPIRE_MINUTES} phút và chỉ sử dụng được 1 lần.\n"
        f"Nếu bạn không thực hiện yêu cầu này, vui lòng bỏ qua email này.\n\n"
        f"Trân trọng,\nFresh Orchard FruitStore"
    )

    html_body = f"""
    <div style="font-family: Arial, sans-serif; max-width: 560px; margin: 0 auto; padding: 24px; border: 1px solid #E2E8F0; border-radius: 12px; color: #0F172A;">
      <h2 style="color: #15803D; margin-top: 0;">Fresh Orchard FruitStore</h2>
      <p>Xin chào <strong>{full_name}</strong>,</p>
      <p>Mã xác nhận (OTP) để đặt lại mật khẩu cho tài khoản của bạn là:</p>
      <div style="margin: 24px 0; padding: 16px; background-color: #F0FDF4; border: 1px dashed #15803D; border-radius: 10px; text-align: center;">
        <span style="font-size: 32px; font-weight: 700; letter-spacing: 8px; color: #14532D; font-family: monospace;">{otp_code}</span>
      </div>
      <p style="font-size: 13.5px; color: #334155;">
        Mã có hiệu lực trong <strong>{settings.RESET_TOKEN_EXPIRE_MINUTES} phút</strong> và chỉ sử dụng được 1 lần.
      </p>
      <hr style="border: none; border-top: 1px solid #E2E8F0; margin: 20px 0;" />
      <p style="font-size: 12px; color: #64748B; margin-bottom: 0;">Nếu bạn không yêu cầu đặt lại mật khẩu, hãy bỏ qua email này.</p>
    </div>
    """

    msg.set_content(plain_body)
    msg.add_alternative(html_body, subtype="html")

    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=15) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.send_message(msg)
        logger.info("Đã gửi email OTP đặt lại mật khẩu tới %s.", to_email)
    except Exception as exc:
        logger.exception("Lỗi gửi email OTP đặt lại mật khẩu tới %s: %s", to_email, exc)
