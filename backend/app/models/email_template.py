"""
EmailTemplate - the wording of an alert (Phase 7.8).

SCOPING: lecturer_id NULL means a SYSTEM DEFAULT.
Every install ships with one default per risk tier, seeded by
ensure_system_templates(). That matters for a first run: without them
the very first send would fail with "no template", which is a poor
introduction for anyone opening this project for the first time.

System defaults are READ-ONLY. A lecturer who wants different wording
saves their own template rather than editing the shared one, so one
lecturer cannot silently change what another lecturer's alerts say.

PLACEHOLDERS ARE NOT JINJA, DELIBERATELY.
Bodies use plain {{key}} substitution against a fixed whitelist (see
email_render.py). Letting a lecturer save a real Jinja template would
hand them a server-side template injection surface - {{ ''.__class__ }}
and friends - in a field that exists to hold a sentence of English. It
would also mean a typo in a tag crashes a send instead of rendering.

PLAIN TEXT, NOT HTML. An alert about someone's studies does not need
styling, plain text renders identically in every client, and it removes
HTML injection from a lecturer-editable field entirely.
"""

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.models.base import Base


class EmailTemplate(Base):
    __tablename__ = "email_templates"

    id = Column(Integer, primary_key=True, index=True)

    # NULL = system default, owned by nobody, editable by nobody.
    lecturer_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)

    name = Column(String, nullable=False)

    # Which risk tier this template is written for. A lecturer picks a
    # template when sending, but the sweep needs to choose one on its
    # own, and it chooses by tier.
    risk_tier = Column(String, nullable=False, index=True)

    subject = Column(String, nullable=False)
    body = Column(Text, nullable=False)

    # True only for the seeded defaults. Cheaper and clearer than
    # inferring it from lecturer_id being NULL at every call site.
    is_system = Column(Boolean, nullable=False, default=False)

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    lecturer = relationship("User")
