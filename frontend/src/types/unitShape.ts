/**
 * The unit's shape as the lecturer reads it, and the pass bar they set.
 *
 * Mirrors `app/schemas/unit_shape.py`. Two different people own two
 * halves of one row and this file is where that split becomes visible:
 *
 *   coordinator   name, kind, percentage  -> weight, max_score   (T2)
 *   lecturer      threshold                                       (T4)
 *
 * `pass_mark = max_score * threshold / 100` is the only place they
 * meet, and the server derives it at read time rather than storing it —
 * so neither side can overwrite the other's half.
 */

/** Quiz or assignment. Null for attendance, Moodle and tutorials. */
export type AssessmentKind = "quiz" | "assignment";

/** One criterion, as the shape endpoints return it. */
export interface CriterionShape {
  id: number | null;
  name: string;
  kind: AssessmentKind | null;
  category: string | null;
  sequence_number: number | null;
  /**
   * Share of the unit, reconstructed server-side from `weight` — NOT
   * from `max_score`. The two are only the same number for an
   * assessment: a 10% tutorial is stored with max_score 100, and
   * reading the percentage off it would report the tutorial as being
   * worth the whole unit.
   */
  percentage: number | null;
  max_score: number | null;
  weight: number | null;
  threshold: number | null;
  /** Derived, never stored: max_score × threshold ÷ 100. */
  pass_mark: number | null;
  enabled: boolean;
}

/** The numbers the server validates against, sent rather than copied. */
export interface ShapeLimits {
  max_assessments: number;
  quiz_max_percentage: number;
  tutorial_percentage: number;
  max_total_percentage: number;
}

/** T1's lock, carried in the same response as the shape it governs. */
export interface ShapeLockState {
  state: "draft" | "locked";
  locked: boolean;
  lockable: boolean;
  unlock_active: boolean;
  reasons: string[];
  locking_event_count: number;
  verdict_count: number;
  criteria_updated_at: string | null;
  criteria_unlocked_at: string | null;
}

export type LockState = ShapeLockState;

/**
 * One slider's worth of state — one per adjustable CATEGORY, not one
 * per item.
 *
 * `value` is null when `mixed` is true, i.e. when the category's rows
 * sit on different bars. The form must say so rather than render one of
 * them: D1's per-item endpoint can leave two assessments disagreeing,
 * and a slider showing 50 for a unit whose second assessment is at 46
 * would flatten the 46 on its first drag without ever displaying it.
 */
export interface ThresholdGroup {
  category: string;
  /** The lowest a lecturer may go. 45 for assessments, 40 for tutorials. */
  floor: number | null;
  /** The ceiling AND the starting point. Never raised above. */
  default: number;
  /** How many enabled criteria this slider writes to. 0 → no slider. */
  applies_to: number;
  value: number | null;
  mixed: boolean;
  values: number[];
  adjustable: boolean;
  item_names: string[];
}

/** Response from GET /units/{id}/criteria/shape. */
export interface LecturerUnitShape {
  unit_id: number;
  unit_code: string;
  unit_name: string;
  configured: boolean;
  tutorials_enabled: boolean;
  tutorial: CriterionShape | null;
  assessments: CriterionShape[];
  assessment_total_percentage: number;
  total_percentage: number;
  remaining_percentage: number;
  /** Attendance and Moodle. Stated as automatic, never given a slider. */
  automatic: CriterionShape[];
  limits: ShapeLimits;
  lock: ShapeLockState;
  thresholds: Record<string, ThresholdGroup>;
}

export type UnitShape = Omit<LecturerUnitShape, "thresholds">;

export interface AssessmentItemInput {
  id?: number | null;
  name: string;
  kind: AssessmentKind;
  percentage: number;
}

export interface UnitShapeInput {
  assessments: AssessmentItemInput[];
  tutorials_enabled: boolean;
}

export interface UnlockPreview extends ShapeLockState {
  unit_code: string;
  verdicts_currently_valid: number;
  verdicts_already_stale: number;
  students_affected: number;
  consequence: string;
}

export interface UnlockResult extends ShapeLockState {
  unlocked: boolean;
  detail: string;
}

/**
 * Body for PATCH /units/{id}/criteria/thresholds.
 *
 * Only these two keys exist. The server declares `extra="forbid"`, so
 * sending `attendance` or `weight` is a 422 rather than a field that is
 * silently dropped — a lecturer certain they moved a bar that never
 * moved is the exact outcome the guards exist to prevent.
 */
export interface ThresholdUpdate {
  assessment?: number;
  weekly_tut?: number;
}

/** The two categories that get a slider, in display order. */
export const ADJUSTABLE_CATEGORIES = ["assessment", "weekly_tut"] as const;