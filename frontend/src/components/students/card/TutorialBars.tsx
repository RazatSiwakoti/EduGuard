import {
  TUTORIAL_CREDIT,
  TUTORIAL_FIRST_WEEK,
  TUTORIAL_LABELS,
} from "../../../utils/studentCard";
import type { TutorialStatus } from "../../../types/studentDetail";

interface TutorialBarsProps {
  /** One status per week, W2 first. `null` = never recorded. */
  weeks: TutorialStatus[] | null;
}

/**
 * Bar height per status, mirroring TUTORIAL_STATUS_CREDIT: submitted
 * earns full credit, late earns 0.8, not submitted earns nothing.
 *
 * A "late" bar is 80% tall AND visually distinct — a hatched amber
 * rather than a slightly shorter green. Height alone would make late
 * and submitted near-indistinguishable at this size, and the difference
 * between them is the whole point of tracking three statuses instead of
 * two.
 */
const STATUS_STYLES: Record<TutorialStatus, { bar: string; label: string }> = {
  submitted: { bar: "bg-green-500", label: "text-green-700" },
  late: { bar: "bg-amber-400", label: "text-amber-700" },
  not_submitted: { bar: "bg-red-400", label: "text-red-600" },
};

/**
 * Week-by-week tutorial submissions.
 *
 * A BAR CHART here, where attendance gets a strip, because the data is
 * genuinely three-valued rather than binary — height carries real
 * meaning. Weeks run 2–7: week 1 has no tutorial, which is why six
 * values and not seven.
 *
 * A not-submitted week still renders a short stub rather than nothing.
 * An absent bar reads as "no data for this week"; a stub reads as
 * "this week happened and nothing was handed in", which is what it is.
 */
export default function TutorialBars({ weeks }: TutorialBarsProps) {
  if (weeks === null) {
    return (
      <p className="rounded-lg border border-dashed border-stone-300 bg-stone-50 px-3 py-2.5 text-xs leading-relaxed text-stone-500">
        Week-by-week tutorial submissions weren't recorded for this upload. Only the
        overall completion percentage and its trend were kept.
      </p>
    );
  }

  const submitted = weeks.filter((status) => status === "submitted").length;
  const late = weeks.filter((status) => status === "late").length;

  return (
    <div>
      <div className="flex items-end gap-2">
        {weeks.map((status, index) => {
          const week = TUTORIAL_FIRST_WEEK + index;
          const style = STATUS_STYLES[status];
          const heightPercent = Math.max(12, TUTORIAL_CREDIT[status] * 100);

          return (
            <div
              key={week}
              className="flex flex-1 flex-col items-center gap-1"
              title={`Week ${week}: ${TUTORIAL_LABELS[status].toLowerCase()}`}
            >
              <div className="flex h-16 w-full items-end justify-center">
                <div
                  className={`w-full rounded-t ${style.bar}`}
                  style={{ height: `${heightPercent}%` }}
                />
              </div>
              <span className="text-[10px] tabular-nums text-stone-400">W{week}</span>
            </div>
          );
        })}
      </div>

      <div className="mt-2.5 flex flex-wrap items-center gap-x-4 gap-y-1 text-[11px]">
        {(Object.keys(STATUS_STYLES) as TutorialStatus[]).map((status) => (
          <span key={status} className="inline-flex items-center gap-1.5 text-stone-500">
            <span
              className={`h-2 w-2 rounded-sm ${STATUS_STYLES[status].bar}`}
              aria-hidden="true"
            />
            {TUTORIAL_LABELS[status]}
          </span>
        ))}
      </div>

      <p className="mt-2 text-xs text-stone-500">
        <span className="font-medium tabular-nums text-stone-700">{submitted}</span>{" "}
        submitted on time
        {late > 0 && (
          <>
            ,{" "}
            <span className="font-medium tabular-nums text-amber-700">{late}</span> late
          </>
        )}
        , of {weeks.length} tutorials.
      </p>

      <span className="sr-only">
        Weekly tutorials:{" "}
        {weeks
          .map(
            (status, index) =>
              `week ${TUTORIAL_FIRST_WEEK + index} ${TUTORIAL_LABELS[status].toLowerCase()}`,
          )
          .join(", ")}
        .
      </span>
    </div>
  );
}
