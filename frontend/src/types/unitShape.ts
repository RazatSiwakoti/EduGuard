/**
 * Types for the coordinator's unit-composition API (sections T1 + T2).
 *
 * Mirrors `app/schemas/unit_shape.py` and the lock schemas in
 * `app/schemas/criteria.py`. Two different backend routers are involved
 * and the split is deliberate, so it is repeated here:
 *
 *   GET/PUT /admin/units/{id}/criteria          the SHAPE   (T2, admin)
 *   GET     /units/{id}/criteria/unlock-preview the COST    (T1, admin)
 *   POST    /units/{id}/criteria/unlock         the WINDOW  (T1, admin)
 *
 * WHAT THIS FILE DELIBERATELY DOES NOT DECLARE
 * --------------------------------------------
 * There are no constants for "3 assessments", "20% quiz cap" or
 * "10% tutorials". The server sends them in `limits` on every read, and
 * a second copy in the client is a second place for a rule to be wrong
 * — the copy nobody re-checks when the rule changes.
 */

/** Quiz or assignment. NULL for attendance, Moodle and tutorials. */
export type AssessmentKind = "quiz" | "assignment";

/** Effective lock state. "draft" means editable right now. */
export type ShapeLockState = "draft" | "locked";

/**
 * Whether a unit's criteria may be edited, and why not.
 *
 * `reasons` is a list of finished sentences from the server. The UI
 * prints them verbatim rather than turning a code into prose — that is
 * how the rules end up described in two places and differently.
 */
export interface LockState {
  state: ShapeLockState;
  locked: boolean;
  /** Would it be locked but for an active unlock window? */
  lockable: boolean;
  /** An admin's one-shot unlock is open right now. */
  unlock_active: boolean;
  reasons: string[];
  locking_event_count: number;
  verdict_count: number;
  criteria_updated_at: string | null;
  criteria_unlocked_at: string | null;
}

/** One criterion as the shape API reports it. */
export interface CriterionShape {
  id: number | null;
  name: string;
  kind: AssessmentKind | null;
  category: string | null;
  sequence_number: number | null;
  /**
   * Share of the unit, reconstructed by the server from `weight`.
   * NOT from `max_score`: max_score is the share only for assessments
   * and is the 0-100 scale for the tutorial, so reading a percentage
   * off it reports a 10% tutorial as being worth 100% of the unit.
   */
  percentage: number | null;
  max_score: number | null;
  weight: number | null;
  /** The lecturer's pass bar (section T4). Read-only here. */
  threshold: number | null;
  /** Derived server-side: max_score * threshold / 100. Never stored. */
  pass_mark: number | null;
  enabled: boolean;
}

/**
 * The numbers the form validates against — sent by the server, never
 * hard-coded here. See the file docstring.
 */
export interface ShapeLimits {
  max_assessments: number;
  quiz_max_percentage: number;
  tutorial_percentage: number;
  max_total_percentage: number;
}

/** Response from GET /admin/units/{id}/criteria. */
export interface UnitShape {
  unit_id: number;
  unit_code: string;
  unit_name: string;
  /**
   * What the "not configured" badge reads. False until the unit has at
   * least one assessment or tutorials switched on — the two seeded rows
   * do not count, or the badge would never appear.
   */
  configured: boolean;
  tutorials_enabled: boolean;
  tutorial: CriterionShape | null;
  assessments: CriterionShape[];
  assessment_total_percentage: number;
  total_percentage: number;
  remaining_percentage: number;
  /** Attendance and Moodle. Stated as automatic, never editable here. */
  automatic: CriterionShape[];
  limits: ShapeLimits;
  lock: LockState;
}

/**
 * One assessment as the form submits it.
 *
 * `id` is present for a row that already exists and MUST be sent back.
 * Without it the server matches by slot only, and a re-ordered save
 * soft-deletes the stored rows and starts new ones — losing the
 * lecturer's pass bar and orphaning every mark attached to them.
 */
export interface AssessmentItemInput {
  id?: number | null;
  name: string;
  kind: AssessmentKind;
  percentage: number;
}

/**
 * Body for PUT /admin/units/{id}/criteria.
 *
 * No `threshold`, `weight` or `max_score`: the first belongs to the
 * lecturer (T4) and the other two are derived differently per category
 * by the server. The tutorial has no percentage because it is fixed —
 * it is a boolean, not a number.
 */
export interface UnitShapeInput {
  assessments: AssessmentItemInput[];
  tutorials_enabled: boolean;
}

/** Response from GET /units/{id}/criteria/unlock-preview. */
export interface UnlockPreview extends LockState {
  unit_code: string;
  verdicts_currently_valid: number;
  verdicts_already_stale: number;
  students_affected: number;
  /**
   * A finished sentence describing what SAVING will cost. Printed
   * verbatim — the server owns the wording so the dialog and the API
   * cannot disagree about what an unlock does.
   */
  consequence: string;
}

/** Response from POST /units/{id}/criteria/unlock. */
export interface UnlockResult extends LockState {
  unlocked: boolean;
  detail: string;
}