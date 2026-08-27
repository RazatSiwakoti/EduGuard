/**
 * Types for the Reports page (Phase 7.9 / sections C1–C4).
 *
 * Mirrors `app/schemas/reports.py` exactly. No codegen step exists in
 * this project, so the two files are kept in sync by hand.
 *
 * WHAT IS NOT HERE MATTERS MORE THAN WHAT IS.
 * There are no helper types for "computed on the client", because
 * nothing on this page is. The dashboard sends raw rows and aggregates
 * in the browser so cross-filtering costs nothing; a report is fixed,
 * computed once, and leaves the building as a PDF. If the browser
 * aggregated it, the PDF generator would aggregate it again and the two
 * would disagree the first time either changed.
 *
 * So: render these fields. Do not derive new ones.
 */

import type { RiskBucket, RiskTier } from "./dashboard";

export interface ReportBucketCount {
  bucket: RiskBucket;
  label: string;
  count: number;
  /**
   * Share of ANALYSED students, not of everyone. Including students the
   * engines never scored would understate the risk rate, which is the
   * opposite of what an early-warning system should do.
   */
  percent_of_analysed: number;
}

export interface ReportCriterionSummary {
  category: string;
  label: string;
  /**
   * On the SAME scale as `average_threshold`. Assessment marks are
   * divided by their own max_score server-side, so this is a percentage
   * for attendance/tutorials/assessments and a raw login count for
   * Moodle. Never plot the four on one axis — use percent_of_threshold.
   */
  average_score: number;
  average_threshold: number;
  /** 100 means "exactly at the bar". This is the comparable figure. */
  percent_of_threshold: number;
  sample_size: number;
  below_threshold: number;
  /**
   * null, not 0, where the question is meaningless. Assessments have no
   * early/late window, so "is anyone declining" cannot be asked of them,
   * and a 0 would read as "nobody is".
   */
  declining_count: number | null;
}

export interface ReportStudentRow {
  student_id: number;
  student_number: string;
  name: string;
  email: string | null;

  /** null while an engine disagreement is unresolved. */
  risk_tier: RiskTier | null;
  risk_label: string;

  /** null means NOT RECORDED, never zero. */
  attendance_pct: number | null;
  attendance_threshold: number | null;
  attendance_trend: number | null;

  tutorial_pct: number | null;
  tutorial_threshold: number | null;

  assessments_marked: number;
  assessments_total: number;
  /** Mean of marked assessments as a percentage of their own max_score. */
  assessment_avg_pct: number | null;

  moodle_logins: number | null;
  moodle_threshold: number | null;

  is_incomplete: boolean;
  decided_by_lecturer: boolean;
  reviewer_name: string | null;
  requires_review: boolean;

  alerts_sent: number;
  last_alert_at: string | null;
}

export interface ReportInterventionSummary {
  /** False when the alerts feature is not installed on this deployment. */
  available: boolean;

  alerts_total: number;
  alerts_sent: number;
  alerts_failed: number;
  alerts_queued: number;
  alerts_automatic: number;
  alerts_manual: number;
  /** Distinct students, which is not the same as alerts sent. */
  students_contacted: number;

  reviews_resolved: number;
  reviews_pending: number;
}

export interface ReportCheckpoint {
  week: number;
  /**
   * Distinct students with a verdict at this week — NOT rows. The
   * verdict table is append-only, so a unit re-analysed four times
   * would otherwise report four times its cohort size.
   */
  student_count: number;
  last_analysed_at: string | null;
}

export interface ReportResponse {
  unit_id: number;
  unit_code: string;
  unit_name: string;
  year: number | null;
  teaching_period: string | null;
  lecturer_name: string | null;

  checkpoint_week: number;
  generated_at: string;

  enrolled_count: number;
  analysed_count: number;
  not_analysed_count: number;
  last_analysed_at: string | null;

  distribution: ReportBucketCount[];
  criteria: ReportCriterionSummary[];
  at_risk: ReportStudentRow[];
  intervention: ReportInterventionSummary;

  /**
   * Honest qualifications, computed server-side and rendered in BOTH
   * the screen and the PDF. Render these ABOVE the figures they
   * qualify — see CaveatsPanel.
   */
  caveats: string[];
}