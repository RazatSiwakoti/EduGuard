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