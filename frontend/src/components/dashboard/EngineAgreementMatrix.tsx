import type { AgreementMatrix } from "../../utils/dashboardAggregations";
import { BUCKET_LABELS, TIER_ORDER } from "../../utils/dashboardAggregations";
import ChartCard from "./ChartCard";
import { sequentialStep, sequentialTextClass } from "./chartTheme";

interface EngineAgreementMatrixProps {
  matrix: AgreementMatrix;
}

/**
 * Where the rule engine and the ML model agreed — and where they didn't.
 *
 * This visual is specific to EduGuard's hybrid architecture. Two
 * independent engines score every student, and a third layer reconciles
 * them. That reconciliation is invisible everywhere else in the product:
 * a lecturer sees only the final tier, never the argument behind it.
 * This matrix is the argument.
 *
 * Reading it: the DIAGONAL is agreement. Anything off the diagonal is a
 * case the hybrid layer had to settle. The two extreme corners
 * (rule says safe / ML says high risk, and the reverse) are the pairs
 * the engine refuses to auto-resolve — those become the "Needs Review"
 * queue, so a heavy corner directly explains a large review backlog.
 *
 * Built with CSS grid rather than a charting library: a 3×3 grid of
 * numbers needs no axes, no scales and no SVG. Reaching for a chart
 * component here would add a dependency's worth of machinery to render
 * nine divs.
 *
 * Colour is a single-hue sequential ramp — the correct encoding for
 * continuous magnitude — and it is strictly redundant: every cell
 * prints its own count, so the shading only speeds up scanning and
 * never carries information by itself.
 */
export default function EngineAgreementMatrix({ matrix }: EngineAgreementMatrixProps) {
  return (
    <ChartCard
      title="Rule Engine vs ML Model"
      subtitle="Where your two engines agreed. Off-diagonal cells are the cases the hybrid layer had to reconcile."
      empty={matrix.total === 0}
      emptyMessage="No students have been scored by both engines yet."
      action={
        <div className="text-right">
          <span className="block text-lg font-semibold leading-none text-stone-900">
            {matrix.agreementPercent}%
          </span>
          <span className="text-xs text-stone-500">engines agreed</span>
        </div>
      }
    >
      <div className="overflow-x-auto">
        <div className="min-w-[360px]">
          {/* Column header: what the ML model said. */}
          <div className="mb-1 grid grid-cols-[92px_repeat(3,1fr)] gap-1">
            <div />
            {TIER_ORDER.map((tier) => (
              <div
                key={tier}
                className="pb-1 text-center text-[11px] font-medium text-stone-500"
              >
                {BUCKET_LABELS[tier]}
              </div>
            ))}
          </div>

          {/* One row per rule-engine tier. */}
          {TIER_ORDER.map((ruleTier) => (
            <div
              key={ruleTier}
              className="mb-1 grid grid-cols-[92px_repeat(3,1fr)] items-center gap-1"
            >
              <div className="pr-2 text-right text-[11px] font-medium text-stone-500">
                {BUCKET_LABELS[ruleTier]}
              </div>

              {TIER_ORDER.map((mlTier) => {
                const cell = matrix.cells.find(
                  (c) => c.ruleTier === ruleTier && c.mlTier === mlTier,
                );
                const count = cell?.count ?? 0;
                const background = sequentialStep(count, matrix.maxCount);

                return (
                  <div
                    key={mlTier}
                    // Zero cells render as bare surface with a hairline
                    // rather than as the palest ramp step — "nothing
                    // here" should recede, not read as a small value.
                    className={`flex h-14 items-center justify-center rounded-md text-sm font-semibold tabular-nums ${
                      background ? "" : "border border-dashed border-stone-200"
                    } ${sequentialTextClass(count, matrix.maxCount)} ${
                      cell?.agreed ? "ring-1 ring-inset ring-stone-900/15" : ""
                    }`}
                    style={background ? { backgroundColor: background } : undefined}
                    title={`Rule engine: ${BUCKET_LABELS[ruleTier]} · ML model: ${
                      BUCKET_LABELS[mlTier]
                    } — ${count} student${count === 1 ? "" : "s"}${
                      cell?.agreed ? " (agreement)" : " (reconciled by hybrid engine)"
                    }`}
                  >
                    {count}
                  </div>
                );
              })}
            </div>
          ))}

          {/* Axis captions. Without these the reader cannot tell which
              direction is which, and the matrix becomes unreadable. */}
          <div className="mt-2 flex items-center justify-between text-[11px] text-stone-400">
            <span>Rows: rule engine verdict</span>
            <span>Columns: ML model verdict</span>
          </div>
        </div>
      </div>

      <p className="mt-3 text-xs leading-relaxed text-stone-500">
        {matrix.agreedCount} of {matrix.total} scored students landed in the same tier
        on both engines. Disagreements between <strong>Safe</strong> and{" "}
        <strong>High Risk</strong> are never auto-resolved — they go to your review
        queue.
      </p>
    </ChartCard>
  );
}