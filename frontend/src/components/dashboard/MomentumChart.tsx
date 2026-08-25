import {
  Bar,
  BarChart,
  CartesianGrid,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { TrendingDown, TrendingUp } from "lucide-react";
import type { MomentumRow } from "../../utils/dashboardAggregations";
import { MOMENTUM_BAND_PP } from "../../utils/dashboardAggregations";
import ChartCard from "./ChartCard";
import { CHART_INK, DIVERGING, MARK_GAP_PX, MARK_RADIUS_PX } from "./chartTheme";
import { pluralStudents, toNumber, toText, tooltipContentStyle } from "./tooltipFormat";

interface MomentumChartProps {
  rows: MomentumRow[];
}

/**
 * Who is sliding and who is climbing, per category.
 *
 * WHY THIS EXISTS INSTEAD OF A TREND LINE
 * ---------------------------------------
 * There is no week-by-week line chart on this dashboard, and that is a
 * data-honesty decision rather than an omission. Ingestion aggregates a
 * student's raw weekly cells into one percentage plus one trend figure
 * and discards the weekly values (ingestion_service.py is explicit
 * about this). Drawing a "risk over time" line would therefore mean
 * inventing points that were never recorded.
 *
 * What IS recorded is `trend_value`: the late-window average minus the
 * early-window average, in percentage points. That supports a real,
 * defensible question — is this student's engagement moving up or down
 * across the checkpoint window — without fabricating anything.
 *
 * A diverging bar suits direction better than a stacked one: the zero
 * line does the work, and length either side reads as magnitude in
 * opposite senses without the reader decoding a legend first.
 *
 * COLOUR NOTE: red↔blue, deliberately not red↔green. Red/green is the
 * worst possible pairing for colour-vision deficiency, and this pair
 * validates clean on every check. Direction is additionally carried by
 * SIDE of the zero line and by the arrow icons in the legend, so the
 * chart never depends on hue alone.
 */
export default function MomentumChart({ rows }: MomentumChartProps) {
  const hasData = rows.length > 0;

  return (
    <ChartCard
      title="Engagement Momentum"
      subtitle={`Direction of travel across the checkpoint window. Movement under ${MOMENTUM_BAND_PP} percentage points counts as steady.`}
      empty={!hasData}
      emptyMessage="Momentum needs weekly attendance or tutorial data, which hasn't been uploaded for these students."
      action={
        <div className="flex items-center gap-3 text-xs">
          <span className="inline-flex items-center gap-1.5 text-stone-600">
            <TrendingDown
              className="h-3.5 w-3.5"
              style={{ color: DIVERGING.negative }}
              aria-hidden="true"
            />
            Declining
          </span>
          <span className="inline-flex items-center gap-1.5 text-stone-600">
            <TrendingUp
              className="h-3.5 w-3.5"
              style={{ color: DIVERGING.positive }}
              aria-hidden="true"
            />
            Improving
          </span>
        </div>
      }
    >
      <ResponsiveContainer width="100%" height={Math.max(160, rows.length * 62 + 40)}>
        <BarChart
          data={rows}
          layout="vertical"
          stackOffset="sign"
          margin={{ top: 0, right: 16, bottom: 0, left: 8 }}
          barCategoryGap="34%"
        >
          <CartesianGrid horizontal={false} stroke={CHART_INK.grid} />

          <XAxis
            type="number"
            allowDecimals={false}
            // Counts are never negative in reality — the sign is only a
            // rendering device to push the bar left of zero, so it is
            // stripped from the tick labels.
            tickFormatter={(value: number) => `${Math.abs(value)}`}
            tick={{ fontSize: 11, fill: CHART_INK.muted }}
            axisLine={{ stroke: CHART_INK.axis }}
            tickLine={false}
          />
          <YAxis
            type="category"
            dataKey="label"
            width={104}
            tick={{ fontSize: 11, fill: CHART_INK.muted }}
            axisLine={false}
            tickLine={false}
          />

          <Tooltip
            cursor={{ fill: "rgba(11,11,11,0.04)" }}
            formatter={(value: unknown, name: unknown): [string, string] => [
              // Math.abs strips the rendering-only sign — a count of
              // "-12 declining students" would be nonsense to read.
              pluralStudents(Math.abs(toNumber(value))),
              toText(name),
            ]}
            labelFormatter={(rawLabel: unknown): string => {
              const label = toText(rawLabel);
              const row = rows.find((r) => r.label === label);
              return row ? `${row.label} · ${row.stable} steady` : label;
            }}
            contentStyle={tooltipContentStyle(CHART_INK.grid, CHART_INK.secondary)}
          />

          {/* The anchor the whole chart is read against. Drawn heavier
              than the grid so the split point is unmistakable. */}
          <ReferenceLine x={0} stroke={CHART_INK.axis} strokeWidth={1.5} />

          <Bar
            dataKey="declining"
            name="Declining"
            stackId="momentum"
            fill={DIVERGING.negative}
            stroke={CHART_INK.surface}
            strokeWidth={MARK_GAP_PX}
            radius={MARK_RADIUS_PX}
            isAnimationActive={false}
          />
          <Bar
            dataKey="improving"
            name="Improving"
            stackId="momentum"
            fill={DIVERGING.positive}
            stroke={CHART_INK.surface}
            strokeWidth={MARK_GAP_PX}
            radius={MARK_RADIUS_PX}
            isAnimationActive={false}
          />
        </BarChart>
      </ResponsiveContainer>
    </ChartCard>
  );
}