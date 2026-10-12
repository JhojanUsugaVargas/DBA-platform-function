"""Email dispatching service for OTP verification."""
import smtplib
from email.message import EmailMessage
import logging
from app.core.config import settings


def send_otp_email(dest_email: str, otp_code: str) -> bool:
    """Send one-time security password (OTP) via SMTP using environment configuration."""
    if not settings.SMTP_USER or not settings.SMTP_PASSWORD:
        logging.warning("SMTP credentials not configured in environment. OTP email skipped.")
        return False

    try:
        msg = EmailMessage()
        html_content = f"""
        <html>
            <body style="font-family: 'Segoe UI', Arial, sans-serif; background-color: #0a0a0a; color: #ededed; padding: 20px;">
                <div style="max-width: 480px; margin: 0 auto; background-color: #141414; padding: 30px; border-radius: 12px; border: 1px solid rgba(255,255,255,0.1); box-shadow: 0 8px 32px rgba(0,0,0,0.5);">
                    <h2 style="color: #ffffff; text-align: center; margin-top: 0;">DataCheck Security</h2>
                    <p style="color: #a1a1aa; font-size: 14px; line-height: 1.5;">Hola,</p>
                    <p style="color: #a1a1aa; font-size: 14px; line-height: 1.5;">Se ha solicitado acceso a la plataforma <strong>DataCheck</strong>. Usa el siguiente código de verificación:</p>
                    <div style="text-align: center; margin: 30px 0;">
                        <span style="font-size: 32px; font-weight: 700; color: #00e5ff; background-color: rgba(0, 229, 255, 0.1); padding: 12px 28px; border-radius: 8px; letter-spacing: 6px; border: 1px solid rgba(0,229,255,0.3);">
                            {otp_code}
                        </span>
                    </div>
                    <p style="color: #52525b; font-size: 12px; text-align: center; margin-bottom: 0;">Válido durante {settings.OTP_EXPIRE_SECONDS // 60} minutos. Si no lo solicitaste, puedes ignorar este mensaje.</p>
                </div>
            </body>
        </html>
        """
        msg.add_alternative(html_content, subtype="html")
        msg["Subject"] = "Código de Acceso - DataCheck Security"
        msg["From"] = settings.SMTP_USER
        msg["To"] = dest_email

        server = smtplib.SMTP(settings.SMTP_SERVER, settings.SMTP_PORT, timeout=10)
        server.starttls()
        server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        server.send_message(msg)
        server.quit()

        logging.info(f"Correo OTP enviado a {dest_email}")
        return True
    except Exception as exc:
        logging.error(f"Error al enviar correo OTP a {dest_email}: {exc}")
        return False
