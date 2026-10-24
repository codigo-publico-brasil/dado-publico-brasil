"""Alerta por e-mail (SMTP), configurado por variável de ambiente; sem configuração, não envia."""

import os
import smtplib
import ssl
from email.message import EmailMessage


def send(subject: str, body: str) -> bool:
    """Envia o e-mail. Devolve False se o SMTP ou o destinatário não estiverem configurados."""
    host, to = os.environ.get("DADO_PUBLICO_SMTP_HOST"), os.environ.get("DADO_PUBLICO_ALERT_TO")
    if not host or not to:
        return False
    user = os.environ.get("DADO_PUBLICO_SMTP_USER")
    port = int(os.environ.get("DADO_PUBLICO_SMTP_PORT", "587"))
    message = EmailMessage()
    message["Subject"], message["To"] = subject, to
    message["From"] = os.environ.get("DADO_PUBLICO_ALERT_FROM") or user or to
    message.set_content(body)
    context = ssl.create_default_context()
    with smtplib.SMTP_SSL(host, port, context=context) if port == 465 else smtplib.SMTP(host, port) as smtp:
        if port != 465:
            smtp.starttls(context=context)
        if user:
            smtp.login(user, os.environ["DADO_PUBLICO_SMTP_PASSWORD"])
        smtp.send_message(message)
    return True
