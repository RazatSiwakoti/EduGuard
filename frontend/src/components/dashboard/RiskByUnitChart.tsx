import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { UnitRiskRow } from "../../utils/dashboardAggregations";
import { BUCKET_LABELS, BUCKET_ORDER } from "../../utils/dashboardAggregations";
import BucketBadge from "./BucketBadge";
import ChartCard from "./ChartCard";
import { BUCKET_STYLES, CHART_INK, MARK_GAP_PX, MARK_RADIUS_PX } from "./chartTheme";
import { toNumber, toText, tooltipContentStyle } from "./tooltipFormat";
import { useChartIntroAnimation } from "../../utils/chartAnimation";

interface RiskByUnitChartProps {
  rows: UnitRiskRow[];
  onSelectUnit: (unitId: number) => void;
}

/**
 * Risk composition of each unit, side by side.
 *
 * Horizontal bars rather than vertical: unit codes are text labels of
 * varying length, and on a horizontal layout they read left-to-right at
 * normal size instead of being rotated 45° or truncated.
 *
 * Stacked by COUNT, not percentage. A lecturer comparing units needs to
 * see that one unit is simply larger than another; normalising every
 * bar to 100% would erase exactly that, and make a unit with 2 of 4
 * students at risk look identical to one with 30 of 60.
 *
 * Only rendered in "All units" mode — with a single unit selected this
 * chart degenerates into one bar showing what the donut already said.
 */
export default function RiskByUnitChart({ rows, onSelectUnit }: RiskByUnitChartProps) {
  // Grows in once on first paint, then stays instant for every
  // filter change after it. See utils/chartAnimation.ts.
  // The bars grow in once, on first paint only. See
  // utils/chartAnimation.ts for why this is a CSS class rather
  // than Recharts' own isAnimationActive, which does nothing at
  // this version.
  const intro = useChartIntroAnimation();

  const hasData = rows.some((row) => row.total > 0);

  // Index-based lookup, same reasoning as the donut: the chart hands
  // back a position, we resolve it against our own typed rows.
  const handleBarClick = (_data: unknown, index: number) => {
    const row = rows[index];
    if (row) onSelectUnit(row.unitId);
  };

  // Height grows with the number of units so bars keep a readable
  // thickness instead of being squeezed into a fixed box.
  const chartHeight = Math.max(180, rows.length * 46 + 40);

  return (
    <ChartCard
      title="Risk by Unit"
      subtitle="Where the at-risk students actually are. Click a bar to focus that unit."
      empty={!hasData}
      emptyMessage="No students are enrolled in your units yet."
      // Five badges is far too wide to sit beside the title — it goes in
      // the full-width legend row underneath instead.
      legend={BUCKET_ORDER.map((bucket) => (
        <BucketBadge key={bucket} bucket={bucket} />
      ))}
    >
      <ResponsiveContainer width="100%" height={chartHeight}>
        <BarChart
          data={rows}
          layout="vertical"
          margin={{ top: 0, right: 16, bottom: 0, left: 8 }}
          barCategoryGap="28%"
        >
          {/* Grid only along the measured axis. A grid line across the
              category axis would add ink without aiding comparison. */}
          <CartesianGrid horizontal={false} stroke={CHART_INK.grid} />

          <XAxis
            type="number"
            allowDecimals={false}
            tick={{ fontSize: 11, fill: CHART_INK.muted }}
            axisLine={{ stroke: CHART_INK.axis }}
            tickLine={false}
          />
          <YAxis
            type="category"
            dataKey="unitCode"
            width={78}
            tick={{ fontSize: 11, fill: CHART_INK.muted }}
            axisLine={false}
            tickLine={false}
          />

          <Tooltip
            cursor={{ fill: "rgba(11,11,11,0.04)" }}
            formatter={(value: unknown, name: unknown): [string, string] => [
              `${toNumber(value)}`,
              toText(name),
            ]}
            labelFormatter={(label: unknown): string => {
              const unitCode = toText(label);
              const row = rows.find((r) => r.unitCode === unitCode);
              return row ? `${row.unitCode} — ${row.unitName}` : unitCode;
            }}
            contentStyle={tooltipContentStyle(CHART_INK.grid, CHART_INK.secondary)}
          />

          {BUCKET_ORDER.map((bucket) => (
            <Bar
              key={bucket}
              dataKey={bucket}
              name={BUCKET_LABELS[bucket]}
              stackId="risk"
              fill={BUCKET_STYLES[bucket].fill}
              // A surface-coloured stroke is how a real gap between
              // stacked segments is achieved in Recharts — without it
              // adjacent fills touch and the boundary disappears.
              stroke={CHART_INK.surface}
              strokeWidth={MARK_GAP_PX}
              radius={MARK_RADIUS_PX}
              {...intro}
              onClick={handleBarClick}
              className="cursor-pointer"
            />
          ))}
        </BarChart>
      </ResponsiveContainer>
    </ChartCard>
  );
}