/**
 * Pure helpers for the student card (Phase 7.6b).
 *
 * Same contract as `studentsTable.ts`: plain functions, no React, no
 * network. Everything the card ASSERTS about a student is derived here,
 * in one place, so each claim can be traced to the criterion it came
 * from — which matters more on this screen than anywhere else in the
 * app, because the card is where a lecturer decides to contact someone.
 */

import type {
  StudentCriterionDetail,
  StudentDetailResponse,
  TutorialStatus,
} from "../types/studentDetail";
import { MOMENTUM_BAND_PP } from "./dashboardAggregations";

/* ------------------------------------------------------------------ */
/* Criterion grouping                                                  */
/* ------------------------------------------------------------------ */

export interface GroupedCriteria {
  attendance: StudentCriterionDetail | null;
  tutorial: StudentCriterionDetail | null;
  moodle: StudentCriterionDetail | null;
  assessments: StudentCriterionDetail[];
  /**
   * Criteria with `category === null`.
   *
   * These are scored by the rule engine (it falls back to the
   * criterion's name) but are INVISIBLE to the ML model, which filters
   * on category — so they manufacture disagreement between the two
   * engines. Every other view in this app keys off category and would
   * drop them silently. The card lists them explicitly, because a
   * criterion that only one engine can see is exactly the kind of thing
   * a lecturer needs to know about when the two disagree.
   */
  uncategorised: StudentCriterionDetail[];
  /** Categories the unit defines more than once — the rule engine scores
   *  all of them, the ML model keeps only the last, and single-value
   *  displays can only show one. Flagged rather than silently resolved. */
  duplicatedCategories: string[];
}

export function groupCriteria(criteria: StudentCriterionDetail[]): GroupedCriteria {
  const byCategory = new Map<string, StudentCriterionDetail[]>();
  const uncategorised: StudentCriterionDetail[] = [];

  for (const criterion of criteria) {
    if (criterion.category === null) {
      uncategorised.push(criterion);
      continue;
    }
    const list = byCategory.get(criterion.category) ?? [];
    list.push(criterion);
    byCategory.set(criterion.category, list);
  }

  const first = (category: string) => byCategory.get(category)?.[0] ?? null;

  return {
    attendance: first("attendance"),
    tutorial: first("weekly_tut"),
    moodle: first("moodle"),
    assessments: byCategory.get("assessment") ?? [],
    uncategorised,
    duplicatedCategories: ["attendance", "weekly_tut", "moodle"].filter(
      (category) => (byCategory.get(category)?.length ?? 0) > 1,
    ),
  };
}

/* ------------------------------------------------------------------ */
/* Weekly values                                                       */
/* ------------------------------------------------------------------ */

/** Attendance weeks are 1–7; tutorial weeks are 2–7 (week 1 has no tutorial). */
export const ATTENDANCE_FIRST_WEEK = 1;
export const TUTORIAL_FIRST_WEEK = 2;

/**
 * Narrows the untyped weekly list to attendance booleans.
 *
 * Returns null rather than an empty array when the data is absent, so
 * the card can distinguish "not recorded" from "recorded as all
 * absent". Rows ingested before 7.6b have `weekly_values: null` — those
 * cells were genuinely discarded and cannot be recovered, so the card
 * shows an explanation rather than an empty chart that would read as
 * seven weeks of absence.
 */
export function attendanceWeeks(
  criterion: StudentCriterionDetail | null,
): boolean[] | null {
  const raw = criterion?.weekly_values;
  if (!raw || raw.length === 0) return null;
  return raw.map((value) => value === true || value === "true" || value === "1");
}

const TUTORIAL_STATUSES: TutorialStatus[] = ["submitted", "late", "not_submitted"];

/** Narrows the untyped weekly list to tutorial statuses. */
export function tutorialWeeks(
  criterion: StudentCriterionDetail | null,
): TutorialStatus[] | null {
  const raw = criterion?.weekly_values;
  if (!raw || raw.length === 0) return null;

  return raw.map((value) => {
    const text = String(value);
    return (TUTORIAL_STATUSES as string[]).includes(text)
      ? (text as TutorialStatus)
      : "not_submitted";
  });
}

