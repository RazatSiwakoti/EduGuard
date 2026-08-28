import { useMemo, useState } from "react";
import { CircleAlert, LayoutDashboard, RefreshCw } from "lucide-react";
import { useLecturerDashboard } from "../hooks/useDashboard";
import type { DashboardFilters, RiskBucket } from "../types/dashboard";
import {
  computeKpis,
  countByBucket,
  criteriaPerformance,
  engineAgreement,
  filterStudents,
  getBucket,
  momentumByCategory,
  riskByUnit,
} from "../utils/dashboardAggregations";
import CriteriaPerformanceChart from "../components/dashboard/CriteriaPerformanceChart";
import EngineAgreementMatrix from "../components/dashboard/EngineAgreementMatrix";
import FilterBar from "../components/dashboard/FilterBar";
import KpiTiles from "../components/dashboard/KpiTiles";
import MomentumChart from "../components/dashboard/MomentumChart";
import RiskByUnitChart from "../components/dashboard/RiskByUnitChart";
import RiskDistributionDonut from "../components/dashboard/RiskDistributionDonut";
import StudentTable from "../components/dashboard/StudentTable";
import RunAnalysisButton from "../components/analysis/RunAnalysisButton";

/**
 * The lecturer's interactive analytics dashboard — Phase 6.2.
 *
 * ARCHITECTURE
 * ------------
 * One fetch, one filter object, six derived views.
 *
 * The full cohort is loaded once. Both filters live in a single
 * `filters` state object here, and every visual below is derived from
 * it inside a `useMemo`. That is what makes cross-filtering instant:
 * clicking a donut segment or a unit bar is a local state change, not a
 * network request, so nothing reloads and nothing flickers.
 *
 * It also guarantees consistency. Because all six visuals plus the
 * table read from the SAME filtered array, they can never disagree
 * about what is currently on screen — a class of bug that appears the
 * moment each chart is allowed to fetch its own slice.
 *
 * Initial state is "All units, all risk levels", as specified.
 */
