"""
Sanity-check script for the rule engine.
Run with: python quick_test_rule_engine.py
"""

from app.services.rule_engine import (
    CriterionInput,
    compute_rule_based_risk,
    calculate_tutorial_completion_pct,
    calculate_attendance_pct,
    validate_lecturer_threshold,
)


def check(label, condition):
    status = "PASS" if condition else "FAIL"
    print(f"[{status}] {label}")


print("=" * 70)
print("TEST 1: The known edge case - 60% attendance, everything else fine")
print("=" * 70)
criteria = [
    CriterionInput("attendance", actual=60.0, threshold=80.0, weight=0.5),
    CriterionInput("assessment", actual=90.0, threshold=45.0, weight=0.4),
    CriterionInput("tutorial", actual=100.0, threshold=40.0, weight=0.05),
    CriterionInput("moodle", actual=15.0, threshold=10.0, weight=0.05),
]
result = compute_rule_based_risk(criteria)
print(f"Tier: {result.tier}, Score: {result.combined_score:.4f}")
check("Tier is safe", result.tier.value == "safe")
check("Score is 0.125", abs(result.combined_score - 0.125) < 0.0001)

print()
print("=" * 70)
print("TEST 2: A clearly high_risk student across the board")
print("=" * 70)
criteria = [
    CriterionInput("attendance", actual=20.0, threshold=80.0, weight=0.5),
    CriterionInput("assessment", actual=10.0, threshold=45.0, weight=0.4),
    CriterionInput("tutorial", actual=20.0, threshold=40.0, weight=0.05),
    CriterionInput("moodle", actual=2.0, threshold=10.0, weight=0.05),
]
result = compute_rule_based_risk(criteria)
print(f"Tier: {result.tier}, Score: {result.combined_score:.4f}")
for b in result.breakdown:
    print(f"  {b.category}: actual={b.actual}, threshold={b.threshold}, badness={b.badness:.4f}")
check("Tier is high_risk", result.tier.value == "high_risk")

print()
print("=" * 70)
print("TEST 3: No-tutorial unit (structural absence) - weight auto-rescales")
print("=" * 70)
criteria = [
    CriterionInput("attendance", actual=70.0, threshold=80.0, weight=0.5),
    CriterionInput("assessment", actual=40.0, threshold=45.0, weight=0.4),
    CriterionInput("tutorial", actual=None, threshold=40.0, weight=0.05),  # structurally absent
    CriterionInput("moodle", actual=12.0, threshold=10.0, weight=0.05),
]
result = compute_rule_based_risk(criteria)
print(f"Tier: {result.tier}, Score: {result.combined_score:.4f}")
print(f"Breakdown entries: {len(result.breakdown)} (should be 3, tutorial excluded)")
check("Tutorial excluded from breakdown", len(result.breakdown) == 3)
check("Total weight used rescaled to 0.95 (not 1.0)",
      abs(sum(b.weight for b in result.breakdown) - 0.95) < 0.0001)

print()
print("=" * 70)
print("TEST 4: Tutorial completion % with late=0.8 credit")
print("=" * 70)
statuses = ["submitted", "late", "late", "not_submitted", "submitted", "submitted"]
pct = calculate_tutorial_completion_pct(statuses)
# (1.0 + 0.8 + 0.8 + 0.0 + 1.0 + 1.0) / 6 * 100 = 76.666...
print(f"Completion %: {pct:.4f}")
check("Matches expected 76.6667%", abs(pct - 76.6667) < 0.001)

print()
print("=" * 70)
print("TEST 5: Attendance % calculation")
print("=" * 70)
weeks = [True, True, False, True, True, True, False]  # 5 of 7
pct = calculate_attendance_pct(weeks)
print(f"Attendance %: {pct:.4f}")
check("Matches expected 71.4286%", abs(pct - 71.4286) < 0.001)

print()
print("=" * 70)
print("TEST 6: Threshold floor validation")
print("=" * 70)
try:
    validate_lecturer_threshold("assessment", 30.0)
    check("Should have raised for 30% assessment (floor 45%)", False)
except ValueError as e:
    print(f"Correctly rejected: {e}")
    check("Assessment floor enforced", True)

try:
    validate_lecturer_threshold("tutorial", 35.0)
    check("Should have raised for 35% tutorial (floor 40%)", False)
except ValueError as e:
    print(f"Correctly rejected: {e}")
    check("Tutorial floor enforced", True)

try:
    validate_lecturer_threshold("assessment", 50.0)
    check("50% assessment (above floor) correctly allowed", True)
except ValueError:
    check("50% assessment (above floor) correctly allowed", False)

print()
print("=" * 70)
print("TEST 7: Unsubmitted assessment (literal 0, near-max badness)")
print("=" * 70)
criteria = [
    CriterionInput("assessment", actual=0.0, threshold=45.0, weight=0.4),
]
result = compute_rule_based_risk(criteria)
print(f"Badness for unsubmitted (0) assessment: {result.breakdown[0].badness:.4f}")
check("Badness is 1.0 (maximum)", abs(result.breakdown[0].badness - 1.0) < 0.0001)

print()
print("=" * 70)
print("TEST 8: Exact boundary values (0.15 and 0.30 cutoffs)")
print("=" * 70)
from app.services.rule_engine import bucket_score
check("0.1499 -> safe", bucket_score(0.1499).value == "safe")
check("0.15 -> low_risk (inclusive lower bound)", bucket_score(0.15).value == "low_risk")
check("0.2999 -> low_risk", bucket_score(0.2999).value == "low_risk")
check("0.30 -> high_risk (inclusive lower bound)", bucket_score(0.30).value == "high_risk")

print()
print("=" * 70)
print("All tests completed.")
print("=" * 70)