"""
Single source of truth for every fixed numeric constant shared between
the rule engine (app/services/rule_engine.py) and unit seeding
(app/services/unit_service.py). Defined ONCE here so the two can never
silently drift out of sync with each other.
"""

# Fixed, non-lecturer-editable thresholds
FIXED_ATTENDANCE_THRESHOLD = 80.0   # percent
FIXED_MOODLE_THRESHOLD = 10.0       # raw login count over the checkpoint

# Fixed, non-lecturer-editable weights
FIXED_ATTENDANCE_WEIGHT = 0.5
FIXED_MOODLE_WEIGHT = 0.05

# Global floors - lecturer-adjustable thresholds cannot be set below these
ASSESSMENT_THRESHOLD_FLOOR = 45.0   # percent
TUTORIAL_THRESHOLD_FLOOR = 40.0     # percent

# Final label bucket cutoffs - fixed, independent of any single criterion
# threshold. Matches the cutoffs used when the ML training labels were built.
SAFE_CUTOFF = 0.15
HIGH_RISK_CUTOFF = 0.30

# Weekly tutorial submission status -> partial credit toward completion %
# late=0.8 matches the value used in the ML training label formula.
TUTORIAL_STATUS_CREDIT = {
    "submitted": 1.0,
    "late": 0.8,
    "not_submitted": 0.0,
}