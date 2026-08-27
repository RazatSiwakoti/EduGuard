"""
EmailMessage - the outbox AND the log, in one table (Phase 7.8).

WHY ONE TABLE.
A queued message and a sent message are the same message at different
points in its life. Two tables would mean copying a row between them at
the exact moment a send succeeds - and that copy is precisely where a
crash loses a record of an email that already went out.

WHY A ROW EXISTS BEFORE THE EMAIL IS SENT.
SMTP is a blocking network call, roughly 0.3-2 seconds each. Forty
alerts inside one HTTP request is a request that times out, and if it
dies halfway there are eighteen delivered emails and no record of any
of them. So: write the row (fast, transactional), then dispatch
(slow, network, retryable), then record the outcome. The counters on
the Alerts page are only trustworthy because of that ordering.

WHY subject AND body ARE STORED HERE, NOT JUST A TEMPLATE ID.
Templates are editable. If the log rendered from a template at read
time, a lecturer rewriting their template next month would silently
rewrite the history of what was actually sent to a student two months
ago. The rendered text is captured at queue time and never touched
again - the same lesson as verdict reviews and assessment events.
template_name is captured as a plain string for the same reason: the
log has to survive the template being deleted.

STATUS IS "sent", NOT "delivered".
SMTP accepting a message means the SERVER took it, not that a human
received it. Bounces arrive later and asynchronously, and catching them
needs inbound mail handling this project does not have. Calling this
"delivered" would claim something the system cannot know.
"""

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.models.base import Base


class EmailMessage(Base):
    __tablename__ = "email_messages"

    id = Column(Integer, primary_key=True, index=True)

    # "student_alert" | "lecturer_summary".
    # Summaries share this table so one log answers "what did this system
    # send" completely, rather than splitting the answer across two
    # places a reader has to know to check.
    kind = Column(String, nullable=False, default="student_alert", index=True)

    # NULL on a lecturer summary, which is about a cohort, not a student.
    student_id = Column(Integer, ForeignKey("students.id"), nullable=True, index=True)
    unit_id = Column(Integer, ForeignKey("units.id"), nullable=True, index=True)

    # The lecturer this message belongs to - the recipient of a summary,
    # or the owner of the unit for a student alert. Every query on this
    # table is tenant-scoped through it.
    lecturer_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # CAPTURED AT QUEUE TIME, not read from the student at send time. A
    # student who changes their address should not retroactively change
    # who the log says was contacted.
    recipient_email = Column(String, nullable=False)
    recipient_name = Column(String, nullable=True)

    subject = Column(String, nullable=False)
    body = Column(Text, nullable=False)

    # SET NULL rather than cascade: deleting a template must not delete
    # the record of emails sent with it.
    template_id = Column(
        Integer, ForeignKey("email_templates.id", ondelete="SET NULL"), nullable=True
    )
    # Survives that deletion, so the log's Template column never blanks.
    template_name = Column(String, nullable=True)

    # The tier that justified this alert, and the verdict that produced
    # it. If a student ever asks why they were emailed, this is the
    # answer - traceable to two engine scores and their explanations.
    risk_tier = Column(String, nullable=True)
    verdict_id = Column(Integer, ForeignKey("final_verdicts.id"), nullable=True)

    # "automatic" (weekly sweep) | "manual" (a lecturer pressed send).
    trigger = Column(String, nullable=False, default="manual", index=True)

    # "queued" | "sent" | "failed"
    status = Column(String, nullable=False, default="queued", index=True)
    # The SMTP error, kept verbatim. A lecturer looking at a red row
    # needs to know whether the address was wrong or the server was down.
    error = Column(Text, nullable=True)

    # Retries are for TRANSIENT failures only - see classify_failure().
    # A hard bounce is never retried; resending to an address that does
    # not exist just produces three identical failures.
    attempts = Column(Integer, nullable=False, default=0)

    queued_at = Column(DateTime, server_default=func.now(), index=True)
    sent_at = Column(DateTime, nullable=True)

    # NULL for an automatic send - nobody pressed anything.
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    student = relationship("Student")
    unit = relationship("Unit")
    lecturer = relationship("User", foreign_keys=[lecturer_id])
    creator = relationship("User", foreign_keys=[created_by])
    template = relationship("EmailTemplate")
