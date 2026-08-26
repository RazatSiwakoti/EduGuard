import { TriangleAlert } from "lucide-react";
import type { MetricValue } from "../../utils/studentsTable";

interface MetricCellProps {
  value: MetricValue | null;
  /** What this measures, for the tooltip: "Attendance", "Weekly tutorials". */
  label: string;
  /** Extra tooltip line, e.g. the tutorial column's "W2–W7 completion". */
  hint?: string;
}

/**
 * How far above the threshold still counts as "only just passing".
 *
 * A student sitting one point above the bar is not safe, they are about
 * to fall through it. Ten percentage points matches the momentum band
 * used everywhere else on this page.
 */
const NEAR_THRESHOLD_PP = 10;

type Standing = "below" | "near" | "clear";

function standingOf(score: number, threshold: number): Standing {
  if (score < threshold) return "below";
  if (score < threshold + NEAR_THRESHOLD_PP) return "near";
  return "clear";
}

/**
 * Text and bar colours per standing.
 *
 * "clear" is deliberately NOT green. If every healthy row glows green
 * the page becomes a wall of colour and the genuinely red rows stop
 * standing out — the whole job of this table is making six bad rows
 * findable among two hundred. Healthy reads as ordinary text.
 */
const STANDING_STYLES: Record<Standing, { text: string; bar: string }> = {
  below: { text: "text-red-600", bar: "bg-red-500" },
  near: { text: "text-amber-700", bar: "bg-amber-500" },
  clear: { text: "text-stone-800", bar: "bg-stone-400" },
};

/**
 * A percentage with a bar showing it against the unit's own threshold.
 *
 * THE THRESHOLD IS PER UNIT AND READ FROM THE DATA. Never hardcode 80
 * here: `seed_default_criteria()` copies the constant into the criteria
 * row at unit-creation time, so units created before the constant
 * changed still carry the old value, and two units can legitimately
 * hold their students to different bars.
 *
 * No data renders as an em dash, never "0%". A student with nothing
 * uploaded has not attended zero classes — we simply do not know, and
 * showing 0% would invent a fact and mark them red for it.
 */
export default function MetricCell({ value, label, hint }: MetricCellProps) {
  if (value === null) {
    return (
      <span className="text-stone-400" title={`No ${label.toLowerCase()} data recorded`}>
        —
      </span>
    );
  }

  const standing = standingOf(value.score, value.threshold);
  const style = STANDING_STYLES[standing];
  const rounded = Math.round(value.score);

  // Percentages can exceed 100 through a data-entry error; clamping the
  // bar keeps it inside its track rather than overflowing the cell.
  const barWidth = Math.max(0, Math.min(100, value.score));

  const tooltip = [
    `${label}: ${rounded}%`,
    `Threshold for this unit: ${Math.round(value.threshold)}%`,
    hint,
    value.ambiguous
      ? "This unit defines more than one criterion in this category — only the first is shown here."
      : undefined,
  ]
    .filter(Boolean)
    .join("\n");

  return (
    <div className="w-24" title={tooltip}>
      <div className="flex items-center gap-1">
        <span className={`text-sm font-medium tabular-nums ${style.text}`}>
          {rounded}%
        </span>

        {/* Icon, not colour alone. The amber and red bands sit close
            enough in greyscale that a printout or a colour-vision
            deficiency would otherwise lose the distinction. */}
        {standing === "below" && (
          <TriangleAlert className="h-3.5 w-3.5 shrink-0 text-red-500" aria-hidden="true" />
        )}

        {value.ambiguous && (
          <span className="shrink-0 text-xs font-bold text-amber-500" aria-hidden="true">
            *
          </span>
        )}
      </div>

      {/* The bar is decoration for the number above it, which is why it
          is hidden from assistive tech rather than duplicated there. */}
      <div className="mt-1 h-1 w-full overflow-hidden rounded-full bg-stone-100" aria-hidden="true">
        <div className={`h-full rounded-full ${style.bar}`} style={{ width: `${barWidth}%` }} />
      </div>

      <span className="sr-only">
        {label} {rounded} percent, against a threshold of {Math.round(value.threshold)} percent
        {standing === "below" ? ", below threshold" : ""}
      </span>
    </div>
  );
}