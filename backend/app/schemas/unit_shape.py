"""
Schemas for the admin unit-composition API (section T2).

Kept out of `schemas/criteria.py` because this is a different object.
That file describes ONE Criteria row as the lecturer's per-item endpoints
see it; this one describes a whole unit's shape as the coordinator's
setup form sees it - which is the level every composition rule is stated
at (three items, one quiz cap, one 100% budget).

WHAT THE CLIENT DOES NOT SEND
-----------------------------
`threshold`, `weight` and `max_score` are all absent from the request.

  * `threshold` is the lecturer's pass bar (section T4). A setup form
    that posted it back would reset it to 50 every time a coordinator
    fixed a typo, silently undoing a lecturer's setting.
  * `weight` and `max_score` are DERIVED from `percentage`, and the
    derivation is not the same for both categories - see
    `unit_composition.assessment_row_values` / `tutorial_row_values`.
    Letting a client send them is letting a client get that wrong.

The tutorial has no percentage field for the same reason: it is fixed at
10%, so it is a boolean, not a number.
"""

from typing import Optional

from pydantic import BaseModel, Field

from app.models.enums import AssessmentKind


class AssessmentItemIn(BaseModel):
    """One assessment as the setup form submits it."""

    #: Present when the form is editing a row that already exists, so a
    #: rename or a re-order keeps that row's AssessmentEvent history
    #: instead of soft-deleting it and starting a new one. Absent for a
    #: newly added item. An id that does not belong to this unit is
    #: ignored rather than rejected - the row is then treated as new,
    #: which is the safe reading of a stale form.
    id: Optional[int] = None

    name: str = Field(..., min_length=1, max_length=255)
    kind: AssessmentKind

    #: Share of the unit. `gt=0` and `le=100` are the cheap bounds; the
    #: real rules (quiz cap, item count, 100% budget) are checked in
    #: `unit_composition.validate_composition` so they are enforced for
    #: every caller and not just for ones that go through pydantic.
    percentage: float = Field(..., gt=0, le=100)


class UnitShapeIn(BaseModel):
    """
    A whole unit shape. Both fields are required: an absent
    `tutorials_enabled` would have to default to something, and either
    default silently adds or silently removes 10% of the unit.
    """

    assessments: list[AssessmentItemIn] = Field(default_factory=list)
    tutorials_enabled: bool


class CriterionShapeOut(BaseModel):
    id: Optional[int] = None
    name: str
    kind: Optional[str] = None
    category: Optional[str] = None
    sequence_number: Optional[int] = None
    #: Share of the unit, reconstructed from `weight`. NOT from
    #: `max_score` - that is the share only for assessments, and is the
    #: 0-100 scale for the tutorial.
    percentage: Optional[float] = None
    max_score: Optional[float] = None
    weight: Optional[float] = None
    threshold: Optional[float] = None
    #: Derived at read time, never stored: max_score * threshold / 100.
    pass_mark: Optional[float] = None
    enabled: bool = True


class ShapeLimitsOut(BaseModel):
    """
    The numbers the form validates against, sent by the server rather
    than hard-coded in the client. Two copies of a rule is two places for
    it to be wrong, and the client's copy is the one nobody re-checks.
    """

    max_assessments: int
    quiz_max_percentage: float
    tutorial_percentage: float
    max_total_percentage: float


class UnitShapeOut(BaseModel):
    unit_id: int
    unit_code: str
    unit_name: str
    #: What T3's "not configured" badge reads. False until the unit has
    #: at least one assessment or tutorials switched on - the two seeded
    #: rows do not count, or the badge would never appear.
    configured: bool
    tutorials_enabled: bool
    tutorial: Optional[CriterionShapeOut] = None
    assessments: list[CriterionShapeOut] = []
    assessment_total_percentage: float = 0.0
    total_percentage: float = 0.0
    remaining_percentage: float = 0.0
    #: Attendance and Moodle. Stated so the form can say they are
    #: automatic, never editable through this endpoint.
    automatic: list[CriterionShapeOut] = []
    limits: ShapeLimitsOut
    lock: dict


# ---------------------------------------------------------------------
# The lecturer's threshold bar (section T4)
# ---------------------------------------------------------------------

class ThresholdGroupOut(BaseModel):
    """
    One slider. There is one per adjustable CATEGORY, not one per item -
    a lecturer decides what "passing an assessment" means for the unit,
    not for Quiz 1 specifically.

    `value` is None when the category's rows disagree (`mixed`). The
    form must say so rather than render the first row's number: D1's
    per-item endpoint can leave two assessments on different bars, and a
    slider that showed 50 for a unit whose second assessment sits at 46
    would flatten the 46 on its first drag without ever displaying it.
    """

    category: str
    #: The lowest a lecturer may go, read from D1's own floors dict.
    floor: Optional[float] = None
    #: The ceiling and the starting point. Never raised above.
    default: float
    #: How many enabled criteria this slider writes to. Zero means the
    #: category is absent from the unit and no slider is shown.
    applies_to: int
    value: Optional[float] = None
    mixed: bool = False
    values: list[float] = []
    adjustable: bool = False
    item_names: list[str] = []


class LecturerUnitShapeOut(UnitShapeOut):
    """
    The coordinator's shape plus the lecturer's bars, in one response.

    Deliberately an extension of `UnitShapeOut` rather than a parallel
    type: the lecturer is reading the SAME rows the setup form writes,
    and two differently-shaped reads of one table is how two screens end
    up disagreeing about what a unit is worth.
    """

    thresholds: dict[str, ThresholdGroupOut] = {}


class ThresholdUpdateIn(BaseModel):
    """
    A pass-bar change for one or both adjustable categories.

    `extra="forbid"` is doing real work: it is what makes
    `{"attendance": 10}` a 422 rather than a silently ignored field. A
    lecturer who believes they moved the attendance bar and did not is
    exactly the outcome D1's guards exist to prevent.

    Both fields optional so one slider can save without echoing the
    other; a payload that changes nothing is accepted and writes
    nothing.

    NOTE what is NOT here: name, weight, max_score, kind, percentage.
    The shape belongs to the coordinator's admin PUT (section T2), and
    this endpoint is the lecturer's entire write surface on a unit.
    """

    model_config = {"extra": "forbid"}

    assessment: Optional[float] = Field(None, ge=0, le=100)
    weekly_tut: Optional[float] = Field(None, ge=0, le=100)