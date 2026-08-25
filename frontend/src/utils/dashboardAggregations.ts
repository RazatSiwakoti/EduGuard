/**
 * Pure aggregation functions for the lecturer dashboard (Phase 6.2).
 *
 * Everything here is a plain function of its inputs — no React, no
 * network, no hidden state. That is deliberate:
 *
 *  1. The dashboard cross-filters six visuals at once. Recomputing them
 *     from one already-loaded array inside a `useMemo` is instant, where
 *     asking the server on every filter click would not be.
 *  2. Pure functions are trivially unit-testable later, without having
 *     to render a component or mock an API.
 *
 * Keep it that way — if something here starts needing a hook, it belongs
 * in the component, not in this file.
 */

import type {
  DashboardFilters,
  DashboardStudent,
  DashboardUnit,
  RiskBucket,
  RiskTier,
} from "../types/dashboard";

/* ------------------------------------------------------------------ */
/* Display labels                                                      */
/* ------------------------------------------------------------------ */

/** Human labels for every bucket, used by charts, legends and the table. */
export const BUCKET_LABELS: Record<RiskBucket, string> = {
  safe: "Safe",
  low_risk: "Low Risk",
  high_risk: "High Risk",
  needs_review: "Needs Review",
  not_analysed: "Not Analysed",
};

/**
 * Fixed display order — worst first. Charts and legends must all use
 * this same order so a colour always means the same thing in every
 * visual on the page.
 */
export const BUCKET_ORDER: RiskBucket[] = [
  "high_risk",
  "low_risk",
  "safe",
  "needs_review",
  "not_analysed",
];

/** The three real engine tiers, ordered worst → best for the matrix axes. */
export const TIER_ORDER: RiskTier[] = ["high_risk", "low_risk", "safe"];

/** Backend category slug → the label a lecturer actually recognises. */
export const CATEGORY_LABELS: Record<string, string> = {
  attendance: "Attendance",
  weekly_tut: "Weekly Tutorials",
  assessment: "Assessments",
  moodle: "Moodle Logins",
};

/**
 * Category display order for the criteria chart. Fixed rather than
 * discovered from the data, so the bars don't reshuffle themselves when
 * a filter changes and leave the lecturer re-reading the axis.
 */
export const CATEGORY_ORDER = ["attendance", "weekly_tut", "assessment", "moodle"];

/**
 * How many percentage points a student's trend must move before we call
 * it a real direction rather than noise. A student who attended 2 of 3
 * early weeks and 3 of 3 late weeks has already moved 33pp, so 10pp is
 * a deliberately low bar that still filters out rounding wobble.
 */
export const MOMENTUM_BAND_PP = 10;

/* ------------------------------------------------------------------ */
/* Bucketing and filtering                                             */
/* ------------------------------------------------------------------ */

/**
 * Which bucket one student row belongs to.
 *
 * Order of the checks matters. "Not analysed" is tested first because
 * such a row has no verdict at all, and "needs review" is tested before
 * final_tier because a review-pending verdict deliberately carries a
 * NULL tier — treating that as missing data would hide exactly the
 * cases a lecturer most needs to act on.
 */
export function getBucket(student: DashboardStudent): RiskBucket {
  if (!student.analysed) return "not_analysed";
  if (student.requires_review || student.final_tier === null) return "needs_review";
  return student.final_tier;
}

/**
 * Applies both live filters. `null` on either filter means "no
 * restriction", which is how the initial "All units, all risk levels"
 * state is represented.
 */
export function filterStudents(
  students: DashboardStudent[],
  filters: DashboardFilters,
): DashboardStudent[] {
  return students.filter((student) => {
    if (filters.unitId !== null && student.unit_id !== filters.unitId) return false;
    if (filters.bucket !== null && getBucket(student) !== filters.bucket) return false;
    return true;
  });
}

/* ------------------------------------------------------------------ */
/* KPI tiles                                                           */
/* ------------------------------------------------------------------ */

export interface DashboardKpis {
  totalStudents: number;
  highRisk: number;
  needsReview: number;
  notAnalysed: number;
  unitCount: number;
  /** High risk as a share of ANALYSED students, not of everyone. */
  highRiskPercent: number;
}

/**
 * Headline numbers.
 *
 * highRiskPercent divides by analysed students rather than the whole
 * cohort on purpose: including students the engine never scored would
 * quietly understate the real risk rate, which is the opposite of what
 * an early-warning system should do.
 */
export function computeKpis(
  students: DashboardStudent[],
  units: DashboardUnit[],
  filters: DashboardFilters,
): DashboardKpis {
  let highRisk = 0;
  let needsReview = 0;
  let notAnalysed = 0;

  for (const student of students) {
    const bucket = getBucket(student);
    if (bucket === "high_risk") highRisk += 1;
    else if (bucket === "needs_review") needsReview += 1;
    else if (bucket === "not_analysed") notAnalysed += 1;
  }

  const analysed = students.length - notAnalysed;

  return {
    totalStudents: students.length,
    highRisk,
    needsReview,
    notAnalysed,
    unitCount: filters.unitId !== null ? 1 : units.length,
    highRiskPercent: analysed > 0 ? Math.round((highRisk / analysed) * 100) : 0,
  };
}

