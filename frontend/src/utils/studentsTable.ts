/**
 * Pure helpers for the Students page (Phase 7.6a).
 *
 * Same contract as `dashboardAggregations.ts`: plain functions of their
 * inputs, no React, no network, no hidden state. Two reasons that
 * matters here in particular:
 *
 *  1. The page cross-filters on four things at once (subject, risk tab,
 *     search, sort) and then paginates. Recomputing that chain from one
 *     already-cached array inside a `useMemo` is instant; asking the
 *     server on every keystroke would not be.
 *  2. Every rule that decides what a lecturer SEES about a student —
 *     which criterion counts as "attendance", what makes a trend
 *     "declining", how many assessments are marked — lives in one
 *     testable place rather than being scattered through JSX.
 *
 * If something in here starts needing a hook, it belongs in the
 * component, not in this file.
 */

import type {
  DashboardStudent,
  DashboardUnit,
  DashboardCriterionScore,
  RiskBucket,
} from "../types/dashboard";
import {
  BUCKET_LABELS,
  BUCKET_ORDER,
  MOMENTUM_BAND_PP,
  getBucket,
} from "./dashboardAggregations";

/* ------------------------------------------------------------------ */
/* Constants                                                           */
/* ------------------------------------------------------------------ */

/**
 * Rows per page.
 *
 * Eight is a design decision, not a technical one: the table sits below
 * a header, four KPI-style tabs and a filter bar, and eight rows is
 * what still fits on a laptop screen without the lecturer scrolling
 * past the filters they just set. Pagination is client-side — the whole
 * cohort is already in memory from the dashboard query.
 */
export const PAGE_SIZE = 8;

/**
 * Severity rank used for sorting, derived from BUCKET_ORDER (worst
 * first) so this page's idea of "most urgent" can never drift from the
 * order the dashboard's charts and legends use.
 */
const SEVERITY_RANK: Record<string, number> = Object.fromEntries(
  BUCKET_ORDER.map((bucket, index) => [bucket, index]),
);

/* ------------------------------------------------------------------ */
/* Criterion extraction                                                */
/* ------------------------------------------------------------------ */

/**
 * One metric cell's worth of data: the student's value for a single
 * criterion category, plus the bar it was measured against.
 */
export interface MetricValue {
  criteriaId: number;
  name: string;
  score: number;
  /** The UNIT'S OWN threshold, never a hardcoded constant. */
  threshold: number;
  maxScore: number;
  trendValue: number | null;
  weeklyValues: (string | boolean | null)[] | null;
  /**
   * True when the unit defines more than one criterion in this
   * category. The rule engine scores all of them; the ML model keeps
   * only the last; this cell can only show one. Surfaced as a warning
   * rather than silently picking a winner.
   */
  ambiguous: boolean;
}

/**
 * Every criterion a student has in one category, ordered by id.
 *
 * Ordering explicitly rather than trusting payload order means the cell
 * shows the same criterion on every render and after every refetch.
 */
function criteriaInCategory(
  student: DashboardStudent,
  category: string,
): DashboardCriterionScore[] {
  return student.criteria
    .filter((criterion) => criterion.category === category)
    .sort((a, b) => a.criteria_id - b.criteria_id);
}

/**
 * The student's value for a single-valued category (attendance or
 * weekly tutorials).
 *
 * Returns null when the student has no event for it. That is NOT the
 * same as zero and must never be rendered as "0%" — a student with no
 * attendance data uploaded yet has not attended zero classes, we simply
 * do not know.
 */
function singleMetric(
  student: DashboardStudent,
  category: string,
): MetricValue | null {
  const matches = criteriaInCategory(student, category);
  if (matches.length === 0) return null;

  const criterion = matches[0];
  return {
    criteriaId: criterion.criteria_id,
    name: criterion.name,
    score: criterion.score,
    threshold: criterion.threshold,
    maxScore: criterion.max_score,
    trendValue: criterion.trend_value,
    weeklyValues: criterion.weekly_values,
    ambiguous: matches.length > 1,
  };
}

