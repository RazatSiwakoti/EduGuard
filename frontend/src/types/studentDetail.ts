/**
 * Types for the student card (Phase 7.6b).
 *
 * Mirrors `app/schemas/student_detail.py` exactly. There is no codegen
 * step in this project, so the two files are kept in sync by hand — if a
 * field changes there, it must change here.
 */

import type { RiskTier } from "./dashboard";

/**
 * One criterion of the unit and this student's standing against it.
 *
 * The important difference from `DashboardCriterionScore`: a criterion
 * the student has NO event for is still present, with `score: null`.
 * The dashboard omits those; the card's job is showing them.
 */
export interface StudentCriterionDetail {
  criteria_id: number;
  name: string;
  category: string | null; // "attendance" | "weekly_tut" | "assessment" | "moodle"
  threshold: number;
  max_score: number;

  /** null = no mark on record. NOT the same as a mark of zero. */
  score: number | null;
  /** Only ever set for attendance / weekly_tut. */
  trend_value: number | null;

  /**
   * The normalised weekly cells behind `score`:
   *   attendance → 7 booleans        (W1–W7)
   *   weekly_tut → 6 status strings  (W2–W7)
   *
   * `null` for assessments and Moodle, which have no weekly dimension,
   * and `null` for anything ingested before 7.6b — those cells were
   * discarded at the time and there is nothing to recover them from.
   */
  weekly_values: (boolean | string)[] | null;

  recorded_at: string | null;
}

/** The three tutorial statuses, matching TUTORIAL_STATUS_CREDIT's keys. */
export type TutorialStatus = "submitted" | "late" | "not_submitted";

/**
 * One engine's independent verdict.
 *
 * ⚠️ `score` MEANS SOMETHING DIFFERENT PER ENGINE — never plot the two
 * on a shared scale. `score_kind` says which:
 *   - "badness"    (rule engine) — combined weighted badness. Higher = worse.
 *   - "confidence" (ML model)    — predicted class probability. Higher =
 *     more certain about the tier it chose, which is NOT more at risk.
 */
export interface StudentEngineDetail {
  tier: RiskTier;
  score: number;
  score_kind: "badness" | "confidence";
  is_incomplete: boolean;
  missing_criteria: string | null;
  explanation: string | null;
  computed_at: string | null;
}

/**
 * One recorded lecturer decision on an engine disagreement.
 *
 * `rule_tier` and `ml_tier` are the pair this decision was made ABOUT,
 * which is what makes carry-forward safe: a later run applies the
 * decision only if both engines still say exactly this. When they don't,
 * the card uses these to say what moved rather than silently re-asking.
 */
export interface StudentReviewDetail {
  id: number;
  decision: RiskTier;
  comment: string | null;
  rule_tier: RiskTier;
  ml_tier: RiskTier;
  reviewed_by: number;
  reviewer_name: string | null;
  created_at: string | null;
}

/** The requesting lecturer's own notes. Never another lecturer's. */
export interface StudentNoteDetail {
  body: string;
  updated_at: string | null;
}

/** The whole payload from GET /lecturer/students/{id}?unit_id=. */
export interface StudentDetailResponse {
  student_id: number;
  student_number: string;
  name: string;
  email: string | null;
  program: string | null;

  unit_id: number;
  unit_code: string;
  unit_name: string;
  enrolled_at: string | null;

  checkpoint_week: number;

  analysed: boolean;
  final_tier: RiskTier | null;
  requires_review: boolean;
  reason: string | null;
  computed_at: string | null;

  rule: StudentEngineDetail | null;
  ml: StudentEngineDetail | null;

  /** EVERY enabled criterion on the unit, including ones with no data. */
  criteria: StudentCriterionDetail[];

  note: StudentNoteDetail | null;

  /** Needed to submit a decision. null when never analysed. */
  verdict_id: number | null;

  /**
   * The review standing behind this verdict's tier — whether submitted
   * against this verdict or CARRIED FORWARD from an earlier run.
   * Non-null means a human decided this tier, not the engines.
   */
  applied_review_id: number | null;

  /** Every decision ever recorded, newest first. Append-only. */
  review_history: StudentReviewDetail[];
}

/** A lecturer's decision on an engine disagreement. */
export interface StudentReviewSubmit {
  decision: RiskTier;
  /** Optional — never required, or lecturers type "ok" fifteen times. */
  comment?: string;
}

/** Identifies which card to open. Both halves are required — risk is per unit. */
export interface StudentCardTarget {
  studentId: number;
  unitId: number;
}