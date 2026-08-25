import { useMemo, useState } from "react";
import { ChevronDown, ChevronUp, CircleAlert } from "lucide-react";
import type { DashboardStudent } from "../../types/dashboard";
import {
  BUCKET_LABELS,
  BUCKET_ORDER,
  getBucket,
} from "../../utils/dashboardAggregations";
import BucketBadge from "./BucketBadge";

interface StudentTableProps {
  students: DashboardStudent[];
}

type SortKey = "name" | "unit" | "risk";
type SortDirection = "asc" | "desc";

/**
 * Rows rendered before the "show all" control appears.
 *
 * A lecturer with several large units can easily have 300+ enrolments,
 * and rendering every row would produce a page metres long that buries
 * the charts above it. Since the default sort puts the most urgent
 * students first, the first 50 rows are the ones that matter — the rest
 * stay one click away.
 */
const INITIAL_ROW_LIMIT = 50;

/**
 * Severity rank for sorting. Derived from BUCKET_ORDER (worst first) so
 * the table's idea of "most urgent" can never drift from the order the
 * charts and legends use.
 */
const SEVERITY_RANK: Record<string, number> = Object.fromEntries(
  BUCKET_ORDER.map((bucket, index) => [bucket, index]),
);

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
 * Declared at module level rather than inside StudentTable on purpose:
 * a component defined during render is a NEW component type on every
 * render, so React unmounts and remounts it each time and any state it
 * held is silently thrown away. The React Compiler lint rules reject
 * this outright. Everything it needs arrives as props instead.
 */
function SortHeader({
  label,
  sortKeyValue,
  activeKey,
  direction,
  onSort,
}: SortHeaderProps) {
  const isActive = activeKey === sortKeyValue;
  const Icon = direction === "asc" ? ChevronDown : ChevronUp;

  return (
    <button
      type="button"
      onClick={() => onSort(sortKeyValue)}
      className="inline-flex items-center gap-1 font-medium text-stone-600 transition hover:text-stone-900"
    >
      {label}
      {/* The arrow only appears on the active column — showing one on
          every heading makes it impossible to see which is in effect. */}
      {isActive && <Icon className="h-3 w-3" aria-hidden="true" />}
    </button>
  );
}

/**
 * The named list behind every chart on the page.
 *
 * This is not a bonus feature — it is the accessibility relief the
 * colour palette requires. Two risk tiers sit below 3:1 contrast on a
 * white card, and the rule for that is that a text alternative must
 * exist. Every figure in every chart above can be traced to named rows
 * here, so no information on this dashboard is reachable only through
 * colour.
 *
 * It also closes the loop on cross-filtering: clicking "High Risk" in a
 * chart is only actionable if the lecturer can immediately see WHICH
 * students that is.
 *
 * Defaults to sorting by risk, worst first — a lecturer opening an
 * early-warning system wants the urgent cases at the top, not
 * alphabetical order.
 */