export default function Dashboard() {
  const { data, isLoading, isError, error, refetch, isFetching } = useLecturerDashboard();

  const [filters, setFilters] = useState<DashboardFilters>({
    unitId: null,
    bucket: null,
  });

  const units = useMemo(() => data?.units ?? [], [data]);
  const allStudents = useMemo(() => data?.students ?? [], [data]);

  /**
   * Everything the page renders, recomputed only when the data or a
   * filter actually changes.
   *
   * Note what is NOT unit-filtered: `riskByUnit` deliberately ignores
   * the unit filter, because a chart whose job is comparing units must
   * keep showing all of them — otherwise selecting a unit would
   * collapse it to a single bar and remove the only control for getting
   * back. The risk-level filter still applies to it, so it stays in
   * step with the rest of the page.
   */
  const view = useMemo(() => {
    const filtered = filterStudents(allStudents, filters);

    const unitComparison = filterStudents(allStudents, {
      unitId: null,
      bucket: filters.bucket,
    });

    // Which risk chips to offer. Computed from the UNIT-filtered set
    // with no bucket filter applied — using the fully filtered set
    // instead would make every other chip vanish the moment one was
    // selected, stranding the user.
    const bucketsInScope = filterStudents(allStudents, {
      unitId: filters.unitId,
      bucket: null,
    }).map(getBucket);

    return {
      filtered,
      kpis: computeKpis(filtered, units, filters),
      slices: countByBucket(filtered),
      unitRows: riskByUnit(unitComparison, units),
      criteria: criteriaPerformance(filtered),
      momentum: momentumByCategory(filtered),
      agreement: engineAgreement(filtered),
      availableBuckets: [...new Set(bucketsInScope)] as RiskBucket[],
    };
  }, [allStudents, units, filters]);

  /* ---------------- Guards and non-happy paths ---------------- */
 

  if (isLoading) {
    return (
      <div className="px-6 py-8">
        <div className="mx-auto max-w-6xl">
          <SkeletonDashboard />
        </div>
      </div>
    );
  }

  if (isError) {
    return (
      <StatusPanel
        title="Couldn't load your dashboard"
        message={
          error instanceof Error
            ? error.message
            : "Something went wrong reaching the server."
        }
        onRetry={() => void refetch()}
      />
    );
  }

  // A brand-new lecturer with nothing assigned is a legitimate state,
  // not an error — the API returns 200 with empty lists for it.
  if (units.length === 0) {
    return (
      <StatusPanel
        title="No units assigned yet"
        message="Once an administrator assigns you a unit, your cohort's risk analytics will appear here."
      />
    );
  }

  /* ---------------- The dashboard ---------------- */

  return (
    <div className="px-6 py-8">
      <div className="mx-auto max-w-6xl">
        <header className="mb-6 flex flex-wrap items-end justify-between gap-4">
          <div>
            <h1 className="flex items-center gap-2 text-xl font-semibold text-stone-900">
              <LayoutDashboard className="h-5 w-5 text-stone-400" aria-hidden="true" />
              Risk Analytics
            </h1>
            <p className="mt-1 text-sm text-stone-500">
              Week {data?.checkpoint_week} checkpoint · {units.length} unit
              {units.length === 1 ? "" : "s"} · {allStudents.length} enrolment
              {allStudents.length === 1 ? "" : "s"}
            </p>
          </div>


          <div className="flex flex-wrap items-center gap-2">
            {/* Refresh re-reads what the engines already decided.
              Run analysis re-decides it. Two different actions, so
              they sit side by side rather than one being buried. */}            
            <RunAnalysisButton label="Run analysis on all units" />

          <button
            type="button"
            onClick={() => void refetch()}
            disabled={isFetching}
            className="inline-flex items-center gap-2 rounded-md border border-stone-200 bg-white px-3 py-1.5 text-sm font-medium text-stone-700 transition hover:bg-stone-50 disabled:opacity-50"
          >
            <RefreshCw
              className={`h-4 w-4 ${isFetching ? "animate-spin" : ""}`}
              aria-hidden="true"
            />
            Refresh
          </button>
          </div>
        </header>

        <KpiTiles
          kpis={view.kpis}
          activeBucket={filters.bucket}
          onSelectHighRisk={() =>
            setFilters((current) => ({
              ...current,
              bucket: current.bucket === "high_risk" ? null : "high_risk",
            }))
          }
          onSelectNeedsReview={() =>
            setFilters((current) => ({
              ...current,
              bucket: current.bucket === "needs_review" ? null : "needs_review",
            }))
          }
        />

        <FilterBar
          units={units}
          filters={filters}
          onChange={setFilters}
          availableBuckets={view.availableBuckets}
          visibleCount={view.filtered.length}
          totalCount={allStudents.length}
        />

        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          {/* With a single unit selected the comparison chart has
              nothing left to compare, so it is dropped and the donut
              stretches rather than leaving a hole in the grid. */}
          <div className={filters.unitId === null ? "" : "lg:col-span-2"}>
            <RiskDistributionDonut
              slices={view.slices}
              activeBucket={filters.bucket}
              onSelect={(bucket) => setFilters((current) => ({ ...current, bucket }))}
            />
          </div>

          {filters.unitId === null && (
            <RiskByUnitChart
              rows={view.unitRows}
              onSelectUnit={(unitId) =>
                setFilters((current) => ({ ...current, unitId }))
              }
            />
          )}

          <CriteriaPerformanceChart rows={view.criteria} />

          <MomentumChart rows={view.momentum} />

          <div className="lg:col-span-2">
            <EngineAgreementMatrix matrix={view.agreement} />
          </div>
        </div>

        <section className="mt-6">
          <h2 className="mb-3 text-sm font-semibold text-stone-900">Students in view</h2>
          <StudentTable students={view.filtered} />
        </section>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Shared non-happy-path panel                                         */
/* ------------------------------------------------------------------ */

interface StatusPanelProps {
  title: string;
  message: string;
  onRetry?: () => void;
}

/** One presentation for every "there is nothing to show" case. */
function StatusPanel({ title, message, onRetry }: StatusPanelProps) {
  return (
    <div className="flex min-h-[70vh] items-center justify-center px-4">
      <div className="w-full max-w-md rounded-lg border border-stone-200 bg-white p-8 text-center">
        <CircleAlert className="mx-auto h-8 w-8 text-stone-300" aria-hidden="true" />
        <h1 className="mt-3 text-base font-semibold text-stone-900">{title}</h1>
        <p className="mt-2 text-sm leading-relaxed text-stone-500">{message}</p>

        {onRetry && (
          <button
            type="button"
            onClick={onRetry}
            className="mt-5 inline-flex items-center gap-2 rounded-md bg-stone-900 px-4 py-2 text-sm font-medium text-white transition hover:bg-stone-800"
          >
            <RefreshCw className="h-4 w-4" aria-hidden="true" />
            Try again
          </button>
        )}
      </div>
    </div>
  );
}

/**
 * Loading placeholder shaped like the real dashboard.
 *
 * Matching the final layout stops the page jumping when data lands,
 * which is more comfortable to watch than a spinner and makes the wait
 * feel shorter than it actually is.
 */
function SkeletonDashboard() {
  return (
    <div className="animate-pulse">
      <div className="mb-6 h-8 w-56 rounded bg-stone-200" />

      <div className="mb-5 grid grid-cols-2 gap-3 lg:grid-cols-4">
        {[0, 1, 2, 3].map((index) => (
          <div key={index} className="h-20 rounded-lg bg-stone-200" />
        ))}
      </div>

      <div className="mb-5 h-12 rounded-lg bg-stone-200" />

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        {[0, 1, 2, 3].map((index) => (
          <div key={index} className="h-72 rounded-lg bg-stone-200" />
        ))}
      </div>
    </div>
  );
}