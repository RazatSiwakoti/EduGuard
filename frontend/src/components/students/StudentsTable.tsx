import { ChevronDown, ChevronUp, Download } from "lucide-react";
import type { DashboardStudent, DashboardUnit } from "../../types/dashboard";
import { PAGE_SIZE } from "../../utils/studentsTable";
import type { SortDirection, SortKey } from "../../utils/studentsTable";
import Pagination from "./Pagination";
import StudentRow from "./StudentRow";

interface SortHeaderProps {
  label: string;
  sortKeyValue: SortKey;
  activeKey: SortKey;
  direction: SortDirection;
  onSort: (key: SortKey) => void;
}

/**
 * A sortable column heading.
 *
 * Declared at module level, NOT inside the table component. A component
 * defined during render is a brand-new component type on every render,
 * so React unmounts and remounts it each time and throws away any state
 * it held — and the React Compiler lint rules reject it outright.
 * Everything it needs arrives as props.
 */
function SortHeader({
  label,
  sortKeyValue,
  activeKey,
  direction,
  onSort,
}: SortHeaderProps) {
  const isActive = activeKey === sortKeyValue;
  const Icon = direction === "asc" ? ChevronUp : ChevronDown;

  return (
    <button
      type="button"
      onClick={() => onSort(sortKeyValue)}
      aria-label={`Sort by ${label}`}
      className={`inline-flex items-center gap-1 transition hover:text-stone-900 ${
        isActive ? "text-stone-900" : "text-stone-500"
      }`}
    >
      {label}
      {/* The arrow appears on the active column only — one on every
          heading makes it impossible to see which sort is in effect. */}
      {isActive && <Icon className="h-3 w-3" aria-hidden="true" />}
    </button>
  );
}

interface StudentsTableProps {
  /** Rows for the CURRENT page only. */
  rows: DashboardStudent[];
  /** Every row surviving the filters, for the count and the export. */
  filteredCount: number;
  unitsById: Map<number, DashboardUnit>;
  sortKey: SortKey;
  direction: SortDirection;
  onSort: (key: SortKey) => void;
  page: number;
  totalPages: number;
  onPageChange: (page: number) => void;
  onExport: () => void;
  /** Rendered when the filters match nothing. */
  emptyMessage: string;
  onClearFilters?: () => void;
  onSelectStudent?: (student: DashboardStudent) => void;
  /**
   * Whether to render the Weekly Tut column at all.
   *
   * Decided by the PAGE, not here, because the rule depends on the
   * subject filter: across all subjects the column always shows (units
   * that don't run tutorials simply read "—"), but once one unit is
   * selected the column disappears entirely if that unit has no
   * weekly_tut criterion. A column of nothing but dashes is worse than
   * no column — it reads as a cohort that stopped submitting.
   */
  showTutorial: boolean;
}

/**
 * The students table.
 *
 * Columns are Student · Attendance · Assessments · Weekly Tut · Risk
 * Level · Trend. Deliberately absent:
 *
 *   - GPA, because no such field exists anywhere in the schema.
 *   - The engine scores. Both are real — the ML one is genuinely a
 *     confidence figure (`max(probabilities.values())`) — but they
 *     measure DIFFERENT things on the same 0–1 range: rule is weighted
 *     badness, ML is class confidence. Two such numbers in adjacent
 *     table cells invite exactly the comparison that makes no sense.
 *     They belong in the card, each with a caption saying what it is,
 *     beside the SHAP explanation that justifies it.
 *
 * Sorting applies to the whole filtered set, not just the visible page,
 * so "sort by attendance ascending" genuinely surfaces the worst
 * attender in the cohort rather than the worst on page one.
 */
