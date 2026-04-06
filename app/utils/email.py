"""
app/utils/email.py - 异步邮件发送工具（aiosmtplib + SMTP）
"""
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import aiosmtplib

from app.config import settings

logger = logging.getLogger(__name__)


def _build_otp_html(otp: str, purpose: str = "register") -> str:
    action = "注册" if purpose == "register" else "重置密码"
    return f"""
<!DOCTYPE html>
<html>
<body style="font-family:'Roboto',Arial,sans-serif;background:#f1f3f4;margin:0;padding:40px 0;">
  <div style="max-width:480px;margin:0 auto;background:#fff;border-radius:16px;
              box-shadow:0 1px 6px rgba(0,0,0,.1);overflow:hidden;">
    <div style="background:#0b57d0;padding:28px 40px;">
      <div style="color:#fff;font-size:22px;font-weight:700;letter-spacing:1px;">TOOLKIT</div>
    </div>
    <div style="padding:40px;">
      <h2 style="color:#202124;font-weight:400;margin:0 0 12px;">您的 {action} 验证码</h2>
      <p style="color:#444746;margin:0 0 32px;line-height:1.6;">
        请在 10 分钟内使用以下验证码完成{action}，切勿将验证码分享给他人。
      </p>
      <div style="background:#e8f0fe;border-radius:12px;padding:24px;text-align:center;margin-bottom:32px;">
        <span style="font-size:40px;font-weight:700;letter-spacing:12px;color:#0b57d0;">{otp}</span>
      </div>
      <p style="color:#80868b;font-size:13px;margin:0;">
        如果您没有申请此验证码，请忽略本邮件。<br>
        此验证码将在 <strong>10 分钟</strong>后失效。
      </p>
    </div>
    <div style="padding:20px 40px;border-top:1px solid #e8eaed;color:#80868b;font-size:12px;">
      © 2024 TOOLKIT · 此邮件由系统自动发送，请勿回复
    </div>
  </div>
</body>
</html>"""


async def send_otp_email(to_email: str, otp: str, purpose: str = "register") -> bool:
    """
    发送 OTP 验证码邮件
    :returns: True 发送成功，False 失败（如 SMTP 未配置则直接打印到日志）
    """
    # ── 开发模式：SMTP 未配置时直接打印到控制台 ────────────────────────────────
    if not settings.smtp_user or not settings.smtp_password:
        logger.warning(f"[EMAIL] SMTP not configured. OTP for {to_email}: {otp}")
        return True  # 开发时视为成功

    action = "注册" if purpose == "register" else "重置密码"
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"【TOOLKIT】您的{action}验证码：{otp}"
    msg["From"] = f"{settings.smtp_from_name} <{settings.smtp_user}>"
    msg["To"] = to_email

    msg.attach(MIMEText(_build_otp_html(otp, purpose), "html", "utf-8"))

    try:
        await aiosmtplib.send(
            msg,
            hostname=settings.smtp_host,
            port=settings.smtp_port,
            username=settings.smtp_user,
            password=settings.smtp_password,
            start_tls=settings.smtp_tls,
        )
        logger.info(f"[EMAIL] OTP sent to {to_email}")
        return True
    except Exception as e:
        logger.error(f"[EMAIL] Failed to send to {to_email}: {e}")
        return False
