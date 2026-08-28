"""
The student acknowledgment portal - the ONLY unauthenticated page in
this API (Phase Email).

CONTRIBUTED BY AASH (branch `backend-aash-test`,
`backend_aash_test/alerts_routes.py`). The feature, the flow and the
receipt page are his. What changed in the adaptation is set out below,
because each change closes something that would have been a real defect
in this codebase.

WHY THIS ROUTER IS PUBLIC.
Students do not have accounts in EduGuard. There is nothing to log in
to, so a link in an email is the only way a student can ever tell the
system anything. Every other router in this project sits behind
`require_teaching_role()`; this one deliberately does not, and the token
in the URL is what stands in for authentication.

THREE CHANGES FROM THE ORIGINAL, AND WHY.

  1. THE URL CARRIES A TOKEN, NOT THE ROW ID.
     The original endpoint was `/alerts/acknowledge/{log_id}` against an
     auto-increment primary key. Anyone holding one valid link could
     read every other student's notice by typing a different number, and
     this page prints a name and a unit code. `ack_token` is 256 bits
     from `secrets.token_urlsafe`, so the link is a capability rather
     than a coordinate: holding it is the proof, and it exists in one
     mailbox.

  2. GET DOES NOT WRITE. THE POST DOES.
     The original recorded the acknowledgment on the GET. Mail providers
     - Gmail, Outlook, and every corporate link scanner - fetch the URLs
     inside a message before a human ever sees it. On a GET-writes
     design, that scanner acknowledges the notice on the student's
     behalf, and the one number in this system that was supposed to come
     from a human hand becomes a record of a robot. The GET renders a
     button; pressing it is what writes.

  3. THE PAGE LEAKS NOTHING SIDEWAYS, AND LINKS NOWHERE.
     `Referrer-Policy: no-referrer`, so the token is never handed to
     another origin in a Referer header. `X-Robots-Tag: noindex`,
     because a forwarded link that reaches a crawler should not become
     a search result with a student's name in it. `Cache-Control:
     no-store`, so a shared or library machine does not keep the
     receipt in its back button.

     The original receipt ended with an "Open EduGuard Portal" button.
     Rendering this page and looking at it is what killed that link: a
     student has no account here, so the button sends the one person it
     was built for to a login screen they cannot pass. Deleting it also
     removed the only place the token could have leaked outward - a
     better outcome than the `rel="noreferrer"` that was mitigating it.

WHAT IS DELIBERATELY NOT ON THIS PAGE.
No risk tier, no scores, no message body. The student already has all of
that in the email; repeating it here means a page reachable without
logging in that states an academic judgement about a named person.
Name and unit code are shown, and only so the reader can tell the notice
was meant for them.
"""

from datetime import datetime, timezone
from html import escape
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, Path
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.email_message import EmailMessage
from app.models.unit import Unit
from app.services import alert_service as alerts

# No `dependencies=[...]`. That absence is the whole point of the file.
router = APIRouter(prefix="/alerts/acknowledge", tags=["Student - Acknowledgment"])

_SAFE_HEADERS = {
    "Cache-Control": "no-store",
    "Referrer-Policy": "no-referrer",
    "X-Robots-Tag": "noindex, nofollow",
}


def _local(moment: datetime | None) -> str:
    """Formats a stored UTC timestamp in the institution's own timezone."""
    if moment is None:
        return ""
    aware = moment if moment.tzinfo else moment.replace(tzinfo=timezone.utc)
    try:
        local = aware.astimezone(ZoneInfo(settings.SCHEDULER_TIMEZONE))
    except Exception:  # noqa: BLE001 - an unknown tz must not 500 a receipt
        local = aware
    # %-I is POSIX; this API is not deployed on Windows, and a
    # zero-padded "04:39 PM" would still be readable if it ever were.
    return f"{local.strftime('%A, %d %B %Y at %I:%M %p (%Z)').replace(' 0', ' ').replace(' at 0', ' at ')}"


