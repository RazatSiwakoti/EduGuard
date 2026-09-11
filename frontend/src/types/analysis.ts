/**
 * Types for Run Analysis (section E1).
 *
 * Mirrors `app/schemas/analysis.py`. Kept in sync by hand — there is no
 * codegen step in this project.
 *
 * WHY THE RESULT IS A DIFF AND NOT A COUNT. "40 succeeded" answers "did
 * it work", not "what did it do", and the second is the question a
 * lecturer pressing the button actually has. The two movement
 * directions stay separate deliberately: someone moving toward risk
 * needs contacting, someone moving away is good news that needs no
 * action, and summing them loses exactly that distinction.
 */

export interface TierMovement {
  student_id: number;
  from_tier: string | null;
  to_tier: string | null;
  /** "toward_risk" | "away_from_risk" */
  direction: string;
}

export interface UnitAnalysisResult {
  unit_id: number;
  unit_code: string;
  unit_name: string;
  checkpoint_week: number;

  total_students: number;
  succeeded: number;
  failed: number;
  missing_data: number;
  /** Set when nothing ran, with the reason in plain words. */
  skipped_reason: string | null;

  newly_analysed: number;
  moved_toward_risk: number;
  moved_away_from_risk: number;
  unchanged: number;

  now_needs_review: number;
  review_resolved_by_engines: number;

  /**
   * A review decision carries forward only while BOTH engine tiers are
   * unchanged. One that did not carry is a human judgement the run has
   * discarded — reported because nothing was deleted, so nothing else
   * would tell the lecturer.
   */
  lecturer_decisions_carried: number;
  lecturer_decisions_invalidated: number;

  movements: TierMovement[];
}

export interface AnalysisRunResult {
  checkpoint_week: number;
  units_analysed: number;

  total_students: number;
  succeeded: number;
  failed: number;
  missing_data: number;

  newly_analysed: number;
  moved_toward_risk: number;
  moved_away_from_risk: number;
  unchanged: number;

  now_needs_review: number;
  review_resolved_by_engines: number;
  lecturer_decisions_carried: number;
  lecturer_decisions_invalidated: number;

  units: UnitAnalysisResult[];
}