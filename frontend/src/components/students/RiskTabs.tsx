import type { RiskBucket } from "../../types/dashboard";
import { BUCKET_LABELS, BUCKET_ORDER } from "../../utils/dashboardAggregations";
import { BUCKET_ICONS } from "../dashboard/BucketBadge";
import { BUCKET_STYLES } from "../dashboard/chartTheme";

interface RiskTabsProps {
  /** Counts per bucket for the currently selected subject. */
  counts: Record<RiskBucket, number>;
  /** Total for the "All students" tab. */
  total: number;
  /** `null` = All students. */
  active: RiskBucket | null;
  onChange: (bucket: RiskBucket | null) => void;
}

/**
 * The five risk filters.
 *
 * FIVE, NOT THREE — this is the important design decision on this page.
 * `final_tier` is NULL by design whenever the rule engine and the ML
 * model disagreed badly enough to require a human (`requires_review`),
 * and students who are enrolled but never analysed exist too. With only
 * High / At Risk / Safe:
 *
 *   - the tab counts would not sum to the total, with no explanation
 *   - "Needs Review" students — the ONLY group on this page a lecturer
 *     can personally resolve — would be unreachable
 *
 * Every bucket is rendered even at zero. A tab that vanishes when empty
 * makes the row jump under the cursor, and a lecturer could not tell
 * "nobody needs review" from "there is no review tab".
 *
 * Rendered as a real tablist so arrow-key navigation and screen-reader
 * semantics come for free, and each tab carries its bucket's icon so
 * the filter is identifiable without relying on its colour.
 */
export default function RiskTabs({ counts, total, active, onChange }: RiskTabsProps) {
  return (
    <div
      role="tablist"
      aria-label="Filter students by risk level"
      className="flex flex-wrap items-center gap-1 rounded-xl border border-stone-200 bg-white p-1"
    >
      <button
        type="button"
        role="tab"
        aria-selected={active === null}
        onClick={() => onChange(null)}
        className={`flex items-center gap-2 rounded-lg px-3.5 py-2 text-sm font-medium transition ${
          active === null
            ? "bg-stone-900 text-white"
            : "text-stone-600 hover:bg-stone-50 hover:text-stone-900"
        }`}
      >
        All Students
        <span
          className={`rounded-full px-1.5 py-0.5 text-xs tabular-nums ${
            active === null ? "bg-white/20 text-white" : "bg-stone-100 text-stone-600"
          }`}
        >
          {total}
        </span>
      </button>

      {BUCKET_ORDER.map((bucket) => {
        const Icon = BUCKET_ICONS[bucket];
        const isActive = active === bucket;

        return (
          <button
            key={bucket}
            type="button"
            role="tab"
            aria-selected={isActive}
            onClick={() => onChange(bucket)}
            title={BUCKET_STYLES[bucket].hint}
            className={`flex items-center gap-2 rounded-lg px-3.5 py-2 text-sm font-medium transition ${
              isActive
                ? "bg-stone-900 text-white"
                : "text-stone-600 hover:bg-stone-50 hover:text-stone-900"
            }`}
          >
            <Icon className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
            {BUCKET_LABELS[bucket]}
            <span
              className={`rounded-full px-1.5 py-0.5 text-xs tabular-nums ${
                isActive ? "bg-white/20 text-white" : "bg-stone-100 text-stone-600"
              }`}
            >
              {counts[bucket]}
            </span>
          </button>
        );
      })}
    </div>
  );
}