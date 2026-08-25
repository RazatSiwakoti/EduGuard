"""
One-off repair: gives every existing unit its missing default criteria.

WHY THIS IS NEEDED
------------------
seed_default_criteria() was written, documented as mandatory, and never
called from create_unit. Every unit created through POST /admin/units
therefore has ZERO Criteria rows.

That silently breaks risk scoring rather than erroring. With no criteria:

  * the rule engine's total_weight_used is 0, combined_score falls back
    to 0.0, and bucket_score(0.0) returns SAFE - so every student in
    that unit is reported safe no matter what their data says
  * the ML engine receives every feature as NaN and predicts from
    priors alone
  * nothing anywhere reports a problem

The route is fixed going forward. This script repairs units created
before that fix.

SAFE TO RE-RUN. Each category is added only if the unit does not
already have one, so a unit that was set up correctly is left untouched
and running this twice never produces duplicates.

That last point matters more than it looks: ml_score_service builds
criteria_by_category with a dict comprehension, so a duplicate
attendance criterion would be silently dropped by the ML engine while
the rule engine counted BOTH - manufacturing a disagreement out of
nothing.

Usage, from the backend/ directory:

    python scripts/backfill_default_criteria.py           # report only
    python scripts/backfill_default_criteria.py --apply   # write changes
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import SessionLocal
from app.models.criteria import Criteria
from app.models.enums import CriteriaCategory
from app.models.unit import Unit
from app.services.unit_service import seed_default_criteria

# Seeded by seed_default_criteria(). Anything else on a unit was created
# by a lecturer and is none of this script's business.
DEFAULT_CATEGORIES = (CriteriaCategory.ATTENDANCE, CriteriaCategory.MOODLE)


def main() -> None:
    apply_changes = "--apply" in sys.argv
    db = SessionLocal()

    try:
        units = db.query(Unit).order_by(Unit.id).all()
        if not units:
            print("No units found.")
            return

        needs_repair = []

        for unit in units:
            existing = {
                criterion.category
                for criterion in db.query(Criteria)
                .filter(Criteria.unit_id == unit.id)
                .all()
                if criterion.category
            }
            missing = [c for c in DEFAULT_CATEGORIES if c not in existing]
            if missing:
                needs_repair.append((unit, missing))

        print(f"Scanned {len(units)} unit(s).")

        if not needs_repair:
            print("Every unit already has its default criteria. Nothing to do.")
            return

        print(f"{len(needs_repair)} unit(s) missing default criteria:\n")
        for unit, missing in needs_repair:
            names = ", ".join(c.value for c in missing)
            print(f"  #{unit.id:<4} {unit.unit_code:<12} missing: {names}")

        if not apply_changes:
            print("\nDry run - nothing written. Re-run with --apply to fix these.")
            return

        # seed_default_criteria() always stages BOTH criteria, so a unit
        # missing only one would get a duplicate of the other. Staging
        # each missing category individually avoids that, and keeps the
        # values sourced from the same helper rather than duplicating
        # risk_constants here.
        for unit, missing in needs_repair:
            before = {
                criterion.category
                for criterion in db.query(Criteria)
                .filter(Criteria.unit_id == unit.id)
                .all()
                if criterion.category
            }

            seed_default_criteria(db, unit)

            # Drop whichever staged rows duplicate a category the unit
            # already had, before anything is committed.
            for staged in list(db.new):
                if isinstance(staged, Criteria) and staged.unit_id == unit.id:
                    if staged.category in before:
                        db.expunge(staged)

        db.commit()
        print(f"\nDone. Repaired {len(needs_repair)} unit(s).")
        print(
            "Now re-run the analysis for each repaired unit so its students "
            "are rescored against the criteria that finally exist:\n"
            "  POST /units/{unit_id}/risk/run-analysis"
        )

    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()