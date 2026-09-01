import {
  Bar,
  BarChart,
  CartesianGrid,
  LabelList,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { CriteriaPerformanceRow } from "../../utils/dashboardAggregations";
import ChartCard from "./ChartCard";
import { CHART_INK, MARK_RADIUS_PX, SERIES_BLUE } from "./chartTheme";
import { toNumber, toText, tooltipContentStyle } from "./tooltipFormat";
import { useChartIntroAnimation } from "../../utils/chartAnimation";

interface CriteriaPerformanceChartProps {
  rows: CriteriaPerformanceRow[];
}

/**
 * Cohort performance per criteria category, against each category's own
 * pass mark. This is the chart that answers "WHY are they at risk?"
 * rather than "how many are at risk".
 *
 * THE ONE AXIS PROBLEM, AND HOW THIS SOLVES IT
 * --------------------------------------------
 * The four categories are not measured in the same unit at all.
 * Attendance is a percentage judged against 80. Moodle is a raw login
 * COUNT judged against 10. Plotting both on one axis of raw values
 * would render the Moodle bar as a sliver next to an attendance bar of
 * ~75, implying Moodle engagement is catastrophic when it may be fine.
 *
 * The fix is NOT a second y-axis — a dual-axis chart lets you place the
 * two scales wherever flatters the story, and is the single most
 * misleading thing you can do to a reader. Instead every value is
 * divided by its own threshold, so the axis measures one honest thing:
 * distance from the bar you had to clear. 100% IS the threshold, which
 * makes a single reference line meaningful for all four categories at
 * once.
 *
 * Raw averages are still in the tooltip, because the normalised number
 * answers "are they passing" while the raw one answers "by how much".
 */
export default function CriteriaPerformanceChart({
  rows,
}: CriteriaPerformanceChartProps) {
  // Grows in once on first paint, then stays instant for every
  // filter change after it. See utils/chartAnimation.ts.
  // The bars grow in once, on first paint only. See
  // utils/chartAnimation.ts for why this is a CSS class rather
  // than Recharts' own isAnimationActive, which does nothing at
  // this version.
  const intro = useChartIntroAnimation();

  // Headroom above the tallest bar so its label never collides with the
  // top of the plot. Always at least 120 so the threshold line sits
  // comfortably inside the chart rather than pinned to the ceiling.
  const upperBound = Math.max(
    120,
    Math.ceil(Math.max(...rows.map((r) => r.percentOfThreshold), 0) / 20) * 20 + 10,
  );

  return (
    <ChartCard
      title="Criteria Performance vs Threshold"
      subtitle="Cohort average for each category, measured against its own pass mark. 100% = exactly at the threshold."
      empty={rows.length === 0}
      emptyMessage="No criterion data has been uploaded for these students yet."
    >
      <ResponsiveContainer width="100%" height={260}>
        <BarChart
          data={rows}
          // Generous right margin so the "Threshold" reference-line
          // label has room to render instead of being clipped by the
          // plot edge.
          margin={{ top: 24, right: 68, bottom: 0, left: 0 }}
          barCategoryGap="34%"
        >
          <CartesianGrid vertical={false} stroke={CHART_INK.grid} />

          <XAxis
            dataKey="label"
            tick={{ fontSize: 11, fill: CHART_INK.muted }}
            axisLine={{ stroke: CHART_INK.axis }}
            tickLine={false}
          />
          <YAxis
            domain={[0, upperBound]}
            tickFormatter={(value: number) => `${value}%`}
            tick={{ fontSize: 11, fill: CHART_INK.muted }}
            axisLine={false}
            tickLine={false}
            width={46}
          />

          <Tooltip
            cursor={{ fill: "rgba(11,11,11,0.04)" }}
            formatter={(value: unknown): [string, string] => [
              `${toNumber(value)}% of threshold`,
              "Cohort average",
            ]}
            labelFormatter={(rawLabel: unknown): string => {
              const label = toText(rawLabel);
              const row = rows.find((r) => r.label === label);
              if (!row) return label;
              // Raw numbers restored here — the normalised bar says
              // "are they passing", this says "by how much, in reality".
              return `${row.label} · avg ${row.averageScore} vs threshold ${row.averageThreshold} · ${row.belowThreshold}/${row.sampleSize} below`;
            }}
            contentStyle={tooltipContentStyle(CHART_INK.grid, CHART_INK.secondary)}
          />

          {/* The whole point of normalising: one line that is the pass
              mark for every category simultaneously. */}
          <ReferenceLine
            y={100}
            stroke={CHART_INK.axis}
            strokeDasharray="4 4"
            label={{
              value: "Threshold",
              position: "right",
              fill: CHART_INK.muted,
              fontSize: 10,
            }}
          />

          {/* Single series, so no legend box — the card title names it.
              Direct labels instead, which are more precise than a legend
              and keep the reader's eye on the marks. */}
          <Bar
            dataKey="percentOfThreshold"
                        name="Cohort average"
            fill={SERIES_BLUE}
            radius={[MARK_RADIUS_PX, MARK_RADIUS_PX, 0, 0]}
            maxBarSize={64}
            {...intro}
          >
            <LabelList
              dataKey="percentOfThreshold"
              position="top"
              offset={8}
              // Labels wear text ink, never the series colour.
              fill={CHART_INK.secondary}
              fontSize={11}
              formatter={(value: unknown) => `${toNumber(value)}%`}
            />
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </ChartCard>
  );
}