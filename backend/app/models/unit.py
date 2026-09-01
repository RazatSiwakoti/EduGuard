"""
Unit model — represents one specific teaching offering of an academic
subject (e.g. ICT729, Year 2026, Semester 1).

start_date supports Week 8 checkpoint calculations later —
needed to determine which academic week a given AssessmentEvent.date
falls into.

year + teaching_period identify WHICH offering this is. unit_code alone
is no longer unique, since the same subject is taught every semester —
uniqueness is enforced on the (unit_code, year, teaching_period,
class_code) combination instead.

class_code is the fourth part because KOI runs the same subject more
than once in a trimester: ICT730LA1 and ICT730LA2 are two classes with
different lecturers, different students and different results. It is a
NON-NULL column with "" meaning "no class split" — see
app/services/class_code.py for why an empty string rather than NULL is
load-bearing here.

level ("bachelor"/"master") is informational only, not enforced at the
database level - real enrolment can have messy edge cases (bridging
students, dual-pathway students) that a hard constraint would wrongly
block. Useful for reporting and the ML pipeline, not a hard rule.
"""

from sqlalchemy import (
    Column, Integer, String, Date, DateTime, Boolean, ForeignKey, UniqueConstraint,
)
from sqlalchemy.sql import true
from sqlalchemy.orm import relationship
from app.models.base import Base
from app.services import class_code as class_code_rules


class Unit(Base):
    __tablename__ = "units"
    __table_args__ = (
        # class_code is INSIDE the constraint and is never NULL. A
        # nullable column in a UNIQUE constraint stops constraining the
        # moment it is NULL, because SQL does not treat NULL as equal to
        # itself - so two classless ICT730 rows in one trimester would
        # both be accepted, which is the exact duplicate this constraint
        # exists to refuse.
        UniqueConstraint(
            "unit_code", "year", "teaching_period", "class_code",
            name="uq_unit_code_year_period_class",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    unit_code = Column(String, nullable=False)
    unit_name = Column(String, nullable=False)

    year = Column(Integer, nullable=True)
    teaching_period = Column(String, nullable=True)

    # "LA1" | "LA2" | "NCLA" | "" (no class split). NEVER NULL - see the
    # note on __table_args__ and app/services/class_code.py.
    #
    # Stored as one composed string rather than a type column plus a
    # number column, because the constraint above has to compare it and
    # two nullable columns cannot be compared reliably. The form's two
    # fields are composed on the way in and split on the way out.
    class_code = Column(
        String(8), nullable=False, default="", server_default="",
    )

    # Informational only - see docstring above. Plain string, not an
    # Enum, since it's not enforced and keeping it simple avoids a
    # migration later if a third level (e.g. "diploma") ever appears.
    level = Column(String, nullable=True)

    start_date = Column(Date, nullable=True)

    lecturer_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    is_active = Column(Boolean, nullable=False, default=True, server_default=true())
    status = Column(String, nullable=False, default="UNASSIGNED")

    # --- criteria shape lifecycle (section T1) -------------------------
    # When this unit's criteria SHAPE last changed. Any FinalVerdict
    # older than this was computed against weights that no longer exist,
    # which is how staleness is derived - there is deliberately no
    # `is_stale` flag to keep in sync.
    #
    # NULL means "no shape change has ever been recorded", not "changed
    # at the epoch". Every unit that predates this column is NULL and
    # therefore has nothing stale, which is correct: back-filling it
    # would have declared every historical result suspect on the day the
    # feature shipped.
    #
    # A rename does NOT bump this. A label is not a rule.
    criteria_updated_at = Column(DateTime, nullable=True)

    # A one-shot admin unlock. Set by POST /units/{id}/criteria/unlock,
    # cleared by the next successful shape change. Stored as a timestamp
    # rather than a boolean so the window is auditable after the fact -
    # "who opened this unit and when" is the question anyone asks after a
    # cohort's results move.
    criteria_unlocked_at = Column(DateTime, nullable=True)
    criteria_unlocked_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    # `foreign_keys` is now REQUIRED on both sides: `criteria_unlocked_by`
    # is a second FK to users.id, so SQLAlchemy can no longer infer which
    # column joins a Unit to its lecturer and raises AmbiguousForeignKeys
    # at mapper-configuration time - i.e. the app fails to start, loudly.
    lecturer = relationship(
        "User", back_populates="units", foreign_keys=[lecturer_id]
    )
    enrollments = relationship("Enrollment", back_populates="unit")
    criteria = relationship("Criteria", back_populates="unit")
    rule_versions = relationship("RuleVersion", back_populates="unit")
    assessment_events = relationship("AssessmentEvent", back_populates="unit")
    risk_scores = relationship("RiskScore", back_populates="unit")
    ingestion_batches = relationship("IngestionBatch", back_populates="unit")
    
    @property
    def class_type(self) -> str | None:
        """"LA" | "NCLA" | None. Derived, never stored separately."""
        return class_code_rules.split(self.class_code)[0]

    @property
    def class_number(self) -> int | None:
        """The number on an LA class; None for NCLA and for no class."""
        return class_code_rules.split(self.class_code)[1]

    @property
    def full_code(self) -> str:
        """
        The identity a human uses: "ICT730LA1", or "ICT730" if this unit
        has no class split.

        Everywhere two classes of one subject must be told apart -
        the unit card, the dashboard filter, the report header, the PDF
        filename, the typed unlock confirmation - prints THIS, not
        `unit_code`. `unit_code` remains the SUBJECT, which is what makes
        grouping several classes under one subject possible at all.
        """
        return class_code_rules.full_code(self.unit_code, self.class_code)

    @property
    def enrolled_count(self) -> int:
        """
        Computed live from the enrollments relationship - never stored,
        so there's nothing to keep in sync. Whether a student arrives via
        bulk upload or manual entry (both go through
        ingestion_service.resolve_or_create_enrollment), this reflects it
        immediately without any extra update step anywhere.
        """
        return len(self.enrollments)