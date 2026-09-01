"""
Single source of truth for every fixed numeric constant shared between
the rule engine (app/services/rule_engine.py) and unit seeding
(app/services/unit_service.py). Defined ONCE here so the two can never
silently drift out of sync with each other.
"""

# Fixed, non-lecturer-editable thresholds
FIXED_ATTENDANCE_THRESHOLD = 50.0   # percent
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

# ---------------------------------------------------------------------
# Evidence coverage
#
# The share of a unit's total criterion weight that must actually have
# data behind it before either engine is allowed to state a tier.
#
# WHY THIS EXISTS. Both engines used to drop a criterion with no data
# from BOTH sides of the weighted average, which silently rescaled the
# blend onto whatever evidence happened to exist. A student with no
# assessment marks was scored purely on attendance and tutorials, scored
# a perfect 0.0000 badness, and was reported SAFE - and a student with
# NO data at all scored 0.0000 too, because zero is not a neutral value
# here, it is the best possible one.
#
# 0.70 rather than something stricter: a student missing only their
# Moodle datum still has 96% of the unit's weight behind them and does
# not belong in a review queue. A student missing a major assessment
# drops to 0.65 and does. A floor that sends nearly-complete students to
# review would fill the queue with non-events, and a queue full of
# non-events is one nobody reads.
MIN_EVIDENCE_COVERAGE = 0.70