def _page(title: str, tone: str, heading: str, body_html: str, status_code: int = 200) -> HTMLResponse:
    """One shell for all four states, so they cannot drift apart visually."""
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex, nofollow">
<title>{escape(title)}</title>
<style>
  :root {{ color-scheme: light; }}
  body {{ margin: 0; padding: 32px 16px; background: #f5f5f4;
         font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
         color: #1c1917; line-height: 1.6; }}
  .card {{ max-width: 560px; margin: 0 auto; background: #fff; border: 1px solid #e7e5e4;
          border-radius: 16px; overflow: hidden; }}
  .bar {{ height: 4px; background: {tone}; }}
  .inner {{ padding: 28px 30px; }}
  h1 {{ margin: 0 0 6px; font-size: 20px; }}
  p {{ margin: 0 0 14px; font-size: 15px; }}
  .muted {{ color: #78716c; font-size: 13px; }}
  .meta {{ background: #fafaf9; border: 1px solid #e7e5e4; border-radius: 10px;
          padding: 14px 16px; margin: 18px 0; font-size: 14px; }}
  .meta div + div {{ margin-top: 6px; }}
  button {{ font: inherit; font-weight: 600; background: #15803d; color: #fff; border: 0;
           border-radius: 10px; padding: 12px 22px; cursor: pointer; }}
  button:hover {{ background: #166534; }}
  a {{ color: #1d4ed8; }}
  footer {{ border-top: 1px solid #e7e5e4; padding: 12px 30px; background: #fafaf9;
           font-size: 12px; color: #a8a29e; text-align: center; }}
</style>
</head>
<body>
  <div class="card">
    <div class="bar"></div>
    <div class="inner">
      <h1>{escape(heading)}</h1>
      {body_html}
    </div>
    <footer>EduGuard &middot; automated student support notification</footer>
  </div>
</body>
</html>"""
    return HTMLResponse(content=html, status_code=status_code, headers=_SAFE_HEADERS)


def _not_found() -> HTMLResponse:
    """
    Identical for an expired link, a mistyped one and a guessed one.

    Distinguishing them would turn this page into an oracle that confirms
    whether a token exists, which is the one thing an attacker holding a
    guess actually wants to learn.
    """
    return _page(
        "Link not recognised",
        "#a8a29e",
        "This link is not recognised",
        '<p>It may have been mistyped, or only part of it was copied out of the email.</p>'
        '<p class="muted">Try opening the link directly from your email rather than pasting it. '
        'If it still does not work, reply to the message and your lecturer can confirm it another way.</p>',
        status_code=404,
    )


def _details(db: Session, message: EmailMessage) -> str:
    unit = db.get(Unit, message.unit_id) if message.unit_id else None
    rows = [f"<div><strong>{escape(message.recipient_name or 'Student')}</strong></div>"]
    if unit is not None:
        rows.append(f"<div>{escape(unit.unit_code)} &middot; {escape(unit.unit_name or '')}</div>")
    rows.append(f'<div class="muted">Reference #{message.id}</div>')
    return '<div class="meta">' + "".join(rows) + "</div>"


@router.get("/{token}", response_class=HTMLResponse)
def show_acknowledgement(token: str = Path(..., min_length=8, max_length=64), db: Session = Depends(get_db)):
    """Renders the confirm button, or the receipt if it is already done."""
    message = db.query(EmailMessage).filter(EmailMessage.ack_token == token).first()
    if message is None or message.kind != "student_alert":
        return _not_found()

    if message.acknowledged_at is not None:
        return _receipt(db, message)

    return _page(
        "Confirm you received this notice",
        "#0d9488",
        "Confirm you received this notice",
        _details(db, message)
        + "<p>Pressing the button below records the date and time you confirmed receipt. "
          "That is all it records.</p>"
          '<p class="muted">It is a receipt, not an agreement with anything in the message, '
          "and it has no effect on your marks.</p>"
          f'<form method="post" action="{escape(str(router.prefix))}/{escape(token)}">'
          '<button type="submit">I confirm I received this notice</button>'
          "</form>",
    )


@router.post("/{token}", response_class=HTMLResponse)
def record_acknowledgement(token: str = Path(..., min_length=8, max_length=64), db: Session = Depends(get_db)):
    """The only write on this router."""
    message = alerts.acknowledge(db, token)
    if message is None or message.kind != "student_alert":
        return _not_found()
    return _receipt(db, message)


def _receipt(db: Session, message: EmailMessage) -> HTMLResponse:
    return _page(
        "Receipt confirmed",
        "#16a34a",
        "Thank you - this is confirmed",
        _details(db, message)
        + f"<p>Recorded on <strong>{escape(_local(message.acknowledged_at))}</strong>.</p>"
        + "<p>Nothing further is needed. If you want to talk about the unit, "
          "replying to that email reaches your lecturer directly.</p>"
        + '<p class="muted">You can close this page.</p>',
    )