/* ------------------------------------------------------------------ */
/* Chart 1 — risk distribution (donut)                                 */
/* ------------------------------------------------------------------ */

export interface BucketSlice {
  bucket: RiskBucket;
  label: string;
  count: number;
}

/**
 * Counts per bucket, in fixed BUCKET_ORDER.
 *
 * Empty buckets are dropped so the donut doesn't render zero-width
 * slices — but "needs_review" and "not_analysed" are kept whenever they
 * are non-zero, rather than being folded into the three engine tiers.
 * Those two states are findings in their own right.
 */
export function countByBucket(students: DashboardStudent[]): BucketSlice[] {
  const counts = new Map<RiskBucket, number>();

  for (const student of students) {
    const bucket = getBucket(student);
    counts.set(bucket, (counts.get(bucket) ?? 0) + 1);
  }

  return BUCKET_ORDER.filter((bucket) => (counts.get(bucket) ?? 0) > 0).map((bucket) => ({
    bucket,
    label: BUCKET_LABELS[bucket],
    count: counts.get(bucket) ?? 0,
  }));
}

/* ------------------------------------------------------------------ */
/* Chart 2 — risk by unit (stacked bar)                                */
/* ------------------------------------------------------------------ */

export interface UnitRiskRow {
  unitId: number;
  unitCode: string;
  unitName: string;
  total: number;
  safe: number;
  low_risk: number;
  high_risk: number;
  needs_review: number;
  not_analysed: number;
}

/**
 * One row per unit, split by bucket — the stacked bar's data.
 *
 * Built from the `units` list rather than from whatever units happen to
 * appear in `students`, so a unit with zero enrolled students still
 * shows up as an empty bar. A missing bar reads as "no problems here";
 * an empty one correctly reads as "nobody is enrolled yet".
 */
export function riskByUnit(
  students: DashboardStudent[],
  units: DashboardUnit[],
): UnitRiskRow[] {
  const rows = new Map<number, UnitRiskRow>();

  for (const unit of units) {
    rows.set(unit.id, {
      unitId: unit.id,
      unitCode: unit.unit_code,
      unitName: unit.unit_name,
      total: 0,
      safe: 0,
      low_risk: 0,
      high_risk: 0,
      needs_review: 0,
      not_analysed: 0,
    });
  }

  for (const student of students) {
    const row = rows.get(student.unit_id);
    if (!row) continue; // Defensive: student from a unit not in the list.
    row[getBucket(student)] += 1;
    row.total += 1;
  }

  return [...rows.values()];
}

/* ------------------------------------------------------------------ */
/* Chart 3 — criteria performance vs threshold                         */
/* ------------------------------------------------------------------ */

export interface CriteriaPerformanceRow {
  category: string;
  label: string;
  /** Cohort average expressed as a percentage OF THE THRESHOLD. */
  percentOfThreshold: number;
  /** Averages on the criterion's own native scale, for the tooltip. */
  averageScore: number;
  averageThreshold: number;
  /** How many student-criterion data points went into this average. */
  sampleSize: number;
  /** How many of those points sat below their own threshold. */
  belowThreshold: number;
}

/**
 * Cohort performance per criteria category, normalised to "% of
 * threshold" so all four categories share one honest axis.
 *
 * WHY NORMALISE. The categories are not on the same scale at all:
 * attendance is a percentage against a threshold of 80, while Moodle is
 * a raw login count against a threshold of 10. Plotting both raw would
 * squash the Moodle bar into nothing and make the chart worse than
 * useless. Dividing each value by its own threshold puts everything on
 * one scale where 100% means "exactly at the bar" — so a reference line
 * at 100 becomes meaningful for every category at once.
 *
 * Normalisation happens PER STUDENT before averaging, not on the
 * averages. Thresholds are set per unit, so two units can define
 * different assessment thresholds; normalising first keeps each
 * student's result measured against the bar they were actually held to.
 */
export function criteriaPerformance(
  students: DashboardStudent[],
): CriteriaPerformanceRow[] {
  interface Accumulator {
    percentSum: number;
    scoreSum: number;
    thresholdSum: number;
    count: number;
    below: number;
  }

  const accumulators = new Map<string, Accumulator>();

  for (const student of students) {
    for (const criterion of student.criteria) {
      if (!criterion.category) continue; // Legacy rows with no category.

      // A zero or negative threshold would make the ratio meaningless
      // (or divide by zero), so those points are skipped rather than
      // allowed to produce an Infinity that breaks the axis.
      if (criterion.threshold <= 0) continue;

      const accumulator = accumulators.get(criterion.category) ?? {
        percentSum: 0,
        scoreSum: 0,
        thresholdSum: 0,
        count: 0,
        below: 0,
      };

      accumulator.percentSum += (criterion.score / criterion.threshold) * 100;
      accumulator.scoreSum += criterion.score;
      accumulator.thresholdSum += criterion.threshold;
      accumulator.count += 1;
      if (criterion.score < criterion.threshold) accumulator.below += 1;

      accumulators.set(criterion.category, accumulator);
    }
  }

  return CATEGORY_ORDER.filter((category) => accumulators.has(category)).map((category) => {
    const accumulator = accumulators.get(category)!;
    return {
      category,
      label: CATEGORY_LABELS[category] ?? category,
      percentOfThreshold: round1(accumulator.percentSum / accumulator.count),
      averageScore: round1(accumulator.scoreSum / accumulator.count),
      averageThreshold: round1(accumulator.thresholdSum / accumulator.count),
      sampleSize: accumulator.count,
      belowThreshold: accumulator.below,
    };
  });
}

