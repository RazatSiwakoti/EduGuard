"""
The audit log - one row per act that changed the basis of a judgement
about a student.

WHAT BELONGS HERE, AND WHAT DOES NOT.
This table answers one question: *who changed the rules a student was
measured against, when, and from what to what?* Four acts qualify -
moving a pass threshold, unlocking a locked unit shape, replacing that
shape, and overriding an engine verdict. Every one of them changes an
outcome for a named person and every one is done by a human who chose
to do it.

Logins, page views and read requests are deliberately absent. An audit
log that records everything records nothing: the four rows that matter
end up buried under ten thousand that do not, and the first thing anyone
reviewing it does is stop reading. Alert sends are also absent, because
`email_messages` already is their log - a second copy would be a second
version of the truth.

WHY THE ACTOR AND THE UNIT ARE COPIED IN, NOT ONLY REFERENCED.
`actor_email`, `actor_name`, `actor_role` and `unit_code` are stored as
plain strings beside their foreign keys. A deleted lecturer must not
blank the record of what they did - that is precisely the record most
worth keeping, and a log that erases itself when an account is removed
is not an audit log. The same reasoning already governs
`EmailMessage.template_name`.

WHY before AND after ARE JSON TEXT.
A threshold moving from 50 to 45 is not usefully described by the word
"changed". The reader of an audit log is reconstructing a decision they
were not present for, and the two numbers are the decision. JSON rather
than columns because the four actions carry different shapes, and a
table with a nullable column per possible field would be mostly NULL and
still wrong for the fifth action.

WHAT THIS IS NOT.
It is append-only **by convention and by API surface** - nothing in the
application writes an UPDATE or a DELETE against this table, and no
route exposes one. It is NOT tamper-evident: anyone with direct database
access can edit a row and leave no trace. Making it tamper-evident needs
a hash chain over the rows or an append-only store outside this
database, and claiming the property without one would be worse than not
having it. State the limit; do not paper over it.
"""

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.models.base import Base


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id = Column(Integer, primary_key=True, index=True)

    # Server clock, not the caller's. A timestamp an API client can set
    # is a timestamp an API client can lie about.
    occurred_at = Column(DateTime, server_default=func.now(), nullable=False, index=True)

    # A dotted vocabulary - "threshold.changed", "criteria.unlocked".
    # Indexed because the filter every reader reaches for first is
    # "show me only the unlocks".
    action = Column(String, nullable=False, index=True)

    # SET NULL, not CASCADE. Deleting a user must never delete the
    # record of what that user did.
    actor_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    # Captured at write time so the row survives that deletion.
    actor_email = Column(String, nullable=True)
    actor_name = Column(String, nullable=True)
    actor_role = Column(String, nullable=True)

    unit_id = Column(Integer, ForeignKey("units.id", ondelete="SET NULL"), nullable=True, index=True)
    unit_code = Column(String, nullable=True)

    # Set only where the act was about one student - a verdict override.
    # NULL on a threshold change, which is about everyone in the unit.
    student_id = Column(Integer, ForeignKey("students.id", ondelete="SET NULL"), nullable=True, index=True)
    student_name = Column(String, nullable=True)

    # What was acted upon: "criteria" | "unit" | "final_verdict".
    entity_type = Column(String, nullable=True)
    entity_id = Column(Integer, nullable=True)

    # A finished English sentence, written at the call site where the
    # context exists. The UI prints it rather than rebuilding it from
    # the JSON, so the log reads the same in the table, in an export and
    # in a screenshot pasted into an email.
    summary = Column(Text, nullable=False)

    # JSON text. NULL where the act has no meaningful prior state -
    # nothing precedes an unlock.
    before_state = Column(Text, nullable=True)
    after_state = Column(Text, nullable=True)

    # request.client.host, NOT X-Forwarded-For. An unvalidated
    # forwarding header is caller-controlled, so trusting it lets the
    # one field meant to identify the source of an action be set to
    # anything the actor likes. Behind a real reverse proxy this becomes
    # the proxy's address, which is honest; making it the client's needs
    # a configured list of trusted proxies this deployment does not have.
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)

    actor = relationship("User", foreign_keys=[actor_id])
    unit = relationship("Unit")
    student = relationship("Student")