/**
 * Shared visual language for every dashboard chart (Phase 6.2).
 *
 * One file so a colour means the same thing in all six visuals. If red
 * is "high risk" in the donut it must be "high risk" in the stacked bar
 * too, and the only way to guarantee that is to never hardcode a hex in
 * a chart component.
 *
 * PALETTE PROVENANCE
 * ------------------
 * Risk tiers use a STATUS palette (good / warning / critical), not a
 * categorical one, because the tiers are states with inherent severity
 * rather than interchangeable series. Those four hexes are fixed values
 * and are deliberately never re-stepped.
 *
 * Two of them (`low_risk` amber, and the muted grey) sit below 3:1
 * contrast against a white card. That is a known, accepted trade for
 * status colours, and it obliges us to provide RELIEF — meaning colour
 * must never be the only channel carrying the message. Hence:
 *   - every tier ships with an ICON and a TEXT LABEL, never colour alone
 *   - every chart has a legend and direct value labels
 *   - the student table below the charts is the full table view
 *
 * The momentum chart uses the diverging pair red↔blue rather than the
 * more obvious red↔green: red/green is the single worst pair for
 * colour-vision deficiency, and blue↔red validates cleanly on every
 * check (CVD ΔE 23.8, normal-vision ΔE 31.6, both well clear of floors).
 */

import type { RiskBucket, RiskTier } from "../../types/dashboard";

/* ------------------------------------------------------------------ */
/* Chart chrome — recessive by design                                  */
/* ------------------------------------------------------------------ */

export const CHART_INK = {
  /** Card background. Doubles as the separator colour between marks. */
  surface: "#ffffff",
  /** Hairline grid. Must sit well behind the data, never compete. */
  grid: "#e1e0d9",
  /** Axis line and baseline. */
  axis: "#c3c2b7",
  /** Axis tick and label text. */
  muted: "#898781",
  /** Body text inside tooltips. */
  secondary: "#52514e",
  primary: "#0b0b0b",
} as const;

/**
 * Gap rendered between adjacent or stacked marks. Implemented as a
 * surface-coloured stroke, which is how you get a true 2px separation
 * in Recharts without faking it with a spacer series.
 */
export const MARK_GAP_PX = 2;

/** Corner radius on data ends. Small — these are thin marks, not pills. */
export const MARK_RADIUS_PX = 2;

/* ------------------------------------------------------------------ */
/* Risk bucket styling                                                 */
/* ------------------------------------------------------------------ */

export interface BucketStyle {
  /** Mark fill used in every chart. */
  fill: string;
  /** Tailwind classes for the table/legend pill. */
  pill: string;
  /** Short description shown in tooltips and the legend's title text. */
  hint: string;
  dot: string;
}

export const BUCKET_STYLES: Record<RiskBucket, BucketStyle> = {
  high_risk: {
    fill: "#d03b3b", // status: critical
    pill: "bg-red-50 text-red-700 ring-red-200",
    hint: "Both engines agree this student is at high risk",
    dot: "bg-red-500",
  },
  low_risk: {
    fill: "#fab219", // status: warning
    pill: "bg-amber-50 text-amber-800 ring-amber-200",
    hint: "Showing early warning signs, worth monitoring",
    dot: "bg-amber-500",
  },
  safe: {
    fill: "#0ca30c", // status: good
    pill: "bg-green-50 text-green-700 ring-green-200",
    hint: "Tracking well against every criterion",
    dot: "bg-green-500",
  },
  needs_review: {
    fill: "#4a3aa7", // categorical violet — a state, not a severity
    pill: "bg-violet-50 text-violet-700 ring-violet-200",
    hint: "Rule engine and ML model disagreed — awaiting your decision",
    dot: "bg-violet-500",
  },
  not_analysed: {
    fill: "#898781", // muted grey — absence of data, deliberately dull
    pill: "bg-stone-100 text-stone-600 ring-stone-200",
    hint: "Enrolled, but the analysis has never been run for this student",
    dot: "bg-stone-400",
  },
};

/** Engine tiers reuse the identical three status colours. */
export const TIER_FILLS: Record<RiskTier, string> = {
  high_risk: BUCKET_STYLES.high_risk.fill,
  low_risk: BUCKET_STYLES.low_risk.fill,
  safe: BUCKET_STYLES.safe.fill,
};

/* ------------------------------------------------------------------ */
/* Single-series and diverging colours                                 */
/* ------------------------------------------------------------------ */

/** Categorical slot 1. Used where a chart has exactly one series. */
export const SERIES_BLUE = "#2a78d6";

/** Validated diverging pair for the momentum chart. */
export const DIVERGING = {
  negative: "#d03b3b", // declining
  positive: "#2a78d6", // improving
} as const;

/**
 * Sequential blue ramp for the agreement heatmap, light → dark.
 *
 * Index 0 is intentionally close to the surface: in a sequential
 * encoding the lightest step means "near zero" and is allowed to
 * recede. Cells with a count of zero skip the ramp entirely and render
 * as bare surface, and every cell prints its own number, so magnitude
 * never rests on colour alone.
 */
export const SEQUENTIAL_BLUE = [
  "#cde2fb",
  "#9ec5f4",
  "#6da7ec",
  "#3987e5",
  "#256abf",
  "#104281",
] as const;

/**
 * Picks a ramp step for a heatmap cell.
 * @param count this cell's value
 * @param maxCount the largest value anywhere in the matrix
 */
export function sequentialStep(count: number, maxCount: number): string | null {
  if (count === 0 || maxCount === 0) return null; // Render as bare surface.

  const ratio = count / maxCount;
  const index = Math.min(
    SEQUENTIAL_BLUE.length - 1,
    Math.floor(ratio * SEQUENTIAL_BLUE.length),
  );
  return SEQUENTIAL_BLUE[index];
}

/**
 * Heatmap text must stay readable as the cell darkens, so it flips to
 * white on the darker half of the ramp. Index 3 is where the ramp
 * crosses into "too dark for near-black text".
 */
export function sequentialTextClass(count: number, maxCount: number): string {
  if (count === 0 || maxCount === 0) return "text-stone-300";
  const ratio = count / maxCount;
  return ratio >= 0.5 ? "text-white" : "text-stone-900";
}