/**
 * Types for unit assessment criteria.
 *
 * Mirrors app/schemas/criteria.py. A Criteria row is what a unit is
 * actually marked on, and it is the thing CSV columns get mapped TO
 * during import — so this file is a prerequisite for the import wizard,
 * not just for display.
 */

/**
 * What a criterion structurally IS, independent of its display name.
 *
 * The distinction matters because two of these are multi-column on a
 * spreadsheet and two are single-column:
 *   attendance  — exactly 7 weekly values (weeks 1-7)
 *   weekly_tut  — exactly 6 weekly values (weeks 2-7)
 *   assessment  — one value
 *   moodle      — one value (a raw login count, not a percentage)
 */
export type CriteriaCategory = "attendance" | "weekly_tut" | "assessment" | "moodle";

/** Response shape from GET /units/{unit_id}/criteria. */
export interface Criterion {
  id: number;
  unit_id: number;
  name: string;
  weight: number;
  threshold: number;
  max_score: number;
  /** Nullable on legacy rows created before categories existed. */
  category: CriteriaCategory | null;
  /** Only meaningful for assessments — which slot (1-4) this is. */
  sequence_number: number | null;
  enabled: boolean;
}

/**
 * The two categories every unit gets automatically via
 * seed_default_criteria(). Their weights and thresholds come from
 * risk_constants.py and are not lecturer-editable, so the UI shows them
 * as fixed rather than offering an edit control that would be rejected.
 */
export const FIXED_CATEGORIES: CriteriaCategory[] = ["attendance", "moodle"];

/**
 * How many spreadsheet columns a category consumes.
 * `null` means a single column.
 *
 * These are not style choices — calculate_attendance_trend() returns
 * None unless it receives exactly 7 values, and
 * calculate_tutorial_completion_trend() unless it receives exactly 6.
 * Get the count wrong and the student still gets a percentage but
 * silently loses their trend value, which the momentum chart depends on.
 */
export const CATEGORY_COLUMN_COUNT: Record<CriteriaCategory, number | null> = {
  attendance: 7,
  weekly_tut: 6,
  assessment: null,
  moodle: null,
};