/** Attendance percentage for one enrolment, or null if never recorded. */
export function attendanceOf(student: DashboardStudent): MetricValue | null {
  return singleMetric(student, "attendance");
}

/**
 * Weekly tutorial completion percentage, or null.
 *
 * The percentage remains the bar value; weekly_values lets the cell show
 * the more useful submitted/total headline when available.
 */
export function tutorialOf(student: DashboardStudent): MetricValue | null {
  return singleMetric(student, "weekly_tut");
}

export function completedWeeks(
  values: (string | boolean | null)[] | null,
): { done: number; total: number } | null {
  if (values === null) return null;
  return {
    done: values.filter((value) => value === true || value === "submitted" || value === "late").length,
    total: values.length,
  };
}

/* ------------------------------------------------------------------ */
/* Assessments                                                         */
/* ------------------------------------------------------------------ */

/** One assessment on the unit, and this student's mark for it if any. */
export interface AssessmentItem {
  criteriaId: number;
  name: string;
  /** null = no AssessmentEvent exists. NOT the same as a mark of zero. */
  score: number | null;
  maxScore: number;
}

export interface AssessmentProgress {
  /** Assessments this student has a recorded mark for. */
  marked: number;
  /** Assessments the UNIT defines. */
  total: number;
  /** Mean of the marked assessments as a percentage of max_score. */
  averagePercent: number | null;
  /** Per-assessment detail for the tooltip. */
  items: AssessmentItem[];
  /**
   * True when the unit's criteria list was unavailable, so `total` fell
   * back to `marked` and the ratio is not trustworthy. The cell renders
   * a plain count instead of "n of m" in that case.
   */
  totalUnknown: boolean;
  /** True when the unit criteria list was unavailable but marks exist. */
  unitTotalUnavailable: boolean;
}

/**
 * How many of a unit's assessments this student has been MARKED for.
 *
 * The word is "marked", not "submitted", and that is deliberate. In
 * `bulk_ingest` a blank cell creates no AssessmentEvent while a literal
 * `0` creates an event scored zero — so a lecturer who types 0 for a
 * no-show has that student counted here. Calling it "submitted" would
 * either overclaim, or force us to treat a mark of 0 as a
 * non-submission, which would make a genuine zero invisible in exactly
 * the row a lecturer most needs to see. The tooltip shows every
 * assessment with its real mark so the distinction stays visible.
 *
 * The denominator comes from the UNIT, because student.criteria omits
 * criteria the student has no event for.
 */
export function assessmentProgressOf(
  student: DashboardStudent,
  unit: DashboardUnit | undefined,
): AssessmentProgress {
  const marks = new Map<number, DashboardCriterionScore>();
  for (const criterion of criteriaInCategory(student, "assessment")) {
    marks.set(criterion.criteria_id, criterion);
  }

  const unitAssessments = (unit?.criteria ?? [])
    .filter((criterion) => criterion.category === "assessment")
    .sort((a, b) => a.id - b.id);

  // GET /lecturer/units returns units with no criteria, and a unit
  // could in principle be missing from the list entirely. Fall back to
  // what the student has rather than dividing by zero.
  const unitTotalUnavailable = unitAssessments.length === 0 && marks.size > 0;
  const totalUnknown = unitAssessments.length === 0 && marks.size === 0;

  const items: AssessmentItem[] = totalUnknown
    ? [...marks.values()].map((criterion) => ({
        criteriaId: criterion.criteria_id,
        name: criterion.name,
        score: criterion.score,
        maxScore: criterion.max_score,
      }))
    : unitAssessments.map((criterion) => {
        const mark = marks.get(criterion.id);
        return {
          criteriaId: criterion.id,
          name: criterion.name,
          score: mark ? mark.score : null,
          maxScore: criterion.max_score,
        };
      });

  // Percentages, because assessments are not all out of the same
  // max_score — a quiz out of 20 and an exam out of 100 cannot be
  // averaged raw. This is the same normalisation the rule engine had to
  // be fixed to perform in 7.4.
  const percentages = items
    .filter((item) => item.score !== null && item.maxScore > 0)
    .map((item) => (item.score! / item.maxScore) * 100);

  return {
    marked: marks.size,
    total: totalUnknown ? marks.size : unitAssessments.length,
    averagePercent:
      percentages.length > 0
        ? Math.round(percentages.reduce((sum, value) => sum + value, 0) / percentages.length)
        : null,
    items,
    totalUnknown,
    unitTotalUnavailable,
  };
}

