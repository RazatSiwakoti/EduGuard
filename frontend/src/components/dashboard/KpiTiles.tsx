import { BookOpen, CircleDashed, OctagonAlert, Scale, Users } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import type { DashboardKpis } from "../../utils/dashboardAggregations";
import { BUCKET_STYLES } from "./chartTheme";

interface TileProps {
  label: string;
  value: number | string;
  hint: string;
  icon: LucideIcon;
  /** Tier colour for the icon. Omitted tiles stay neutral stone. */
  accent?: string;
  /** Called when the tile doubles as a filter shortcut. */
  onClick?: () => void;
  isActive?: boolean;
}

/**
 * One headline figure.
 *
 * A stat tile rather than a chart on purpose: a single number has no
 * shape worth plotting, and wrapping four of them in mini-charts would
 * add ink without adding information.
 */
function Tile({ label, value, hint, icon: Icon, accent, onClick, isActive }: TileProps) {
  const interactive = typeof onClick === "function";

  return (
    <button
      type="button"
      onClick={onClick}
      disabled={!interactive}
      aria-pressed={interactive ? isActive : undefined}
      title={hint}
      className={`flex items-start gap-3 rounded-lg border bg-white p-4 text-left transition ${
        isActive ? "border-stone-900 ring-1 ring-stone-900" : "border-stone-200"
      } ${interactive ? "cursor-pointer hover:border-stone-300 hover:bg-stone-50" : "cursor-default"}`}
    >
      <span
        className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-stone-50"
        style={accent ? { color: accent } : { color: "#898781" }}
      >
        <Icon className="h-4 w-4" aria-hidden="true" />
      </span>

      <span className="min-w-0">
        {/* Proportional figures by default; tabular-nums is reserved for
            columns that must align vertically, which these do not. */}
        <span className="block text-2xl font-semibold leading-none text-stone-900">
          {value}
        </span>
        <span className="mt-1 block text-xs font-medium text-stone-600">{label}</span>
      </span>
    </button>
  );
}

interface KpiTilesProps {
  kpis: DashboardKpis;
  /** Lets the High Risk and Needs Review tiles act as filter shortcuts. */
  onSelectHighRisk: () => void;
  onSelectNeedsReview: () => void;
  activeBucket: string | null;
}

/**
 * The four headline numbers, above every chart.
 *
 * Two of them are clickable and set the risk filter — the same state
 * the chips and the donut write to. A lecturer opening this page almost
 * always wants "who is high risk", so making that number itself the
 * shortcut removes a step.
 *
 * "Not Analysed" is shown as a tile rather than buried in a chart
 * legend because it is an ACTION for the lecturer: those students need
 * an analysis run, not interpretation.
 */
export default function KpiTiles({
  kpis,
  onSelectHighRisk,
  onSelectNeedsReview,
  activeBucket,
}: KpiTilesProps) {
  return (
    <div className="mb-5 grid grid-cols-2 gap-3 lg:grid-cols-4">
      <Tile
        label="Students in view"
        value={kpis.totalStudents}
        hint={`Across ${kpis.unitCount} unit${kpis.unitCount === 1 ? "" : "s"}`}
        icon={Users}
      />

      <Tile
        label={`High risk · ${kpis.highRiskPercent}% of analysed`}
        value={kpis.highRisk}
        hint="Click to filter the whole dashboard to these students"
        icon={OctagonAlert}
        accent={BUCKET_STYLES.high_risk.fill}
        onClick={onSelectHighRisk}
        isActive={activeBucket === "high_risk"}
      />

      <Tile
        label="Awaiting your review"
        value={kpis.needsReview}
        hint="The rule engine and ML model disagreed — you decide the tier"
        icon={Scale}
        accent={BUCKET_STYLES.needs_review.fill}
        onClick={onSelectNeedsReview}
        isActive={activeBucket === "needs_review"}
      />

      {/* Swaps to a units count once nothing is left unanalysed, so the
          tile never sits there reading a permanent, meaningless zero. */}
      {kpis.notAnalysed > 0 ? (
        <Tile
          label="Not yet analysed"
          value={kpis.notAnalysed}
          hint="Enrolled students with no verdict — run the analysis for their unit"
          icon={CircleDashed}
          accent={BUCKET_STYLES.not_analysed.fill}
        />
      ) : (
        <Tile
          label={kpis.unitCount === 1 ? "Unit in view" : "Units you teach"}
          value={kpis.unitCount}
          hint="Active units assigned to you"
          icon={BookOpen}
        />
      )}
    </div>
  );
}