export default function StudentsTable({
  rows,
  filteredCount,
  unitsById,
  sortKey,
  direction,
  onSort,
  page,
  totalPages,
  onPageChange,
  onExport,
  emptyMessage,
  onClearFilters,
  onSelectStudent,
  showTutorial,
}: StudentsTableProps) {
  // Derived from PAGE_SIZE rather than a literal, so the "showing 9–16
  // of 47" line can never drift out of step with the actual slice.
  const firstRow = filteredCount === 0 ? 0 : (page - 1) * PAGE_SIZE + 1;
  const lastRow = filteredCount === 0 ? 0 : firstRow + rows.length - 1;

  return (
    <section className="overflow-hidden rounded-2xl border border-stone-200 bg-white">
      <header className="flex flex-wrap items-center justify-between gap-3 border-b border-stone-200 px-5 py-4">
        <div className="flex items-center gap-2.5">
          <h2 className="text-base font-semibold text-stone-900">Student Overview</h2>
          <span className="rounded-full bg-stone-100 px-2 py-0.5 text-xs font-medium tabular-nums text-stone-600">
            {filteredCount} student{filteredCount === 1 ? "" : "s"}
          </span>
        </div>

        <button
          type="button"
          onClick={onExport}
          disabled={filteredCount === 0}
          // The label says "filtered" because that is what it exports.
          // Exporting only the visible eight would produce a file that
          // looks complete and is missing most of the cohort.
          title="Downloads every row matching the current filters, not just this page"
          className="inline-flex items-center gap-2 rounded-xl bg-stone-900 px-4 py-2.5 text-sm font-medium text-white transition hover:bg-stone-700 disabled:cursor-not-allowed disabled:opacity-40 disabled:hover:bg-stone-900"
        >
          <Download className="h-4 w-4" aria-hidden="true" />
          Export CSV
        </button>
      </header>

      {filteredCount === 0 ? (
        <div className="px-6 py-14 text-center">
          <p className="text-sm text-stone-500">{emptyMessage}</p>

          {onClearFilters && (
            <button
              type="button"
              onClick={onClearFilters}
              className="mt-3 text-sm font-medium text-stone-700 underline underline-offset-4 transition hover:text-stone-900"
            >
              Clear all filters
            </button>
          )}
        </div>
      ) : (
        <>
          {/* Horizontal scroll is confined to this wrapper so the page
              body never scrolls sideways on a narrow screen. */}
          <div className="overflow-x-auto">
            <table className={`w-full text-left ${showTutorial ? "min-w-[880px]" : "min-w-[760px]"}`}>
              <thead className="border-b border-stone-200 bg-stone-50/70 text-xs font-medium uppercase tracking-wide text-stone-500">
                <tr>
                  <th scope="col" className="px-4 py-3">
                    <SortHeader
                      label="Student"
                      sortKeyValue="name"
                      activeKey={sortKey}
                      direction={direction}
                      onSort={onSort}
                    />
                  </th>
                  <th scope="col" className="px-4 py-3">
                    <SortHeader
                      label="Attendance"
                      sortKeyValue="attendance"
                      activeKey={sortKey}
                      direction={direction}
                      onSort={onSort}
                    />
                  </th>
                  <th scope="col" className="px-4 py-3">
                    <SortHeader
                      label="Assessments"
                      sortKeyValue="assessments"
                      activeKey={sortKey}
                      direction={direction}
                      onSort={onSort}
                    />
                  </th>
                  {showTutorial && (
                    <th scope="col" className="px-4 py-3">
                      <SortHeader
                        label="Weekly Tut"
                        sortKeyValue="tutorial"
                        activeKey={sortKey}
                        direction={direction}
                        onSort={onSort}
                      />
                    </th>
                  )}
                  <th scope="col" className="px-4 py-3">
                    <SortHeader
                      label="Risk Level"
                      sortKeyValue="risk"
                      activeKey={sortKey}
                      direction={direction}
                      onSort={onSort}
                    />
                  </th>
                  <th scope="col" className="px-4 py-3">
                    <SortHeader
                      label="Trend"
                      sortKeyValue="trend"
                      activeKey={sortKey}
                      direction={direction}
                      onSort={onSort}
                    />
                  </th>
                </tr>
              </thead>

              <tbody className="divide-y divide-stone-100">
                {rows.map((student) => (
                  <StudentRow
                    // student_id alone is NOT unique — the same student
                    // appears once per unit — so the key is the pair.
                    key={`${student.student_id}-${student.unit_id}`}
                    student={student}
                    unit={unitsById.get(student.unit_id)}
                    onSelect={onSelectStudent}
                    showTutorial={showTutorial}
                  />
                ))}
              </tbody>
            </table>
          </div>

          <Pagination
            page={page}
            totalPages={totalPages}
            totalRows={filteredCount}
            firstRow={firstRow}
            lastRow={lastRow}
            onChange={onPageChange}
          />
        </>
      )}
    </section>
  );
}