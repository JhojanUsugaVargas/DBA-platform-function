"""Email and invitation service for DataCheck Platform."""
import os
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any, Optional
from app.core.config import settings


def send_user_invitation(
    to_email: str,
    username: str,
    full_name: str,
    password: str,
    role: str
) -> Dict[str, Any]:
    """Sends a professional onboarding and credential invitation email to a newly created user."""
    smtp_host = os.getenv("SMTP_HOST", "")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER", "")
    smtp_password = os.getenv("SMTP_PASSWORD", "")
    smtp_from = os.getenv("SMTP_FROM", "soporte@datacheck.local")

    subject = f"🔐 Invitación y Credenciales de Acceso - DataCheck Pro ({role})"
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="utf-8">
      <style>
        body {{ font-family: 'Segoe UI', Arial, sans-serif; background: #0b0c10; color: #e2e8f0; margin: 0; padding: 20px; }}
        .card {{ max-width: 540px; margin: 0 auto; background: #13141f; border: 1px solid #2d3748; border-radius: 12px; padding: 32px; }}
        .header {{ text-align: center; border-bottom: 1px solid #2d3748; padding-bottom: 20px; margin-bottom: 24px; }}
        .title {{ color: #00e5ff; font-size: 22px; font-weight: bold; margin: 0; }}
        .subtitle {{ color: #94a3b8; font-size: 13px; margin-top: 6px; }}
        .cred-box {{ background: #1a1c29; border: 1px solid #3b82f6; border-radius: 8px; padding: 18px; margin: 20px 0; }}
        .cred-row {{ display: flex; justify-content: space-between; margin-bottom: 8px; font-size: 14px; }}
        .cred-label {{ color: #94a3b8; font-weight: 500; }}
        .cred-val {{ color: #ffffff; font-family: monospace; font-weight: bold; }}
        .btn {{ display: inline-block; background: #00e5ff; color: #000000; padding: 10px 24px; border-radius: 6px; text-decoration: none; font-weight: bold; margin-top: 15px; text-align: center; }}
        .footer {{ text-align: center; font-size: 11px; color: #64748b; margin-top: 24px; }}
      </style>
    </head>
    <body>
      <div class="card">
        <div class="header">
          <div class="title">🛡️ DataCheck Pro</div>
          <div class="subtitle">Plataforma de Monitoreo & Copiloto DBA Multimotor</div>
        </div>
        <p>Hola <strong>{full_name}</strong>,</p>
        <p>Has sido dado de alta como usuario en la plataforma con el rol de <strong>{role}</strong>.</p>
        
        <div class="cred-box">
          <div class="cred-row"><span class="cred-label">Usuario:</span> <span class="cred-val">{username}</span></div>
          <div class="cred-row"><span class="cred-label">Contraseña inicial:</span> <span class="cred-val">{password}</span></div>
          <div class="cred-row"><span class="cred-label">Rol:</span> <span class="cred-val">{role}</span></div>
        </div>

        <p style="font-size: 13px; color: #cbd5e1;">Por motivos de seguridad, te sugerimos cambiar tu contraseña inmediatamente después de tu primer inicio de sesión.</p>

        <div style="text-align: center;">
          <a href="http://localhost:4200" class="btn">Acceder a DataCheck Pro</a>
        </div>

        <div class="footer">
          Este correo fue generado automáticamente por DataCheck Pro. Por favor no respondas a este mensaje.
        </div>
      </div>
    </body>
    </html>
    """

    plain_content = (
        f"Hola {full_name},\n\n"
        f"Has sido invitado a DataCheck Pro con el rol {role}.\n\n"
        f"Tus credenciales de acceso son:\n"
        f"- Usuario: {username}\n"
        f"- Contraseña inicial: {password}\n\n"
        f"Enlace de acceso: http://localhost:4200\n"
    )

    if smtp_host:
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = smtp_from
            msg["To"] = to_email
            msg.attach(MIMEText(plain_content, "plain"))
            msg.attach(MIMEText(html_content, "html"))

            with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as server:
                server.starttls()
                if smtp_user and smtp_password:
                    server.login(smtp_user, smtp_password)
                server.sendmail(smtp_from, [to_email], msg.as_string())

            logging.info(f"Invitación por correo enviada con éxito a {to_email}")
            return {"sent": True, "to": to_email, "method": "smtp", "detail": "Correo enviado vía SMTP."}
        except Exception as exc:
            logging.error(f"Error enviando correo SMTP a {to_email}: {exc}")
            return {"sent": False, "to": to_email, "method": "smtp_error", "detail": str(exc)}
    else:
        # En entornos locales o de desarrollo sin SMTP configurado, simulación transparente y segura
        logging.info(f"[SIMULATED EMAIL] Invitación generada para {to_email} ({username})")
        return {
            "sent": True,
            "to": to_email,
            "method": "simulated",
            "detail": f"Invitación despachada para {to_email} (servidor SMTP local simulado).",
            "preview_subject": subject
        }


def send_otp_email(to_email: str, code: str) -> bool:
    """Dispatches a one-time MFA login code via email."""
    smtp_server = settings.SMTP_SERVER or os.getenv("SMTP_SERVER", "")
    smtp_port = settings.SMTP_PORT or 587
    smtp_user = settings.SMTP_USER or os.getenv("SMTP_USER", "")
    smtp_password = settings.SMTP_PASSWORD or os.getenv("SMTP_PASSWORD", "")

    if not smtp_user:
        logging.info(f"[SIMULATED OTP EMAIL] Código {code} generado para {to_email}")
        return False

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = "DataCheck Pro - Código de Verificación OTP"
        msg["From"] = smtp_user
        msg["To"] = to_email

        html = f"""
        <html><body>
          <h2>Código de Verificación DataCheck Pro</h2>
          <p>Tu código de seguridad temporal es: <strong>{code}</strong></p>
          <p>Expira en {settings.OTP_EXPIRE_SECONDS} segundos.</p>
        </body></html>
        """
        msg.attach(MIMEText(f"Tu código OTP es: {code}", "plain"))
        msg.attach(MIMEText(html, "html"))

        with smtplib.SMTP(smtp_server, smtp_port, timeout=10) as s:
            s.starttls()
            s.login(smtp_user, smtp_password)
            s.sendmail(smtp_user, [to_email], msg.as_string())
        return True
    except Exception as exc:
        logging.warning(f"No se pudo enviar email OTP a {to_email}: {exc}")
        return False

