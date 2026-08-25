import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";
import type { RiskBucket } from "../../types/dashboard";
import type { BucketSlice } from "../../utils/dashboardAggregations";
import BucketBadge from "./BucketBadge";
import ChartCard from "./ChartCard";
import { BUCKET_STYLES, CHART_INK, MARK_GAP_PX } from "./chartTheme";
import { pluralStudents, toNumber, toText, tooltipContentStyle } from "./tooltipFormat";

interface RiskDistributionDonutProps {
  slices: BucketSlice[];
  activeBucket: RiskBucket | null;
  onSelect: (bucket: RiskBucket | null) => void;
}

/**
 * How the cohort splits across risk buckets.
 *
 * A donut is defensible here specifically because this is a
 * part-to-whole breakdown of ONE cohort into a handful of mutually
 * exclusive states — the narrow case where a circular form actually
 * works. It does not attempt to compare across categories, which is
 * where pie charts normally fall apart.
 *
 * The ring carries shape; the legend beside it carries the real
 * numbers. Nobody has to estimate an angle to read a value, and every
 * segment is named in text — so the chart survives greyscale printing
 * and colour-vision deficiency intact.
 *
 * Clicking a segment or a legend row filters the ENTIRE dashboard to
 * that bucket. Clicking the active one again clears it.
 */
export default function RiskDistributionDonut({
  slices,
  activeBucket,
  onSelect,
}: RiskDistributionDonutProps) {
  const total = slices.reduce((sum, slice) => sum + slice.count, 0);

  // Index-based lookup rather than reading Recharts' event payload —
  // the index maps straight back into our own typed array, so there is
  // no untyped chart data leaking into application logic.
  const handleSliceClick = (_data: unknown, index: number) => {
    const slice = slices[index];
    if (!slice) return;
    onSelect(activeBucket === slice.bucket ? null : slice.bucket);
  };

  return (
    <ChartCard
      title="Risk Distribution"
      subtitle="Every student in view, split by their final verdict"
      empty={total === 0}
      emptyMessage="No students match the current filters."
    >
      <div className="flex flex-col items-center gap-6 sm:flex-row">
        {/* ---------- The ring ---------- */}
        <div className="relative h-52 w-52 shrink-0">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={slices}
                dataKey="count"
                nameKey="label"
                innerRadius="62%"
                outerRadius="100%"
                // Produces the mandated surface gap between segments so
                // adjacent fills never bleed into one another.
                paddingAngle={MARK_GAP_PX}
                stroke={CHART_INK.surface}
                strokeWidth={MARK_GAP_PX}
                isAnimationActive={false}
                onClick={handleSliceClick}
              >
                {slices.map((slice) => (
                  <Cell
                    key={slice.bucket}
                    fill={BUCKET_STYLES[slice.bucket].fill}
                    // Dimming the unselected segments makes the active
                    // filter obvious without moving anything around.
                    opacity={
                      activeBucket === null || activeBucket === slice.bucket ? 1 : 0.25
                    }
                    className="cursor-pointer outline-none"
                  />
                ))}
              </Pie>

              <Tooltip
                cursor={false}
                formatter={(value: unknown, name: unknown): [string, string] => {
                  const count = toNumber(value);
                  return [
                    `${pluralStudents(count)} · ${Math.round((count / total) * 100)}%`,
                    toText(name),
                  ];
                }}
                contentStyle={tooltipContentStyle(CHART_INK.grid, CHART_INK.secondary)}
              />
            </PieChart>
          </ResponsiveContainer>

          {/* Total sits in the hole — the one number the ring can't show.
              pointer-events-none so it never blocks a segment click. */}
          <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
            <span className="text-2xl font-semibold leading-none text-stone-900">
              {total}
            </span>
            <span className="mt-1 text-xs text-stone-500">students</span>
          </div>
        </div>

        {/* ---------- Legend, doubling as the value labels ---------- */}
        {/* Capped width: when this card stretches to the full grid (a
            single unit selected, no comparison chart) an unconstrained
            list would strand the counts far from their labels. */}
        <ul className="w-full max-w-sm space-y-1">
          {slices.map((slice) => {
            const isActive = activeBucket === slice.bucket;
            const percent = Math.round((slice.count / total) * 100);

            return (
              <li key={slice.bucket}>
                <button
                  type="button"
                  onClick={() => onSelect(isActive ? null : slice.bucket)}
                  aria-pressed={isActive}
                  className={`flex w-full items-center gap-3 rounded-md px-2 py-1.5 text-left transition ${
                    isActive ? "bg-stone-100" : "hover:bg-stone-50"
                  }`}
                >
                  <BucketBadge bucket={slice.bucket} />
                  <span className="ml-auto text-sm font-semibold tabular-nums text-stone-900">
                    {slice.count}
                  </span>
                  <span className="w-10 text-right text-xs tabular-nums text-stone-500">
                    {percent}%
                  </span>
                </button>
              </li>
            );
          })}
        </ul>
      </div>
    </ChartCard>
  );
}