/* ------------------------------------------------------------------ */
/* Chart 4 — momentum (diverging bar)                                  */
/* ------------------------------------------------------------------ */

export interface MomentumRow {
  category: string;
  label: string;
  /** Stored NEGATIVE so the bar renders to the left of the zero line. */
  declining: number;
  improving: number;
  stable: number;
  /** Positive count of declining students, for labels and tooltips. */
  decliningCount: number;
}

/**
 * Who is falling behind and who is catching up.
 *
 * This is the honest stand-in for a week-by-week trend line. Raw weekly
 * values are aggregated at ingestion and never persisted (see
 * ingestion_service.py), so a real time-series simply cannot be drawn
 * from this database. What IS stored is `trend_value`: late-window
 * average minus early-window average, in percentage points. Negative
 * means the student is sliding.
 *
 * Only attendance and weekly tutorials carry a trend value — assessments
 * and Moodle are single figures with no early/late split — so those two
 * categories are all this chart can ever show, by design rather than by
 * omission.
 */
export function momentumByCategory(students: DashboardStudent[]): MomentumRow[] {
  const rows = new Map<string, MomentumRow>();

  for (const student of students) {
    for (const criterion of student.criteria) {
      if (!criterion.category) continue;
      if (criterion.trend_value === null) continue;

      const row = rows.get(criterion.category) ?? {
        category: criterion.category,
        label: CATEGORY_LABELS[criterion.category] ?? criterion.category,
        declining: 0,
        improving: 0,
        stable: 0,
        decliningCount: 0,
      };

      if (criterion.trend_value <= -MOMENTUM_BAND_PP) {
        // Negative on purpose — this is what makes the bar diverge left.
        row.declining -= 1;
        row.decliningCount += 1;
      } else if (criterion.trend_value >= MOMENTUM_BAND_PP) {
        row.improving += 1;
      } else {
        row.stable += 1;
      }

      rows.set(criterion.category, row);
    }
  }

  return CATEGORY_ORDER.filter((category) => rows.has(category)).map(
    (category) => rows.get(category)!,
  );
}

/* ------------------------------------------------------------------ */
/* Chart 5 — rule vs ML agreement matrix                               */
/* ------------------------------------------------------------------ */

export interface AgreementCell {
  ruleTier: RiskTier;
  mlTier: RiskTier;
  count: number;
  /** True on the diagonal, where the two engines reached the same tier. */
  agreed: boolean;
}

export interface AgreementMatrix {
  cells: AgreementCell[];
  total: number;
  agreedCount: number;
  /** Whole-number percentage of scored students the engines agreed on. */
  agreementPercent: number;
  /** The largest count in any cell — used to scale the heatmap shading. */
  maxCount: number;
}

/**
 * A 3×3 count of rule-engine tier against ML-model tier.
 *
 * This visual is specific to EduGuard's hybrid architecture: it shows
 * exactly where the two independent engines diverged and the hybrid
 * layer had to reconcile them. The off-diagonal safe↔high_risk corners
 * are the cases that get escalated to a lecturer for manual review, so
 * a heavy corner is a direct signal that the two models are pulling
 * against each other on this cohort.
 *
 * Students without both tiers (never analysed) are excluded — a missing
 * score is not a disagreement.
 */
export function engineAgreement(students: DashboardStudent[]): AgreementMatrix {
  const counts = new Map<string, number>();
  let total = 0;
  let agreedCount = 0;
  let maxCount = 0;

  for (const student of students) {
    if (!student.rule_tier || !student.ml_tier) continue;

    const key = `${student.rule_tier}|${student.ml_tier}`;
    const next = (counts.get(key) ?? 0) + 1;
    counts.set(key, next);
    if (next > maxCount) maxCount = next;

    total += 1;
    if (student.rule_tier === student.ml_tier) agreedCount += 1;
  }

  const cells: AgreementCell[] = [];
  for (const ruleTier of TIER_ORDER) {
    for (const mlTier of TIER_ORDER) {
      cells.push({
        ruleTier,
        mlTier,
        count: counts.get(`${ruleTier}|${mlTier}`) ?? 0,
        agreed: ruleTier === mlTier,
      });
    }
  }

  return {
    cells,
    total,
    agreedCount,
    agreementPercent: total > 0 ? Math.round((agreedCount / total) * 100) : 0,
    maxCount,
  };
}

/* ------------------------------------------------------------------ */
/* Shared helpers                                                      */
/* ------------------------------------------------------------------ */

/** One decimal place — enough precision for a chart label, no more. */
function round1(value: number): number {
  return Math.round(value * 10) / 10;
}