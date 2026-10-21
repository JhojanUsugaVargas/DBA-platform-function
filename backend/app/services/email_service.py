"""Email and invitation service for DataCheck Platform."""
import os
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any, Optional
from app.core.config import settings


def check_smtp_status() -> Dict[str, Any]:
    """Returns the current SMTP configuration status (without exposing secrets)."""
    smtp_host = settings.SMTP_SERVER or os.getenv("SMTP_SERVER", "") or os.getenv("SMTP_HOST", "")
    smtp_user = settings.SMTP_USER or os.getenv("SMTP_USER", "")
    is_configured = bool(smtp_host and (smtp_user or os.getenv("SMTP_ALLOW_ANONYMOUS", "").lower() in ("1", "true", "yes")))
    return {
        "configured": is_configured,
        "host": smtp_host or "No configurado",
        "port": settings.SMTP_PORT,
        "user": smtp_user or "No configurado",
        "from_address": settings.SMTP_FROM or smtp_user or "soporte@datacheck.local"
    }


def send_user_invitation(
    to_email: str,
    username: str,
    full_name: str,
    password: str,
    role: str,
    unsubscribe_url: Optional[str] = None
) -> Dict[str, Any]:
    """Sends a professional onboarding and credential invitation email to a newly created user."""
    smtp_host = settings.SMTP_SERVER or os.getenv("SMTP_SERVER", "") or os.getenv("SMTP_HOST", "")
    smtp_port = settings.SMTP_PORT or int(os.getenv("SMTP_PORT", "587"))
    smtp_user = settings.SMTP_USER or os.getenv("SMTP_USER", "")
    smtp_password = settings.SMTP_PASSWORD or os.getenv("SMTP_PASSWORD", "")
    smtp_from = settings.SMTP_FROM or os.getenv("SMTP_FROM", "") or smtp_user or "soporte@datacheck.local"
    access_url = settings.FRONTEND_URL
    unsubscribe_html = (
        f'<br><a href="{unsubscribe_url}" style="color:#67e8f9;">Darme de baja de estos correos</a>'
        if unsubscribe_url else ""
    )
    unsubscribe_plain = f"\nPara darte de baja de estos correos: {unsubscribe_url}\n" if unsubscribe_url else ""

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
        .footer {{ text-align: center; font-size: 12px; color: #94a3b8; margin-top: 24px; }}
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
          <a href="{access_url}" class="btn">Acceder a DataCheck Pro</a>
        </div>

        <div class="footer">
          Este correo fue generado automáticamente por DataCheck Pro. Por favor no respondas a este mensaje.<br>
          Tratamos tus datos conforme a nuestra política de privacidad: {access_url}/legal/privacidad{unsubscribe_html}
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
        f"Enlace de acceso: {access_url}\n"
        f"Política de privacidad: {access_url}/legal/privacidad\n"
        f"{unsubscribe_plain}"
    )

    is_configured = bool(smtp_host and (smtp_user or os.getenv("SMTP_ALLOW_ANONYMOUS", "").lower() in ("1", "true", "yes")))

    if not is_configured:
        logging.warning(
            f"[SMTP NOT CONFIGURED] Invitación simulada para {to_email} ({username}). "
            "El servidor SMTP no está configurado en el archivo .env del backend."
        )
        return {
            "sent": False,
            "to": to_email,
            "method": "simulated",
            "detail": "Servidor SMTP no configurado en el archivo .env del backend. El correo no pudo enviarse a internet.",
            "preview_subject": subject
        }

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = smtp_from
        msg["To"] = to_email
        if unsubscribe_url:
            msg["List-Unsubscribe"] = f"<{unsubscribe_url}>"
            msg["List-Unsubscribe-Post"] = "List-Unsubscribe=One-Click"
        msg.attach(MIMEText(plain_content, "plain"))
        msg.attach(MIMEText(html_content, "html"))

        with smtplib.SMTP(smtp_host, smtp_port, timeout=12) as server:
            if settings.SMTP_USE_TLS:
                server.starttls()
            if smtp_user and smtp_password:
                server.login(smtp_user, smtp_password)
            server.sendmail(smtp_from, [to_email], msg.as_string())

        logging.info(f"Invitación por correo enviada con éxito a {to_email}")
        return {"sent": True, "to": to_email, "method": "smtp", "detail": f"Correo enviado exitosamente vía {smtp_host}."}
    except Exception as exc:
        logging.error(f"Error enviando correo SMTP a {to_email}: {exc}")
        return {"sent": False, "to": to_email, "method": "smtp_error", "detail": f"Error SMTP ({smtp_host}): {str(exc)}"}


def send_otp_email(to_email: str, code: str) -> bool:
    """Dispatches a one-time MFA login code via email."""
    smtp_server = settings.SMTP_SERVER or os.getenv("SMTP_SERVER", "") or os.getenv("SMTP_HOST", "")
    smtp_port = settings.SMTP_PORT or 587
    smtp_user = settings.SMTP_USER or os.getenv("SMTP_USER", "")
    smtp_password = settings.SMTP_PASSWORD or os.getenv("SMTP_PASSWORD", "")
    smtp_from = settings.SMTP_FROM or smtp_user or "soporte@datacheck.local"

    if not (smtp_server and (smtp_user or os.getenv("SMTP_ALLOW_ANONYMOUS", "").lower() in ("1", "true", "yes"))):
        logging.info(f"[SIMULATED OTP EMAIL] Código {code} generado para {to_email} (SMTP no configurado)")
        return False

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = "DataCheck Pro - Código de Verificación OTP"
        msg["From"] = smtp_from
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

        with smtplib.SMTP(smtp_server, smtp_port, timeout=12) as s:
            if settings.SMTP_USE_TLS:
                s.starttls()
            if smtp_user and smtp_password:
                s.login(smtp_user, smtp_password)
            s.sendmail(smtp_from, [to_email], msg.as_string())
        return True
    except Exception as exc:
        logging.warning(f"No se pudo enviar email OTP a {to_email}: {exc}")
        return False


def send_alert_email(
    to_email: str,
    instance_name: str,
    metric_name: str,
    severity: str,
    current_value: str,
    threshold_value: str,
    title: str,
    message: str
) -> Dict[str, Any]:
    """Dispatches a critical proactive monitoring alert email to DBA administrators."""
    smtp_host = settings.SMTP_SERVER or os.getenv("SMTP_SERVER", "") or os.getenv("SMTP_HOST", "")
    smtp_port = settings.SMTP_PORT or int(os.getenv("SMTP_PORT", "587"))
    smtp_user = settings.SMTP_USER or os.getenv("SMTP_USER", "")
    smtp_password = settings.SMTP_PASSWORD or os.getenv("SMTP_PASSWORD", "")
    smtp_from = settings.SMTP_FROM or os.getenv("SMTP_FROM", "") or smtp_user or "alertas@datacheck.local"
    access_url = settings.FRONTEND_URL

    severity_color = "#ef4444" if severity == "CRITICAL" else "#f59e0b"
    subject = f"[{severity}] 🚨 Alerta Proactiva DBA - {instance_name} ({metric_name})"

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="utf-8">
      <style>
        body {{ font-family: 'Segoe UI', Arial, sans-serif; background: #0b0c10; color: #e2e8f0; margin: 0; padding: 20px; }}
        .card {{ max-width: 580px; margin: 0 auto; background: #13141f; border: 1px solid #2d3748; border-radius: 12px; padding: 32px; }}
        .badge {{ display: inline-block; background: {severity_color}; color: #ffffff; padding: 4px 12px; border-radius: 6px; font-weight: bold; font-size: 12px; text-transform: uppercase; margin-bottom: 12px; }}
        .title {{ color: #ffffff; font-size: 20px; font-weight: bold; margin: 0 0 10px 0; }}
        .metric-box {{ background: #1a1c29; border: 1px solid #374151; border-radius: 8px; padding: 18px; margin: 20px 0; }}
        .row {{ display: flex; justify-content: space-between; margin-bottom: 8px; font-size: 14px; }}
        .lbl {{ color: #94a3b8; font-weight: 500; }}
        .val {{ color: #ffffff; font-family: monospace; font-weight: bold; }}
        .val-alert {{ color: {severity_color}; font-family: monospace; font-weight: bold; }}
        .btn {{ display: inline-block; background: #00e5ff; color: #000000; padding: 10px 24px; border-radius: 6px; text-decoration: none; font-weight: bold; margin-top: 15px; text-align: center; }}
        .footer {{ text-align: center; font-size: 12px; color: #64748b; margin-top: 24px; }}
      </style>
    </head>
    <body>
      <div class="card">
        <span class="badge">{severity}</span>
        <h2 class="title">{title}</h2>
        <p style="color: #cbd5e1; font-size: 14px; line-height: 1.5;">{message}</p>

        <div class="metric-box">
          <div class="row"><span class="lbl">Instancia Afectada:</span> <span class="val">{instance_name}</span></div>
          <div class="row"><span class="lbl">Métrica Monitoreada:</span> <span class="val">{metric_name}</span></div>
          <div class="row"><span class="lbl">Valor Registrado:</span> <span class="val-alert">{current_value}</span></div>
          <div class="row"><span class="lbl">Umbral Configurado:</span> <span class="val">{threshold_value}</span></div>
        </div>

        <div style="text-align: center;">
          <a href="{access_url}" class="btn">Abrir Telemetría en DataCheck Pro</a>
        </div>

        <div class="footer">
          Generado automáticamente por el motor de supervisión proactiva DataCheck Pro.<br>
          Para gestionar umbrales o destinatarios, contacta a la administración de plataforma.
        </div>
      </div>
    </body>
    </html>
    """

    plain_content = (
        f"[{severity}] ALERTA PROACTIVA DBA - {instance_name}\n\n"
        f"Métrica: {metric_name}\n"
        f"Valor Actual: {current_value} (Umbral: {threshold_value})\n\n"
        f"Detalle: {message}\n\n"
        f"Acceso a la plataforma: {access_url}\n"
    )

    is_configured = bool(smtp_host and (smtp_user or os.getenv("SMTP_ALLOW_ANONYMOUS", "").lower() in ("1", "true", "yes")))
    if not is_configured:
        logging.info(f"[SIMULATED ALERT EMAIL] Alerta {severity} {metric_name} para {to_email} ({instance_name})")
        return {"sent": False, "method": "simulated", "detail": "SMTP no configurado"}

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = smtp_from
        msg["To"] = to_email
        msg.attach(MIMEText(plain_content, "plain"))
        msg.attach(MIMEText(html_content, "html"))

        with smtplib.SMTP(smtp_host, smtp_port, timeout=12) as server:
            if settings.SMTP_USE_TLS:
                server.starttls()
            if smtp_user and smtp_password:
                server.login(smtp_user, smtp_password)
            server.sendmail(smtp_from, [to_email], msg.as_string())

        logging.info(f"Alerta enviada por correo a {to_email} ({instance_name})")
        return {"sent": True, "to": to_email, "method": "smtp"}
    except Exception as exc:
        logging.error(f"Error enviando alerta por correo a {to_email}: {exc}")
        return {"sent": False, "to": to_email, "error": str(exc)}