/* ------------------------------------------------------------------ */
/* Trend                                                               */
/* ------------------------------------------------------------------ */

export type TrendBand = "improving" | "steady" | "declining";

/**
 * Which direction a trend value counts as.
 *
 * Banded at ±MOMENTUM_BAND_PP, imported rather than redefined so this
 * column and the dashboard's Momentum chart can never call the same
 * student "declining" in one place and "steady" in the other.
 */
export function trendBandOf(trendValue: number | null): TrendBand | null {
  if (trendValue === null) return null;
  if (trendValue <= -MOMENTUM_BAND_PP) return "declining";
  if (trendValue >= MOMENTUM_BAND_PP) return "improving";
  return "steady";
}

export const TREND_LABELS: Record<TrendBand, string> = {
  improving: "Improving",
  steady: "Steady",
  declining: "Deteriorating",
};

/**
 * The row's headline trend: attendance.
 *
 * Only attendance and weekly tutorials ever carry a trend_value —
 * assessments and Moodle are single figures with no early/late split.
 * Attendance drives the arrow because it sits in the adjacent column,
 * so the arrow reads as "that number is moving". The tutorial trend is
 * still surfaced, in the cell's tooltip, rather than averaged in:
 * averaging lets collapsing attendance and improving tutorials cancel
 * out to "steady" and hide the collapse.
 */
export function headlineTrendOf(student: DashboardStudent): number | null {
  return attendanceOf(student)?.trendValue ?? null;
}

/* ------------------------------------------------------------------ */
/* Filtering                                                           */
/* ------------------------------------------------------------------ */

/**
 * Free-text search across name, student number and unit code.
 *
 * Unit code is included because a lecturer looking at "all subjects"
 * often wants to narrow to one by typing it, and expecting them to
 * notice the separate dropdown is optimistic.
 */
export function searchStudents(
  students: DashboardStudent[],
  query: string,
): DashboardStudent[] {
  const needle = query.trim().toLowerCase();
  if (needle === "") return students;

  return students.filter(
    (student) =>
      student.name.toLowerCase().includes(needle) ||
      student.student_number.toLowerCase().includes(needle) ||
      student.unit_code.toLowerCase().includes(needle),
  );
}

/** Restricts to one unit. `null` means "all subjects". */
export function filterByUnit(
  students: DashboardStudent[],
  unitId: number | null,
): DashboardStudent[] {
  if (unitId === null) return students;
  return students.filter((student) => student.unit_id === unitId);
}

/** Restricts to one risk bucket. `null` means "all students". */
export function filterByBucket(
  students: DashboardStudent[],
  bucket: RiskBucket | null,
): DashboardStudent[] {
  if (bucket === null) return students;
  return students.filter((student) => getBucket(student) === bucket);
}

/**
 * Counts for the risk tabs, in fixed BUCKET_ORDER.
 *
 * Every bucket is returned even at zero, unlike the dashboard's donut
 * which drops empty slices. A tab that disappears when its count hits
 * zero makes the row of tabs jump around under the cursor, and a
 * lecturer cannot tell "no students need review" from "the Needs Review
 * tab was never there".
 */
export function countsByBucket(
  students: DashboardStudent[],
): Record<RiskBucket, number> {
  const counts = Object.fromEntries(
    BUCKET_ORDER.map((bucket) => [bucket, 0]),
  ) as Record<RiskBucket, number>;

  for (const student of students) counts[getBucket(student)] += 1;
  return counts;
}

