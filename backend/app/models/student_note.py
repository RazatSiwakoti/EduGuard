"""
StudentNote - one lecturer's free-text notes about one student in one
unit (Phase 7.6b).

WHY THIS IS ITS OWN TABLE, AND NOT A COLUMN ON FinalVerdict
-----------------------------------------------------------
Putting the note on FinalVerdict was the obvious first idea and it is
wrong. FinalVerdict is APPEND-ONLY: every "Run Analysis" inserts a new
row. A note written against verdict #12 would silently vanish from the
card the moment verdict #13 was staged, because every read in this
project takes the latest verdict per (student, unit). A lecturer would
watch their notes disappear and have no idea why.

A note is about the STUDENT, not about one run of the engines. It has
to outlive every re-analysis, so it lives on its own row keyed by
(student_id, unit_id, lecturer_id) and is UPDATED in place. That is a
deliberate exception to the project's append-only rule, and it is
correct here for the same reason the rule exists elsewhere: raw
observations must never be rewritten, but a person's own working notes
are theirs to edit.

Scoped per LECTURER as well as per unit. Two lecturers who both teach a
unit keep separate notes rather than overwriting each other, and a
lecturer's private impressions of a student never leak to a colleague
through a shared row.

Separate from FinalVerdict.review_decision, which records the formal
resolution of an engine disagreement. That stays where it is.
"""

from sqlalchemy import Column, DateTime, ForeignKey, Integer, Text, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.models.base import Base


class StudentNote(Base):
    __tablename__ = "student_notes"

    # One note per lecturer per student per unit. Enforced in the
    # database rather than trusted to the service layer, so a double
    # submit can never leave two rows that disagree about what the
    # lecturer wrote.
    __table_args__ = (
        UniqueConstraint(
            "student_id", "unit_id", "lecturer_id", name="uq_student_note_scope"
        ),
    )

    id = Column(Integer, primary_key=True, index=True)

    student_id = Column(Integer, ForeignKey("students.id"), nullable=False, index=True)
    unit_id = Column(Integer, ForeignKey("units.id"), nullable=False, index=True)
    lecturer_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    body = Column(Text, nullable=False, default="")

    created_at = Column(DateTime, server_default=func.now())
    # Bumped on every save so the card can show "last edited" and a
    # lecturer can tell a stale note from a current one.
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    student = relationship("Student")
    unit = relationship("Unit")
    lecturer = relationship("User")