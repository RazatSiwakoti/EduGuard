import { useState } from "react";
import { isAxiosError } from "axios";
import { CircleAlert, FileBarChart, Loader2 } from "lucide-react";
import { useLecturerUnits } from "../hooks/useLecturerUnits";
import { useUnitReport } from "../hooks/useReports";
import CaveatsPanel from "../components/reports/CaveatsPanel";
import CohortSummary from "../components/reports/CohortSummary";
import CriteriaTable from "../components/reports/CriteriaTable";
import AtRiskTable from "../components/reports/AtRiskTable";
import InterventionRecord from "../components/reports/InterventionRecord";
import { formatDateTime } from "../utils/studentCard";

/**
 * Reports — one unit's early-warning picture at one checkpoint.
 *
 * NOTHING ON THIS PAGE IS COMPUTED IN THE BROWSER.
 * Every count, percentage, average and ordering arrives finished from
 * `GET /lecturer/reports/unit/{id}`. The dashboard does the opposite —
 * it ships raw rows and aggregates client-side so cross-filtering costs
 * nothing — and that is correct there. Here the same object is also
 * rendered into a PDF. If this page derived a figure the PDF generator
 * would have to derive it again, and the two would disagree the first
 * time either changed.
 *
 * ORDER OF THE PAGE. Qualifications, then the cohort, then the
 * criteria, then the students, then what was done about them. The
 * caveats go FIRST because every other view in this project qualifies
 * itself through tooltips a reader has to hover to find, and a report
 * is read top to bottom and printed.
 */