/* ------------------------------------------------------------------ */
/* Sorting                                                             */
/* ------------------------------------------------------------------ */

export type SortKey =
  | "name"
  | "attendance"
  | "assessments"
  | "tutorial"
  | "risk"
  | "trend";
export type SortDirection = "asc" | "desc";

/**
 * Sort value for one row on one column.
 *
 * Missing data returns null, which the comparator always sorts LAST
 * regardless of direction. Treating "no data" as zero would park every
 * un-uploaded student at the top of an ascending attendance sort and
 * bury the students who genuinely have 30% attendance underneath them.
 */
function sortValue(
  student: DashboardStudent,
  key: SortKey,
  unitsById: Map<number, DashboardUnit>,
): number | string | null {
  switch (key) {
    case "name":
      return student.name.toLowerCase();
    case "attendance":
      return attendanceOf(student)?.score ?? null;
    case "tutorial":
      return tutorialOf(student)?.score ?? null;
    case "assessments": {
      const progress = assessmentProgressOf(student, unitsById.get(student.unit_id));
      // Ratio rather than raw count, so a student marked 1 of 1 is not
      // ranked below one marked 2 of 8.
      return progress.total > 0 ? progress.marked / progress.total : null;
    }
    case "risk":
      return SEVERITY_RANK[getBucket(student)];
    case "trend":
      return headlineTrendOf(student);
  }
}

/**
 * Sorts a copy. Never sorts in place — the array arrives from a
 * `useMemo` chain that other parts of the page also read, and `sort()`
 * mutates.
 */
export function sortStudents(
  students: DashboardStudent[],
  key: SortKey,
  direction: SortDirection,
  unitsById: Map<number, DashboardUnit>,
): DashboardStudent[] {
  const rows = [...students];
  const modifier = direction === "asc" ? 1 : -1;

  rows.sort((a, b) => {
    const left = sortValue(a, key, unitsById);
    const right = sortValue(b, key, unitsById);

    // Nulls sink to the bottom in BOTH directions.
    if (left === null && right === null) return a.name.localeCompare(b.name);
    if (left === null) return 1;
    if (right === null) return -1;

    let comparison: number;
    if (typeof left === "string" && typeof right === "string") {
      comparison = left.localeCompare(right);
    } else {
      comparison = (left as number) - (right as number);
    }

    // Name is the universal tiebreaker, so equal rows keep a stable,
    // predictable order instead of shuffling between renders.
    return comparison !== 0 ? comparison * modifier : a.name.localeCompare(b.name);
  });

  return rows;
}

/* ------------------------------------------------------------------ */
/* Pagination                                                          */
/* ------------------------------------------------------------------ */

/** Total pages for a row count. Always at least 1, so "Page 1 of 0" is impossible. */
export function pageCount(totalRows: number, pageSize = PAGE_SIZE): number {
  return Math.max(1, Math.ceil(totalRows / pageSize));
}

/** The slice of rows shown on a 1-indexed page. */
export function pageSlice<T>(rows: T[], page: number, pageSize = PAGE_SIZE): T[] {
  const start = (page - 1) * pageSize;
  return rows.slice(start, start + pageSize);
}

/**
 * The page buttons to render: numbers, with "…" where a run is elided.
 *
 * Always shows the first page, the last page, and a window around the
 * current one, so the control stays a fixed width whether the lecturer
 * has 3 pages or 40.
 */
export function pageItems(
  current: number,
  total: number,
  windowSize = 1,
): (number | "ellipsis")[] {
  if (total <= 7) {
    return Array.from({ length: total }, (_, index) => index + 1);
  }

  const pages = new Set<number>([1, total]);
  for (let page = current - windowSize; page <= current + windowSize; page += 1) {
    if (page > 1 && page < total) pages.add(page);
  }

  const ordered = [...pages].sort((a, b) => a - b);
  const items: (number | "ellipsis")[] = [];

  for (let index = 0; index < ordered.length; index += 1) {
    if (index > 0 && ordered[index] - ordered[index - 1] > 1) items.push("ellipsis");
    items.push(ordered[index]);
  }

  return items;
}

