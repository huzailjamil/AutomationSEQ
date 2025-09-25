import os
import smtplib
from email.message import EmailMessage
from typing import Optional

SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASS = os.getenv("SMTP_PASS", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", 465))


def send_email_smtp(to: str, subject: str, body: str, reply_to: Optional[str] = None) -> None:
    """Send an email using basic SMTP credentials."""

    if not SMTP_HOST or not SMTP_USER or not SMTP_PASS:
        raise RuntimeError("SMTP credentials are not configured")

    message = EmailMessage()
    message["From"] = SMTP_USER
    message["To"] = to
    message["Subject"] = subject
    if reply_to:
        message["Reply-To"] = reply_to
    message.set_content(body)

    with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, timeout=20) as server:
        server.login(SMTP_USER, SMTP_PASS)
        server.send_message(message)
