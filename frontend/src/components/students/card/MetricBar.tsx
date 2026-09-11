import { TriangleAlert } from "lucide-react";

interface MetricBarProps {
  label: string;
  /** null = no data recorded. Rendered as "Not recorded", never as 0. */
  value: number | null;
  /** The unit's own threshold for this criterion. */
  threshold: number;
  /** Scale the bar is drawn against — 100 for a percentage, or max_score. */
  scaleMax: number;
  /** Suffix on the number: "%" for percentages, "" for a login count. */
  suffix?: string;
  /** Extra context under the label, e.g. "W2–W7 completion". */
  hint?: string;
  /**
   * The untouched figure, shown beside the normalised one.
   *
   * An assessment is normalised to a percentage before it can be
   * compared with its threshold (see assessmentPercent), but "20%" on
   * its own hides the mark the lecturer actually entered. This puts
   * "4 / 20" back on screen next to it.
   */
  rawLabel?: string;
}

/**
 * One performance metric with its bar and threshold marker.
 *
 * THE THRESHOLD MARKER IS THE POINT. A bare percentage tells a lecturer
 * nothing without the bar the student was actually held to, and that
 * bar is per unit — `seed_default_criteria()` copies the constant into
 * the criteria row at unit-creation time, so two units legitimately
 * hold students to different thresholds, and an older unit still holds
 * the value the constant had when it was created. Hardcoding a number
 * here would show the wrong line on half the cohort.
 *
 * "Not recorded" is not zero. A student with no attendance data has not
 * attended zero classes — nobody has measured them — and rendering 0%
 * would invent a fact and then flag them red for it.
 */
export default function MetricBar({
  label,
  value,
  threshold,
  scaleMax,
  suffix = "%",
  hint,
  rawLabel,
}: MetricBarProps) {
  const hasValue = value !== null;
  const below = hasValue && value < threshold;

  const valuePercent = hasValue ? Math.max(0, Math.min(100, (value / scaleMax) * 100)) : 0;
  const thresholdPercent = Math.max(0, Math.min(100, (threshold / scaleMax) * 100));

  return (
    <div>
      <div className="flex items-baseline justify-between gap-3">
        <div className="min-w-0">
          <p className="truncate text-sm font-medium text-stone-700">{label}</p>
          {hint && <p className="text-[11px] text-stone-400">{hint}</p>}
        </div>

        <div className="flex shrink-0 items-center gap-1.5">
          {hasValue ? (
            <>
              {rawLabel && (
                <span className="text-xs tabular-nums text-stone-400">{rawLabel}</span>
              )}
              <span
                className={`text-sm font-semibold tabular-nums ${
                  below ? "text-red-600" : "text-stone-800"
                }`}
              >
                {Math.round(value)}
                {suffix}
              </span>

              {below && (
                <span className="inline-flex items-center gap-1 text-xs font-medium text-red-600">
                  <TriangleAlert className="h-3.5 w-3.5" aria-hidden="true" />
                  Below threshold
                </span>
              )}
            </>
          ) : (
            <span className="text-sm text-stone-400">Not recorded</span>
          )}
        </div>
      </div>

      <div className="relative mt-1.5 h-2 w-full overflow-hidden rounded-full bg-stone-100">
        {hasValue && (
          <div
            className={`h-full rounded-full ${below ? "bg-red-500" : "bg-stone-400"}`}
            style={{ width: `${valuePercent}%` }}
          />
        )}

        <div
          className="absolute inset-y-0 w-0.5 bg-stone-600"
          style={{ left: `${thresholdPercent}%` }}
          aria-hidden="true"
          title={`Threshold: ${Math.round(threshold)}${suffix}`}
        />
      </div>

      <p className="mt-1 text-[11px] text-stone-400">
        Threshold for this unit: {Math.round(threshold)}
        {suffix}
      </p>
    </div>
  );
}
