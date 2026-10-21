"""Webhook Notification Service for Microsoft Teams and Slack."""
import json
import logging
from typing import Dict, Any, Optional
import urllib.request
import urllib.error

from app.core.config import settings

logger = logging.getLogger(__name__)


def _send_http_post(url: str, payload: Dict[str, Any], timeout: int = 5) -> bool:
    """Helper to dispatch HTTP POST JSON with timeout."""
    try:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return response.status in (200, 204)
    except Exception as exc:
        logger.warning("Error enviando webhook a %s: %s", url[:45], exc)
        return False


def send_teams_alert(
    webhook_url: str,
    instance_name: str,
    metric_name: str,
    severity: str,
    current_value: str,
    threshold_value: str,
    title: str,
    message: str
) -> bool:
    """
    Envía una tarjeta interactiva (Adaptive Card / MessageCard) a Microsoft Teams.
    """
    if not webhook_url:
        return False

    is_critical = severity.upper() == "CRITICAL"
    theme_color = "DC2626" if is_critical else "F59E0B"
    emoji = "🚨" if is_critical else "⚠️"

    payload = {
        "@type": "MessageCard",
        "@context": "http://schema.org/extensions",
        "themeColor": theme_color,
        "summary": f"{emoji} Alerta DBA: {title}",
        "sections": [
            {
                "activityTitle": f"{emoji} DataCheck Pro - {title}",
                "activitySubtitle": f"Instancia: {instance_name} | Severidad: {severity.upper()}",
                "activityImage": "https://img.icons8.com/fluency/48/database-administrator.png",
                "facts": [
                    {"name": "Base de Datos / Host:", "value": instance_name},
                    {"name": "Métrica Anómala:", "value": metric_name},
                    {"name": "Valor Registrado:", "value": current_value},
                    {"name": "Umbral de Alerta:", "value": threshold_value},
                    {"name": "Severidad:", "value": severity.upper()}
                ],
                "text": message,
                "markdown": True
            }
        ],
        "potentialAction": [
            {
                "@type": "OpenURI",
                "name": "Abrir DataCheck Pro",
                "targets": [
                    {"os": "default", "uri": settings.FRONTEND_URL}
                ]
            }
        ]
    }
    return _send_http_post(webhook_url, payload)


def send_slack_alert(
    webhook_url: str,
    instance_name: str,
    metric_name: str,
    severity: str,
    current_value: str,
    threshold_value: str,
    title: str,
    message: str
) -> bool:
    """
    Envía un mensaje enriquecido con Block Kit a Slack.
    """
    if not webhook_url:
        return False

    is_critical = severity.upper() == "CRITICAL"
    color = "#dc2626" if is_critical else "#f59e0b"
    emoji = "🚨" if is_critical else "⚠️"

    payload = {
        "text": f"{emoji} Alerta DBA [{instance_name}]: {title}",
        "attachments": [
            {
                "color": color,
                "blocks": [
                    {
                        "type": "header",
                        "text": {
                            "type": "plain_text",
                            "text": f"{emoji} DataCheck Pro: {title}"
                        }
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"*{message}*"
                        }
                    },
                    {
                        "type": "section",
                        "fields": [
                            {"type": "mrkdwn", "text": f"*Instancia:*\n{instance_name}"},
                            {"type": "mrkdwn", "text": f"*Severidad:*\n`{severity.upper()}`"},
                            {"type": "mrkdwn", "text": f"*Métrica:*\n{metric_name}"},
                            {"type": "mrkdwn", "text": f"*Valor:*\n`{current_value}` (Umbral: {threshold_value})"}
                        ]
                    },
                    {
                        "type": "actions",
                        "elements": [
                            {
                                "type": "button",
                                "text": {
                                    "type": "plain_text",
                                    "text": "Ver en Dashboard"
                                },
                                "url": settings.FRONTEND_URL,
                                "style": "primary" if is_critical else "default"
                            }
                        ]
                    }
                ]
            }
        ]
    }
    return _send_http_post(webhook_url, payload)


def dispatch_webhooks(
    instance_name: str,
    metric_name: str,
    severity: str,
    current_value: str,
    threshold_value: str,
    title: str,
    message: str
) -> Dict[str, bool]:
    """
    Despacha notificaciones a los webhooks activos configurados (Teams y/o Slack).
    """
    results = {}

    teams_url = settings.TEAMS_WEBHOOK_URL
    if teams_url:
        results["teams"] = send_teams_alert(
            webhook_url=teams_url,
            instance_name=instance_name,
            metric_name=metric_name,
            severity=severity,
            current_value=current_value,
            threshold_value=threshold_value,
            title=title,
            message=message
        )

    slack_url = settings.SLACK_WEBHOOK_URL
    if slack_url:
        results["slack"] = send_slack_alert(
            webhook_url=slack_url,
            instance_name=instance_name,
            metric_name=metric_name,
            severity=severity,
            current_value=current_value,
            threshold_value=threshold_value,
            title=title,
            message=message
        )

    return results