/** Credit each status earns — mirrors TUTORIAL_STATUS_CREDIT exactly. */
export const TUTORIAL_CREDIT: Record<TutorialStatus, number> = {
  submitted: 1,
  late: 0.8,
  not_submitted: 0,
};

export const TUTORIAL_LABELS: Record<TutorialStatus, string> = {
  submitted: "Submitted",
  late: "Late",
  not_submitted: "Not submitted",
};

/* ------------------------------------------------------------------ */
/* Assessment normalisation                                            */
/* ------------------------------------------------------------------ */

/**
 * An assessment mark as a PERCENTAGE of its own max_score.
 *
 * THIS IS THE 7.4 BUG, AND IT MUST NOT BE REINTRODUCED IN THE UI.
 * Assessment `score` is a raw mark on the criterion's own scale — 4 out
 * of 20 — while `threshold` is a percentage. Comparing them directly is
 * exactly what the rule engine used to do: it saw `15` where the ML
 * model saw `75%`, which guaranteed a false "needs review" on every
 * assessment not marked out of 100. The engine was fixed to normalise;
 * a metric bar that compares 4 against 45 makes the same mistake on
 * screen, drawing a threshold marker off the end of the track and
 * calling a perfectly good mark "below threshold".
 *
 * Attendance and weekly tutorials are already percentages, and Moodle
 * is a raw count against a raw-count threshold — neither goes through
 * here.
 */
export function assessmentPercent(
  score: number | null,
  maxScore: number,
): number | null {
  if (score === null) return null;
  if (maxScore <= 0) return score;
  return (score / maxScore) * 100;
}

/* ------------------------------------------------------------------ */
/* Risk indicators                                                     */
/* ------------------------------------------------------------------ */

export interface RiskIndicator {
  /** Short sentence a lecturer can act on. */
  text: string;
  /** How serious — drives the icon, never the colour alone. */
  severity: "critical" | "warning" | "info";
}

function formatPp(value: number): string {
  const rounded = Math.round(value);
  return `${rounded > 0 ? "+" : ""}${rounded}pp`;
}

/**
 * Why this student was flagged — DERIVED, never invented.
 *
 * Every line here is a restatement of a number already on the card,
 * traceable to one criterion. That constraint is deliberate. It would
 * be easy to generate lines like "academic probation imminent" or
 * "contact parent advised", and both would be fabrications: this system
 * holds no probation rules and no family contact policy, and tying an
 * intervention to a demographic attribute is exactly the bias failure
 * an early-warning system gets audited for.
 *
 * What a lecturer decides to do about "attendance is 15pp below the
 * threshold" is their judgement and their accountability. The system's
 * job is to be right about the 15pp.
 */
