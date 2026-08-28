"""
How an email actually leaves the building (Phase 7.8).

TWO BACKENDS, CHOSEN BY ENVIRONMENT.

  ConsoleBackend  writes each message to a .eml file under
                  var/outbox/ and returns success. Selected whenever
                  ENVIRONMENT is not "production".
  SmtpBackend     dials the real server.

That default is a safety rule, not a convenience. This project's seed
data contains realistic-looking student addresses, and the whole point
of the feature is that it sends email without being asked. A developer
running the weekly sweep against a populated database with live SMTP
credentials mails strangers. Defaulting to the console backend means
the entire flow - queueing, rendering, retrying, the log - is testable
end to end with nothing leaving the machine.

FAILURES ARE CLASSIFIED, NOT JUST CAUGHT.
A dropped connection deserves a retry. An address that does not exist
does not - resending three times to a mailbox that was never there
produces three identical failures and delays every message behind it.
classify_failure() draws that line, and it is the difference between a
queue that drains and one that grinds.
"""

import re
import smtplib
import ssl
from dataclasses import dataclass
from email.message import EmailMessage as MimeMessage
from email.utils import formatdate, make_msgid
from pathlib import Path
from typing import Optional

from app.config import PROJECT_ROOT, settings


@dataclass
class SendOutcome:
    """What happened to one dispatch attempt."""

    ok: bool
    error: Optional[str] = None
    retryable: bool = False


_TEMPORARY_CODE_RE = re.compile(r"\b4\d\d\b")


def classify_failure(exc: Exception) -> SendOutcome:
    """Decides whether a failed send is worth retrying."""
    if isinstance(exc, (smtplib.SMTPServerDisconnected, smtplib.SMTPConnectError)):
        return SendOutcome(False, f"Could not reach the mail server: {exc}", True)

    if isinstance(exc, (TimeoutError, OSError)) and not isinstance(
        exc, smtplib.SMTPException
    ):
        return SendOutcome(False, f"Network error reaching the mail server: {exc}", True)

    if isinstance(exc, smtplib.SMTPRecipientsRefused):
        return SendOutcome(False, f"Recipient refused: {exc.recipients}", False)

    if isinstance(exc, smtplib.SMTPSenderRefused):
        return SendOutcome(False, f"Sender address refused: {exc}", False)

    if isinstance(exc, smtplib.SMTPAuthenticationError):
        return SendOutcome(False, f"SMTP authentication failed: {exc}", False)

    if isinstance(exc, smtplib.SMTPResponseException):
        message = f"SMTP {exc.smtp_code}: {exc.smtp_error!r}"
        return SendOutcome(False, message, 400 <= exc.smtp_code < 500)

    return SendOutcome(False, f"{type(exc).__name__}: {exc}", True)


def build_mime(
    to_email: str, to_name: Optional[str], subject: str, body: str
) -> MimeMessage:
    """Builds one plain-text message."""
    message = MimeMessage()
    message["From"] = settings.EMAIL_FROM
    message["To"] = f"{to_name} <{to_email}>" if to_name else to_email
    message["Subject"] = subject
    message["Date"] = formatdate(localtime=True)
    message["Message-ID"] = make_msgid()
    message.set_content(body)
    return message


class ConsoleBackend:
    """Writes the message to disk instead of sending it."""

    def __init__(self, outbox: Optional[Path] = None):
        self.outbox = outbox or (PROJECT_ROOT / "var" / "outbox")

    def send(
        self, to_email: str, to_name: Optional[str], subject: str, body: str
    ) -> SendOutcome:
        try:
            self.outbox.mkdir(parents=True, exist_ok=True)
            message = build_mime(to_email, to_name, subject, body)
            safe_id = re.sub(r"[^A-Za-z0-9._-]", "_", message["Message-ID"])[:80]
            path = self.outbox / f"{safe_id}.eml"
            path.write_text(message.as_string(), encoding="utf-8")
            return SendOutcome(True)
        except Exception as exc:  # noqa: BLE001 - reported, never raised
            return SendOutcome(False, f"Could not write to the outbox: {exc}", True)


class SmtpBackend:
    """The real thing."""

    def __init__(self, timeout: int = 20):
        self.timeout = timeout

    def send(
        self, to_email: str, to_name: Optional[str], subject: str, body: str
    ) -> SendOutcome:
        message = build_mime(to_email, to_name, subject, body)

        try:
            if settings.SMTP_PORT == 465:
                context = ssl.create_default_context()
                with smtplib.SMTP_SSL(
                    settings.SMTP_HOST,
                    settings.SMTP_PORT,
                    timeout=self.timeout,
                    context=context,
                ) as server:
                    self._authenticate(server)
                    server.send_message(message)
            else:
                with smtplib.SMTP(
                    settings.SMTP_HOST, settings.SMTP_PORT, timeout=self.timeout
                ) as server:
                    server.starttls(context=ssl.create_default_context())
                    self._authenticate(server)
                    server.send_message(message)

            return SendOutcome(True)
        except Exception as exc:  # noqa: BLE001 - classified, never raised
            return classify_failure(exc)

    @staticmethod
    def _authenticate(server: smtplib.SMTP) -> None:
        """Skips login when no credentials are configured."""
        if settings.SMTP_USERNAME:
            server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)


def get_email_backend():
    """
    Chooses the backend from EMAIL_BACKEND, then ENVIRONMENT.

    EMAIL_BACKEND is checked FIRST and ENVIRONMENT second, so an existing
    deployment that only sets ENVIRONMENT=production keeps sending real
    mail with no config change. The new key exists because the old rule
    made "prove SMTP works" and "declare this machine a production
    system" the same action, and they are not the same action.

    ANYTHING UNRECOGNISED FALLS BACK TO CONSOLE. The failure mode of
    guessing wrong in one direction is a developer wondering why no mail
    arrived. In the other direction it is a seeded database of
    realistic-looking student addresses being emailed for real. Those
    are not symmetric, so the ambiguous case resolves to the safe one.
    """
    choice = (settings.EMAIL_BACKEND or "").strip().lower()
    if choice == "smtp":
        return SmtpBackend()
    if choice == "console":
        return ConsoleBackend()
    if (settings.ENVIRONMENT or "").strip().lower() == "production":
        return SmtpBackend()
    return ConsoleBackend()
