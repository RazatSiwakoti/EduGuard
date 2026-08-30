/** The three tiers the risk engines can actually produce. */
export type RiskTier = "safe" | "low_risk" | "high_risk";

/**
 * What a student is bucketed into on the dashboard. Wider than RiskTier because two states exist that are NOT engine outputs:
 *
 *  - "needs_review": the rule engine and the ML model disagreed badly
 *    (safe vs high_risk), so the hybrid engine deliberately refused to
 *    pick a winner. final_tier is NULL until a lecturer resolves it.
 *  - "not_analysed": the student is enrolled and may even have uploaded
 *    data, but the analysis pipeline has never produced a verdict.
 *  - "incomplete": analysis ran, but one or both engines detected
 *   missing academic input. The calculated tiers may still exist
 *   internally, but the dashboard must not present the final tier
 *   as authoritative.
 *  - "not_analysed": no verdict has ever been produced.
 * Both are shown rather than hidden — a lecturer needs to know their
 * cohort has unresolved cases, not see them quietly vanish from a chart.
 */
export type RiskBucket = RiskTier | "needs_review" | "not_analysed"| "incomplete";
export interface DashboardUnitCriterion {
  id: number;
  name: string;
  category: string | null; // "attendance" | "weekly_tut" | "assessment" | "moodle"
  threshold: number;
  max_score: number;
}
/** One unit the logged-in lecturer is assigned to. */
export interface DashboardUnit {
  id: number;
  unit_code: string;
  unit_name: string;
  year: number | null;
  teaching_period: string | null;
  level: string | null;
  enrolled_count: number;
  criteria: DashboardUnitCriterion[];
}

/**
 * One student's latest value for a single criterion.
 *
 * `score` is on the criterion's NATIVE scale, which differs by category:
 * a percentage for attendance/tutorials/assessments, but a raw login
 * count for Moodle. Never plot these directly on a shared axis — see
 * `criteriaPerformance` in utils/dashboardAggregations.ts.
 */
export interface DashboardCriterionScore {
  criteria_id: number;
  name: string;
  category: string | null; // "attendance" | "weekly_tut" | "assessment" | "moodle"
  score: number;
  threshold: number;
  max_score: number;
  /** Early-vs-late momentum. Only ever set for attendance / weekly_tut. */
  trend_value: number | null;
}

/**
 * One student in one unit. A student enrolled in two of the lecturer's
 * units produces TWO rows — risk is always computed per unit, so the
 * (student_id, unit_id) pair is the real identity of a row.
 */
export interface DashboardStudent {
  student_id: number;
  student_number: string;
  name: string;
  email: string | null;
  program: string | null;
  gender: string | null;
  age: number | null;

  unit_id: number;
  unit_code: string;

  /** False = enrolled but the pipeline has never produced a verdict. */
  analysed: boolean;

  final_tier: RiskTier | null;
  requires_review: boolean;
  reason: string | null;
  checkpoint_week: number | null;
  computed_at: string | null;

  rule_tier: RiskTier | null;
  rule_score: number | null;
  ml_tier: RiskTier | null;
  ml_score: number | null;

  /** Either engine flagged missing input data for this student. */
  is_incomplete: boolean;

  criteria: DashboardCriterionScore[];
}

/** The whole payload from GET /lecturer/dashboard. */
export interface LecturerDashboardResponse {
  units: DashboardUnit[];
  students: DashboardStudent[];
  checkpoint_week: number;
}

/**
 * The dashboard's two live filters.
 *
 * `unitId: null` means "All units" — the initial state, as specified.
 * `bucket: null` means "all risk levels".
 */
export interface DashboardFilters {
  unitId: number | null;
  bucket: RiskBucket | null;
}