export function riskIndicators(detail: StudentDetailResponse): RiskIndicator[] {
  const indicators: RiskIndicator[] = [];
  const groups = groupCriteria(detail.criteria);

  const attendance = groups.attendance;
  if (attendance?.score != null && attendance.score < attendance.threshold) {
    const gap = Math.round(attendance.threshold - attendance.score);
    indicators.push({
      text: `Attendance ${Math.round(attendance.score)}% — ${gap}pp below this unit's ${Math.round(attendance.threshold)}% threshold.`,
      severity: gap >= 15 ? "critical" : "warning",
    });
  }

  if (attendance?.trend_value != null && attendance.trend_value <= -MOMENTUM_BAND_PP) {
    indicators.push({
      text: `Attendance is declining across the checkpoint window (${formatPp(attendance.trend_value)}).`,
      severity: "critical",
    });
  }

  const tutorial = groups.tutorial;
  if (tutorial?.score != null && tutorial.score < tutorial.threshold) {
    indicators.push({
      text: `Tutorial completion ${Math.round(tutorial.score)}% — below this unit's ${Math.round(tutorial.threshold)}% threshold.`,
      severity: "warning",
    });
  }

  if (tutorial?.trend_value != null && tutorial.trend_value <= -MOMENTUM_BAND_PP) {
    indicators.push({
      text: `Tutorial submissions are dropping off (${formatPp(tutorial.trend_value)}).`,
      severity: "warning",
    });
  }

  const unmarked = groups.assessments.filter((item) => item.score === null);
  if (groups.assessments.length > 0 && unmarked.length > 0) {
    indicators.push({
      text: `No mark recorded for ${unmarked.length} of ${groups.assessments.length} assessments: ${unmarked.map((item) => item.name).join(", ")}.`,
      severity: unmarked.length === groups.assessments.length ? "critical" : "warning",
    });
  }

  const moodle = groups.moodle;
  if (moodle?.score != null && moodle.score < moodle.threshold) {
    indicators.push({
      text: `${Math.round(moodle.score)} Moodle logins against a threshold of ${Math.round(moodle.threshold)}.`,
      severity: "warning",
    });
  }

  const missing = [detail.rule?.missing_criteria, detail.ml?.missing_criteria]
    .filter((value): value is string => Boolean(value))
    .flatMap((value) => value.split(", "))
    .filter((value, index, all) => all.indexOf(value) === index);

  if (missing.length > 0) {
    indicators.push({
      text: `Scored with incomplete data — missing: ${missing.join(", ")}.`,
      severity: "info",
    });
  }

  if (detail.requires_review) {
    indicators.push({
      text: "The rule engine and the ML model disagreed. No automatic verdict was recorded — this one needs your decision.",
      severity: "info",
    });
  }

  if (groups.uncategorised.length > 0) {
    indicators.push({
      text: `${groups.uncategorised.length} criterion/criteria have no category set (${groups.uncategorised.map((c) => c.name).join(", ")}) — scored by the rule engine but invisible to the ML model, which can manufacture disagreement.`,
      severity: "info",
    });
  }

  for (const category of groups.duplicatedCategories) {
    indicators.push({
      text: `This unit defines more than one "${category}" criterion. The rule engine scores all of them, the ML model keeps only the last, and the figures above show the first.`,
      severity: "info",
    });
  }

  return indicators;
}

/* ------------------------------------------------------------------ */
/* Engine explanations                                                 */
/* ------------------------------------------------------------------ */

/**
 * Splits a stored explanation into its individual phrases.
 *
 * Both engines build their `explanation` by joining parts with "; " —
 * `build_rule_explanation` and `build_ml_explanation` — so splitting on
 * that recovers the per-factor lines without re-running anything, and
 * without the explanation ever disagreeing with the verdict it was
 * written alongside.
 *
 * A defensive parse of our own format: if it ever changes, this returns
 * the whole string as one line rather than mangling it. The leading
 * "Rule engine flagged:" / "ML model (SHAP):" prefix is stripped because
 * the panel is already labelled with the engine's name.
 */
export function explanationPhrases(explanation: string | null): string[] {
  if (!explanation) return [];

  const withoutPrefix = explanation.replace(/^[^:]{0,40}:\s*/, "");
  const trimmed = withoutPrefix.replace(/\.\s*$/, "");

  return trimmed
    .split("; ")
    .map((phrase) => phrase.trim())
    .filter((phrase) => phrase.length > 0);
}

/* ------------------------------------------------------------------ */
/* Formatting                                                          */
/* ------------------------------------------------------------------ */

/** "20 Aug 2026, 4:00 pm" — en-AU, since this is an Australian institution. */
export function formatDateTime(value: string | null): string | null {
  if (!value) return null;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return null;

  return date.toLocaleString("en-AU", {
    day: "numeric",
    month: "short",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

/** "Jul 2024" — for the enrolment date, where the day is noise. */
export function formatMonthYear(value: string | null): string | null {
  if (!value) return null;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return null;
  return date.toLocaleString("en-AU", { month: "short", year: "numeric" });
}
