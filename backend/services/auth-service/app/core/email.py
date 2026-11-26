"""
Module: app.core.email (Auth Service)
Nhiệm vụ: Gửi email đặt lại mật khẩu qua Gmail SMTP (TLS cổng 587, dùng App Password)
          phục vụ tính năng Quên mật khẩu (FR-A10).
"""

from email.message import EmailMessage
import logging
import smtplib

from app.core.config import settings

logger = logging.getLogger("auth-service.email")


def send_password_reset_email(to_email: str, full_name: str, reset_link: str) -> None:
    """
    Gửi email chứa liên kết đặt lại mật khẩu (TTL 15 phút) qua Gmail SMTP.
    Nếu chưa cấu hình `SMTP_USER` / `SMTP_PASSWORD` (ví dụ môi trường test), chỉ ghi log cảnh báo.
    """
    if not settings.SMTP_USER or not settings.SMTP_PASSWORD:
        logger.warning(
            "Chưa cấu hình SMTP_USER/SMTP_PASSWORD. Bỏ qua gửi email đặt lại mật khẩu tới %s.",
            to_email,
        )
        return

    msg = EmailMessage()
    msg["Subject"] = "[Fresh Orchard] Yêu cầu đặt lại mật khẩu tài khoản"
    msg["From"] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_USER}>"
    msg["To"] = to_email

    plain_body = (
        f"Xin chào {full_name},\n\n"
        f"Chúng tôi nhận được yêu cầu đặt lại mật khẩu cho tài khoản Fresh Orchard của bạn.\n"
        f"Vui lòng mở liên kết sau để đặt lại mật khẩu (liên kết có hiệu lực trong "
        f"{settings.RESET_TOKEN_EXPIRE_MINUTES} phút):\n\n"
        f"{reset_link}\n\n"
        f"Nếu bạn không thực hiện yêu cầu này, vui lòng bỏ qua email này.\n"
        f"Trân trọng,\nFresh Orchard FruitStore"
    )

    html_body = f"""
    <div style="font-family: Arial, sans-serif; max-width: 560px; margin: 0 auto; padding: 24px; border: 1px solid #E2E8F0; border-radius: 12px; color: #0F172A;">
      <h2 style="color: #15803D; margin-top: 0;">Fresh Orchard FruitStore</h2>
      <p>Xin chào <strong>{full_name}</strong>,</p>
      <p>Chúng tôi nhận được yêu cầu đặt lại mật khẩu cho tài khoản của bạn. Liên kết bên dưới có hiệu lực trong <strong>{settings.RESET_TOKEN_EXPIRE_MINUTES} phút</strong>:</p>
      <p style="margin: 24px 0;">
        <a href="{reset_link}" style="background-color: #15803D; color: #FFFFFF; padding: 12px 20px; border-radius: 8px; text-decoration: none; font-weight: 600; display: inline-block;">
          Đặt lại mật khẩu
        </a>
      </p>
      <p style="font-size: 13px; color: #475569;">Hoặc sao chép đường dẫn sau vào trình duyệt:<br/><a href="{reset_link}">{reset_link}</a></p>
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
        logger.info("Đã gửi email đặt lại mật khẩu tới %s.", to_email)
    except Exception as exc:
        logger.exception("Lỗi gửi email đặt lại mật khẩu tới %s: %s", to_email, exc)
