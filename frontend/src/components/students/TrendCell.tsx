import { Minus, TrendingDown, TrendingUp } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { MOMENTUM_BAND_PP } from "../../utils/dashboardAggregations";
import { TREND_LABELS, trendBandOf } from "../../utils/studentsTable";
import type { TrendBand } from "../../utils/studentsTable";

interface TrendCellProps {
  /** Attendance momentum in percentage points. Drives the arrow. */
  attendanceTrend: number | null;
  /** Tutorial momentum. Shown in the tooltip only — never averaged in. */
  tutorialTrend: number | null;
}

const TREND_ICONS: Record<TrendBand, LucideIcon> = {
  improving: TrendingUp,
  steady: Minus,
  declining: TrendingDown,
};

/**
 * Red ↔ blue, never red ↔ green.
 *
 * Red/green is the single worst pair for colour-vision deficiency, and
 * this is the same diverging pair the dashboard's Momentum chart uses
 * (validated at CVD ΔE 23.8). Every state also ships an arrow shape and
 * a written word, so the colour is the third channel, not the only one.
 */
const TREND_STYLES: Record<TrendBand, string> = {
  improving: "text-blue-600",
  steady: "text-stone-500",
  declining: "text-red-600",
};

/** Signed percentage points, so "+12pp" and "−8pp" read unambiguously. */
function formatPp(value: number): string {
  const rounded = Math.round(value);
  return `${rounded > 0 ? "+" : ""}${rounded}pp`;
}

/**
 * Which way this student is moving.
 *
 * Driven by ATTENDANCE alone, on purpose. Only attendance and weekly
 * tutorials carry a `trend_value` at all — assessments and Moodle are
 * single figures with no early/late window to compare. Attendance wins
 * because it sits in a neighbouring column, so the arrow reads as "that
 * number is moving".
 *
 * The tutorial trend is surfaced in the tooltip rather than averaged
 * into the arrow. Averaging would let collapsing attendance and
 * improving tutorials cancel out to "steady" — hiding exactly the
 * collapse this page exists to surface.
 *
 * Banded at MOMENTUM_BAND_PP, imported rather than redefined, so this
 * column can never call a student "declining" while the dashboard's
 * Momentum chart calls the same student "steady".
 */
export default function TrendCell({ attendanceTrend, tutorialTrend }: TrendCellProps) {
  const band = trendBandOf(attendanceTrend);

  const tutorialBand = trendBandOf(tutorialTrend);
  const tutorialLine =
    tutorialBand !== null && tutorialTrend !== null
      ? `Weekly tutorials: ${TREND_LABELS[tutorialBand].toLowerCase()} (${formatPp(tutorialTrend)})`
      : "Weekly tutorials: no trend recorded";

  if (band === null || attendanceTrend === null) {
    return (
      <span
        className="text-stone-400"
        title={`No attendance trend recorded.\n${tutorialLine}\n\nA trend needs all 7 weekly attendance values; a short column returns no trend rather than an error.`}
      >
        —
      </span>
    );
  }

  const Icon = TREND_ICONS[band];

  const tooltip = [
    `Attendance: ${TREND_LABELS[band].toLowerCase()} (${formatPp(attendanceTrend)})`,
    tutorialLine,
    "",
    `Late-window average minus early-window average. Movement within ±${MOMENTUM_BAND_PP}pp counts as steady.`,
  ].join("\n");

  return (
    <span
      className={`inline-flex items-center gap-1.5 text-xs font-medium ${TREND_STYLES[band]}`}
      title={tooltip}
    >
      <Icon className="h-4 w-4 shrink-0" aria-hidden="true" />
      {TREND_LABELS[band]}
    </span>
  );
}