export default function StudentTable({ students }: StudentTableProps) {
  const [sortKey, setSortKey] = useState<SortKey>("risk");
  const [direction, setDirection] = useState<SortDirection>("asc");
  const [showAll, setShowAll] = useState(false);

  const sorted = useMemo(() => {
    // Copy before sorting — sort() mutates, and mutating props would
    // corrupt the array every other chart is reading from.
    const rows = [...students];
    const modifier = direction === "asc" ? 1 : -1;

    rows.sort((a, b) => {
      if (sortKey === "name") return a.name.localeCompare(b.name) * modifier;
      if (sortKey === "unit") {
        // Unit is a weak key with many ties, so students stay
        // alphabetical inside each unit rather than in arbitrary order.
        const byUnit = a.unit_code.localeCompare(b.unit_code) * modifier;
        return byUnit !== 0 ? byUnit : a.name.localeCompare(b.name);
      }
      const bySeverity =
        (SEVERITY_RANK[getBucket(a)] - SEVERITY_RANK[getBucket(b)]) * modifier;
      return bySeverity !== 0 ? bySeverity : a.name.localeCompare(b.name);
    });

    return rows;
  }, [students, sortKey, direction]);

  const visible = showAll ? sorted : sorted.slice(0, INITIAL_ROW_LIMIT);
  const hiddenCount = sorted.length - visible.length;

  function toggleSort(key: SortKey) {
    if (key === sortKey) {
      setDirection((current) => (current === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key);
      setDirection("asc");
    }
  }

  if (students.length === 0) {
    return (
      <div className="rounded-lg border border-stone-200 bg-white p-10 text-center">
        <p className="text-sm text-stone-500">No students match the current filters.</p>
      </div>
    );
  }

  return (
    <div className="overflow-hidden rounded-lg border border-stone-200 bg-white">
      {/* Horizontal scroll is confined to this wrapper so the page body
          itself never scrolls sideways on a narrow screen. */}
      <div className="overflow-x-auto">
        <table className="w-full min-w-[720px] text-left text-sm">
          <thead className="border-b border-stone-200 bg-stone-50 text-xs uppercase tracking-wide text-stone-500">
            <tr>
              <th scope="col" className="px-4 py-3">
                <SortHeader
                  label="Student"
                  sortKeyValue="name"
                  activeKey={sortKey}
                  direction={direction}
                  onSort={toggleSort}
                />
              </th>
              <th scope="col" className="px-4 py-3">
                <SortHeader
                  label="Unit"
                  sortKeyValue="unit"
                  activeKey={sortKey}
                  direction={direction}
                  onSort={toggleSort}
                />
              </th>
              <th scope="col" className="px-4 py-3">
                <SortHeader
                  label="Final verdict"
                  sortKeyValue="risk"
                  activeKey={sortKey}
                  direction={direction}
                  onSort={toggleSort}
                />
              </th>
              <th scope="col" className="px-4 py-3 font-medium">
                Rule engine
              </th>
              <th scope="col" className="px-4 py-3 font-medium">
                ML model
              </th>
            </tr>
          </thead>

          <tbody className="divide-y divide-stone-100">
            {visible.map((student) => {
              const bucket = getBucket(student);

              return (
                // student_id alone is not unique — the same student can
                // appear once per unit — so the key is the pair.
                <tr
                  key={`${student.student_id}-${student.unit_id}`}
                  className="transition hover:bg-stone-50"
                >
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <div className="min-w-0">
                        <p className="truncate font-medium text-stone-900">
                          {student.name}
                        </p>
                        <p className="truncate text-xs tabular-nums text-stone-500">
                          {student.student_number}
                        </p>
                      </div>

                      {/* An incomplete score is still shown, but flagged.
                          Hiding it would be worse: the lecturer would
                          never learn the data was patchy. */}
                      {student.is_incomplete && (
                        <span
                          title="Scored with incomplete data — treat this verdict with caution"
                          className="shrink-0 text-amber-500"
                        >
                          <CircleAlert className="h-4 w-4" aria-hidden="true" />
                          <span className="sr-only">Incomplete data</span>
                        </span>
                      )}
                    </div>
                  </td>

                  <td className="px-4 py-3 text-stone-600">{student.unit_code}</td>

                  <td className="px-4 py-3">
                    <BucketBadge bucket={bucket} />
                  </td>

                  <td className="px-4 py-3 text-xs text-stone-600">
                    {student.rule_tier ? BUCKET_LABELS[student.rule_tier] : "—"}
                  </td>

                  <td className="px-4 py-3 text-xs text-stone-600">
                    {student.ml_tier ? BUCKET_LABELS[student.ml_tier] : "—"}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Only rendered once there is genuinely something hidden, so a
          small cohort never sees a control that does nothing. */}
      {hiddenCount > 0 && (
        <div className="border-t border-stone-200 bg-stone-50 px-4 py-3 text-center">
          <button
            type="button"
            onClick={() => setShowAll(true)}
            className="text-sm font-medium text-stone-700 transition hover:text-stone-900"
          >
            Show {hiddenCount} more student{hiddenCount === 1 ? "" : "s"}
          </button>
        </div>
      )}
    </div>
  );
}