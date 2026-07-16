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