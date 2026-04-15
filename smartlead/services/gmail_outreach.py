from __future__ import annotations

import smtplib
from email.message import EmailMessage

from smartlead.core.settings import Settings


def send_plain_email(
    settings: Settings,
    *,
    to_addr: str,
    subject: str,
    body: str,
) -> None:
    sender = (settings.sender_email or "").strip()
    password = (settings.gmail_smtp_key or "").strip()
    if not sender or not password:
        raise ValueError("SENDER_EMAIL and GMAIL_SMTP_KEY must be set.")

    to_addr = to_addr.strip()
    if not to_addr:
        raise ValueError("Recipient address is empty.")

    msg = EmailMessage()
    msg["Subject"] = subject.strip() or "(no subject)"
    msg["From"] = sender
    msg["To"] = to_addr
    msg.set_content(body)

    with smtplib.SMTP("smtp.gmail.com", 587, timeout=60) as smtp:
        smtp.ehlo()
        smtp.starttls()
        smtp.ehlo()
        smtp.login(sender, password)
        smtp.send_message(msg)