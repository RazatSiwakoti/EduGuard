"""
Template rendering and the system default templates (Phase 7.8).

WHY NOT JINJA2
--------------
This module implements plain {{key}} substitution against a fixed
whitelist, and refuses anything else. That is a deliberate choice over
an actual template engine:

  * A lecturer-editable Jinja template is a server-side template
    injection surface. A template containing Python attribute traversal
    could become a remote code execution path, and "only lecturers can
    edit it" is not a security boundary.
  * A typo in a Jinja tag raises at render time. With substitution, an
    unrecognised placeholder is caught when the template is SAVED, so a
    broken template can never reach the point of sending.

PLAIN TEXT, NOT HTML
--------------------
Alerts are plain text. It renders identically in every mail client, it
needs no styling to say "your attendance is 35%", and it removes
HTML injection from a lecturer-editable field entirely.
"""

import re
from typing import Optional

# ---------------------------------------------------------------------
# Placeholders
# ---------------------------------------------------------------------

# Every placeholder a template may use, with the description shown in
# the editor. A key not in here is rejected at save time.
#
# Deliberately absent: anything the ML model uses as a passive
# demographic feature (gender, age). Those exist to help the model
# generalise; putting them in an email a student receives would be
# indefensible, and there is no wording where "you are 19" belongs in a
# welfare message.
PLACEHOLDERS: dict[str, str] = {
    "student_name": "The student's full name",
    "student_number": "Their student ID, e.g. KOI-2025-015",
    "unit_code": "Unit code, e.g. BSYS401",
    "unit_name": "Full unit name",
    "lecturer_name": "The unit's lecturer",
    "risk_level": "Their risk tier in plain words, e.g. High Risk",
    "attendance_pct": "Attendance percentage, or 'not recorded'",
    "tutorial_pct": "Weekly tutorial completion, or 'not recorded'",
    "assessments_marked": "e.g. '1 of 3', or 'not recorded'",
    "checkpoint_week": "Which checkpoint this reflects, e.g. 8",
    "acknowledge_url": "The student's one-time link confirming they received this",
}

_PLACEHOLDER_RE = re.compile(r"\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\}\}")
_ANY_BRACES_RE = re.compile(r"\{\{(.*?)\}\}", re.DOTALL)


def find_placeholders(text: str) -> list[str]:
    """Every VALID placeholder key used in a string, in order."""
    return _PLACEHOLDER_RE.findall(text or "")


def unknown_placeholders(*texts: str) -> list[str]:
    """Every {{ ... }} construct that this system cannot fill."""
    seen: list[str] = []
    for text in texts:
        for raw in _ANY_BRACES_RE.findall(text or ""):
            key = raw.strip()
            if key in PLACEHOLDERS:
                continue
            if key and key not in seen:
                seen.append(key)
    return seen


def render(text: str, context: dict[str, object]) -> str:
    """Substitutes whitelisted placeholders, using a visible fallback."""
    def substitute(match: re.Match[str]) -> str:
        key = match.group(1)
        if key not in PLACEHOLDERS:
            return match.group(0)
        value = context.get(key)
        if value is None or value == "":
            return "not recorded"
        return str(value)

    return _PLACEHOLDER_RE.sub(substitute, text or "")


# ---------------------------------------------------------------------
# System default templates
# ---------------------------------------------------------------------

SYSTEM_TEMPLATES: list[dict[str, str]] = [
    {
        "name": "High risk - default",
        "risk_tier": "high_risk",
        "subject": "Checking in about {{unit_code}}",
        "body": (
            "Hi {{student_name}},\n\n"
            "I'm getting in touch about {{unit_code}} ({{unit_name}}). Looking at "
            "where things stand at week {{checkpoint_week}}, a few things stood out:\n\n"
            "  Attendance: {{attendance_pct}}\n"
            "  Tutorial submissions: {{tutorial_pct}}\n"
            "  Assessments marked: {{assessments_marked}}\n\n"
            "None of this is a penalty and it isn't on your record - it's just the "
            "point where it's worth having a conversation. If something has been "
            "getting in the way, there is usually more that can be done about it "
            "now than later in the semester.\n\n"
            "Please reply to this email and we'll find a time to talk. If you'd "
            "rather speak to someone else, student support can help too.\n\n"
            "{{lecturer_name}}\n"
            "{{unit_code}}"
        ),
    },
    {
        "name": "At risk - default",
        "risk_tier": "low_risk",
        "subject": "A quick note about {{unit_code}}",
        "body": (
            "Hi {{student_name}},\n\n"
            "A quick check-in about {{unit_code}}. At week {{checkpoint_week}} a "
            "couple of things are drifting a little:\n\n"
            "  Attendance: {{attendance_pct}}\n"
            "  Tutorial submissions: {{tutorial_pct}}\n"
            "  Assessments marked: {{assessments_marked}}\n\n"
            "Nothing here is serious yet, which is exactly why it's worth a "
            "message now rather than in a month. If you're on top of it, ignore "
            "this. If you're not, reply and let me know what's going on.\n\n"
            "{{lecturer_name}}\n"
            "{{unit_code}}"
        ),
    },
    {
        "name": "Safe - default",
        "risk_tier": "safe",
        "subject": "How's {{unit_code}} going?",
        "body": (
            "Hi {{student_name}},\n\n"
            "Nothing's wrong - just checking in on {{unit_code}}. Your attendance "
            "is at {{attendance_pct}} and your tutorial submissions at "
            "{{tutorial_pct}}, which is where they should be.\n\n"
            "If anything comes up this semester, get in touch early.\n\n"
            "{{lecturer_name}}\n"
            "{{unit_code}}"
        ),
    },
]


# ---------------------------------------------------------------------
# Acknowledgment footer
#
# Design contributed by Aash (branch backend-aash-test,
# backend_aash_test/email_service.py), rebuilt as plain text.
#
# WHY IT IS APPENDED RATHER THAN LIVING IN THE TEMPLATE. {{acknowledge_url}}
# is a placeholder a lecturer MAY use, so a lecturer who wants the link
# mid-message can put it there. But a lecturer who writes their own
# template and never types it would produce an alert with no way to
# acknowledge - and the feature would fail silently, on exactly the
# messages someone cared enough to customise. So: use the placeholder if
# it is present, append this if it is not. The link is a property of the
# message, not of the wording.
#
# WHY THE WORDING MATTERS. "Acknowledge" reads to a student under
# pressure like agreeing they are failing. Saying plainly that it is a
# receipt, that it is not an agreement, and that it does not touch their
# marks is the difference between a link that gets clicked and a link
# that gets ignored by the students who most need to be reached.
ACK_MARKER = "/alerts/acknowledge/"

ACK_FOOTER = (
    "\n\n"
    "----------------------------------------\n"
    "Please confirm you received this message:\n"
    "{url}\n\n"
    "This records the date and time only. It is a receipt, not an\n"
    "agreement with anything above, and it does not affect your marks."
)


def ensure_acknowledgement(body: str, url: str) -> str:
    """Appends the receipt footer unless the body already links to one."""
    text = body or ""
    if ACK_MARKER in text:
        return text
    return text + ACK_FOOTER.format(url=url)


def default_template_for(tier: str) -> Optional[dict[str, str]]:
    """The seeded default for one tier, or None if the tier is unknown."""
    for template in SYSTEM_TEMPLATES:
        if template["risk_tier"] == tier:
            return template
    return None
