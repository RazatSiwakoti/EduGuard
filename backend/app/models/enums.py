from enum import Enum


class UserRole(str, Enum):
    SUPER_ADMIN = "super_admin"
    ADMIN = "admin"
    LECTURER = "lecturer"


class EventSource(str, Enum):
    """
    Where an AssessmentEvent came from - lets ingestion distinguish a
    bulk CSV/Excel upload from a single manual entry, for audit purposes.
    """
    BULK_UPLOAD = "bulk_upload"
    MANUAL = "manual"


class CriteriaCategory(str, Enum):
    """
    What a Criteria structurally IS, not just its display name - lets
    the risk engine reliably find "the Attendance one" or "assessment
    slot 2" without guessing from free-text names.
    """
    ATTENDANCE = "attendance"
    WEEKLY_TUT = "weekly_tut"
    ASSESSMENT = "assessment"
    MOODLE = "moodle"


class AssessmentKind(str, Enum):
    """
    What KIND of assessment a criterion is (section T2).

    Deliberately a SECOND field rather than two more CriteriaCategory
    members. `category` is the ML contract: `ml_score_service`,
    `rule_score_service`, `report_service` and the training notebook all
    branch on its four values, and splitting ASSESSMENT into QUIZ and
    ASSIGNMENT would have silently dropped every assessment out of every
    one of those branches. `kind` is a label the coordinator sets and the
    composition rules read; nothing in the scoring path looks at it.

    NULL for attendance, Moodle and weekly tutorials - they have no kind.
    """
    QUIZ = "quiz"
    ASSIGNMENT = "assignment"