"""Simple SMTP email service for EduGuard.

Provides a small synchronous helper `send_email` that wraps smtplib and the
application settings. Intentionally lightweight so it can be used from
FastAPI routes, background tasks, or scheduler jobs.

Behaviour:
- Reads SMTP configuration from `app.config.settings`.
- If `settings.DEBUG` is True it performs a dry-run and logs the mail instead of
  actually connecting to the SMTP server. This prevents accidental sends from
  development environments. (Adjust as required.)
- Retries on failure up to `retries` times with `retry_delay` seconds delay.

Usage example::

    from app.core.email_service import send_email

    send_email(
        to_addresses=["student@example.com"],
        subject="Test email",
        html_body="<p>Hello</p>",
        text_body="Hello",
    )

You may want to call this from a FastAPI BackgroundTask or from a job
worker if sending at scale.
"""

from __future__ import annotations

import logging
import smtplib
import time
from email.message import EmailMessage
from typing import Iterable, List, Optional, Union

from app.config import settings

log = logging.getLogger(__name__)


def _normalize_addresses(addresses: Optional[Union[str, Iterable[str]]]) -> List[str]:
    if addresses is None:
        return []
    if isinstance(addresses, str):
        return [addresses]
    return [str(a).strip() for a in addresses]


def send_email(
    to_addresses: Optional[Union[str, Iterable[str]]],
    subject: str,
    html_body: Optional[str] = None,
    text_body: Optional[str] = None,
    cc: Optional[Union[str, Iterable[str]]] = None,
    bcc: Optional[Union[str, Iterable[str]]] = None,
    retries: int = 3,
    retry_delay: int = 5,
) -> bool:
    """Send an email via the configured SMTP server.

    Returns True on success, False on final failure after retries.

    Notes:
    - Uses STARTTLS when SMTP_PORT is 587.
    - If settings.DEBUG is True the function logs the payload and returns True
      without connecting to an SMTP server (safe default for development).
    """

    to_list = _normalize_addresses(to_addresses)
    if not to_list:
        log.warning("send_email called with no recipient addresses")
        return False

    cc_list = _normalize_addresses(cc)
    bcc_list = _normalize_addresses(bcc)

    msg = EmailMessage()
    msg["From"] = settings.EMAIL_FROM
    msg["To"] = ", ".join(to_list)
    if cc_list:
        msg["Cc"] = ", ".join(cc_list)
    msg["Subject"] = subject

    # prefer a plain-text body if provided
    if text_body and html_body:
        msg.set_content(text_body)
        msg.add_alternative(html_body, subtype="html")
    elif html_body:
        # provide a fallback plain text
        msg.set_content("Please view this email in an HTML-capable client.")
        msg.add_alternative(html_body, subtype="html")
    else:
        msg.set_content(text_body or "")

    all_recipients = to_list + cc_list + bcc_list

    # Development-safe behaviour: don't actually send when DEBUG=True
    if getattr(settings, "DEBUG", False):
        log.info("[email_service] DEBUG=True — dry-run mode. Email not sent.")
        log.info("From: %s", settings.EMAIL_FROM)
        log.info("To: %s", all_recipients)
        log.info("Subject: %s", subject)
        log.debug("Message object:\n%s", msg)
        return True

    host = settings.SMTP_HOST
    port = settings.SMTP_PORT
    username = settings.SMTP_USERNAME
    password = settings.SMTP_PASSWORD

    last_exc: Optional[Exception] = None
    for attempt in range(1, retries + 1):
        try:
            log.info("Connecting to SMTP server %s:%s (attempt %s/%s)", host, port, attempt, retries)
            with smtplib.SMTP(host, port, timeout=30) as server:
                server.ehlo()
                # STARTTLS for common submission port
                try:
                    server.starttls()
                    server.ehlo()
                except Exception:
                    log.debug("STARTTLS not available or failed on server — continuing without it", exc_info=True)

                if username and password:
                    server.login(username, password)

                server.send_message(msg, from_addr=settings.EMAIL_FROM, to_addrs=all_recipients)

            log.info("Email sent to %s", all_recipients)
            return True

        except Exception as exc:  # noqa: BLE001 - broad catch to implement retry semantics
            last_exc = exc
            log.warning("SMTP send attempt %s/%s failed: %s", attempt, retries, exc)
            if attempt < retries:
                log.info("Retrying in %s seconds...", retry_delay)
                time.sleep(retry_delay)

    log.error("All SMTP send attempts failed. Last error: %s", last_exc)
    return False