/* ------------------------------------------------------------------ */
/* CSV export                                                          */
/* ------------------------------------------------------------------ */

/**
 * Escapes one CSV field.
 *
 * Quotes everything rather than only fields that need it. Student names
 * and program names routinely contain commas ("Bachelor of IT, Cyber
 * Security") and apostrophes, and a single unquoted comma silently
 * shifts every later column into the wrong header — a corruption that
 * looks like real data when opened in Excel. Internal quotes are
 * doubled, per RFC 4180.
 */
function csvField(value: string | number | null): string {
  if (value === null) return '""';
  return `"${String(value).replace(/"/g, '""')}"`;
}

const CSV_HEADERS = [
  "Student name",
  "Student ID",
  "Unit",
  "Attendance %",
  "Attendance threshold",
  "Attendance trend (pp)",
  "Assessments marked",
  "Assessments on unit",
  "Assessment average %",
  "Weekly tutorial %",
  "Tutorial trend (pp)",
  "Risk level",
  "Rule engine",
  "ML model",
  "Incomplete data",
];

/**
 * Serialises the CURRENTLY FILTERED rows — not just the visible page.
 *
 * Exporting one page of eight would be a trap: the file looks complete,
 * and the lecturer emails it to a student support team missing 90% of
 * the cohort. The button label says "filtered" for the same reason.
 *
 * Missing values are written as empty cells rather than 0. A zero in a
 * spreadsheet is a fact; an empty cell is honestly nothing.
 */
export function toCsv(
  students: DashboardStudent[],
  unitsById: Map<number, DashboardUnit>,
): string {
  const lines = [CSV_HEADERS.map(csvField).join(",")];

  for (const student of students) {
    const attendance = attendanceOf(student);
    const tutorial = tutorialOf(student);
    const assessments = assessmentProgressOf(student, unitsById.get(student.unit_id));

    lines.push(
      [
        csvField(student.name),
        csvField(student.student_number),
        csvField(student.unit_code),
        csvField(attendance ? Math.round(attendance.score) : null),
        csvField(attendance ? attendance.threshold : null),
        csvField(attendance?.trendValue ?? null),
        csvField(assessments.marked),
        csvField(assessments.totalUnknown ? null : assessments.total),
        csvField(assessments.averagePercent),
        csvField(tutorial ? Math.round(tutorial.score) : null),
        csvField(tutorial?.trendValue ?? null),
        csvField(BUCKET_LABELS[getBucket(student)]),
        csvField(student.rule_tier ? BUCKET_LABELS[student.rule_tier] : null),
        csvField(student.ml_tier ? BUCKET_LABELS[student.ml_tier] : null),
        csvField(student.is_incomplete ? "Yes" : "No"),
      ].join(","),
    );
  }

  // CRLF per RFC 4180 — Excel on Windows is the likeliest destination.
  return lines.join("\r\n");
}

/**
 * Filename for the export, stamped so two downloads never collide in
 * the Downloads folder and so the file is self-describing weeks later.
 */
export function csvFilename(unitCode: string | null): string {
  const date = new Date().toISOString().slice(0, 10);
  return `eduguard-students-${unitCode ? `${unitCode}-` : ""}${date}.csv`;
}

/**
 * Triggers a browser download of a CSV string.
 *
 * Uses a Blob and an object URL rather than a data: URI — data URIs are
 * length-capped in some browsers, and a 300-row export would silently
 * truncate. The object URL is revoked immediately after the click so
 * the blob does not leak for the lifetime of the tab.
 */
export function downloadCsv(csv: string, filename: string): void {
  // A UTF-8 BOM, so Excel renders non-ASCII names correctly instead of
  // showing mojibake. Every other tool ignores it.
  const blob = new Blob([`﻿${csv}`], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);

  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);

  URL.revokeObjectURL(url);
}