export default function ReportsPage() {
  const unitsQuery = useLecturerUnits();
  const units = unitsQuery.data;

  /**
   * State holds ONLY the lecturer's explicit choice; the default is
   * derived.
   *
   * The obvious version — an effect that calls setUnitId once the units
   * arrive — is what the React Compiler rejects (EffectSetState), and
   * it is rejected for a good reason: it renders once with no unit,
   * then again with one, and any later refetch risks stomping the
   * lecturer's selection.
   *
   * Deriving instead means there is no intermediate render and no way
   * for a refetch to undo a choice. `chosen` is dropped if that unit
   * disappears from the list mid-session (an admin unassigning it),
   * because pointing the picker at a unit the lecturer no longer
   * teaches would only ever produce a 404.
   */
  const [chosen, setChosen] = useState<number | null>(null);
  const chosenIsValid =
    chosen !== null && (units?.some((unit) => unit.id === chosen) ?? false);
  const unitId = chosenIsValid ? chosen : (units?.[0]?.id ?? null);

  const reportQuery = useUnitReport(unitId);
  const report = reportQuery.data;

  const notFound =
    isAxiosError(reportQuery.error) && reportQuery.error.response?.status === 404;

  return (
    <div className="px-6 py-8">
      <div className="mx-auto max-w-6xl">
        <header className="mb-6 flex flex-wrap items-start justify-between gap-4">
          <div>
            <h1 className="flex items-center gap-2.5 text-2xl font-semibold tracking-tight text-stone-900">
              <FileBarChart className="h-6 w-6 text-stone-400" aria-hidden="true" />
              Reports
            </h1>
            <p className="mt-1 text-sm text-stone-500">
              {report ? (
                <>
                  {report.unit_code} &mdash; {report.unit_name}
                  <span className="mx-1.5 text-stone-300">·</span>
                  Week {report.checkpoint_week} checkpoint
                  {report.last_analysed_at && (
                    <>
                      <span className="mx-1.5 text-stone-300">·</span>
                      analysis last run {formatDateTime(report.last_analysed_at)}
                    </>
                  )}
                </>
              ) : (
                "A unit's risk picture at one checkpoint, with the qualifications that belong to it."
              )}
            </p>
          </div>

          {units && units.length > 0 && (
            <label className="flex items-center gap-2 text-sm">
              <span className="text-stone-500">Unit</span>
              <select
                value={unitId ?? ""}
                onChange={(event) => setChosen(Number(event.target.value))}
                className="rounded-xl border border-stone-300 bg-white px-3 py-2 text-sm text-stone-900 focus:border-stone-400 focus:outline-none focus:ring-1 focus:ring-stone-400"
              >
                {units.map((unit) => (
                  <option key={unit.id} value={unit.id}>
                    {unit.unit_code} — {unit.unit_name}
                  </option>
                ))}
              </select>
            </label>
          )}
        </header>

        {/* ---------------------------------------------------------- */}
        {/* States before there is a report to show                     */}
        {/* ---------------------------------------------------------- */}
        {unitsQuery.isLoading && (
          <div className="flex items-center justify-center gap-2 rounded-2xl border border-stone-200 bg-white py-16 text-sm text-stone-500">
            <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
            Loading your units…
          </div>
        )}

        {unitsQuery.isError && (
          <div className="rounded-2xl border border-red-200 bg-red-50 px-5 py-4 text-sm text-red-800">
            Your units could not be loaded, so no report can be built. Try
            reloading the page.
          </div>
        )}

        {units && units.length === 0 && (
          <div className="rounded-2xl border border-stone-200 bg-white px-6 py-12 text-center">
            <p className="text-sm font-medium text-stone-700">
              You are not assigned to any units yet.
            </p>
            <p className="mt-1 text-sm text-stone-500">
              A report is built per unit, so there is nothing to report on until
              an administrator assigns you one.
            </p>
          </div>
        )}

        {unitId !== null && reportQuery.isLoading && (
          <div className="flex items-center justify-center gap-2 rounded-2xl border border-stone-200 bg-white py-16 text-sm text-stone-500">
            <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
            Building the report…
          </div>
        )}

        {reportQuery.isError && (
          <div className="flex items-start gap-2.5 rounded-2xl border border-red-200 bg-red-50 px-5 py-4">
            <CircleAlert
              className="mt-0.5 h-4 w-4 shrink-0 text-red-500"
              aria-hidden="true"
            />
            <div className="text-sm text-red-800">
              {notFound ? (
                <>
                  <p className="font-medium">That unit is not available to you.</p>
                  <p className="mt-0.5">
                    Either it does not exist or it is taught by someone else.
                    Reports are scoped to the units you are assigned to.
                  </p>
                </>
              ) : (
                <>
                  <p className="font-medium">The report could not be built.</p>
                  <p className="mt-0.5">
                    Try reloading. If it keeps failing, the analysis data for this
                    unit may be incomplete.
                  </p>
                </>
              )}
            </div>
          </div>
        )}

        {/* ---------------------------------------------------------- */}
        {/* The report                                                  */}
        {/* ---------------------------------------------------------- */}
        {report && (
          <div className="space-y-5">
            {/* FIRST, deliberately. See the component's docstring. */}
            <CaveatsPanel caveats={report.caveats} />

            <CohortSummary
              enrolled={report.enrolled_count}
              analysed={report.analysed_count}
              notAnalysed={report.not_analysed_count}
              atRiskCount={report.at_risk.length}
              distribution={report.distribution}
            />

            <CriteriaTable criteria={report.criteria} />

            <AtRiskTable
              rows={report.at_risk}
              alertsAvailable={report.intervention.available}
            />

            <InterventionRecord intervention={report.intervention} />

            <footer className="px-1 pb-2 text-xs leading-relaxed text-stone-400">
              Generated {formatDateTime(report.generated_at)}
              {report.lecturer_name && <> · {report.lecturer_name}</>}. This report
              contains identifiable student information. Risk tiers are produced
              by automated analysis and, where marked, by a lecturer resolving a
              disagreement between the two engines &mdash; they are an indication
              for follow-up, not a determination about any student.
            </footer>
          </div>
        )}
      </div>
    </div>
  );
}