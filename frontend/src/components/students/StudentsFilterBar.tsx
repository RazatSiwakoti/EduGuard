import { Filter, Search, X } from "lucide-react";
import type { DashboardUnit } from "../../types/dashboard";

interface StudentsFilterBarProps {
  search: string;
  onSearchChange: (value: string) => void;
  units: DashboardUnit[];
  unitId: number | null;
  onUnitChange: (unitId: number | null) => void;
  /** Rows surviving every filter, shown so the lecturer can see the effect. */
  resultCount: number;
}

/**
 * Search and subject filter.
 *
 * The subject list is built from the `units` payload, never from the
 * unit codes appearing in the student rows. A unit with nobody enrolled
 * yet must still be selectable — deriving the list from students would
 * make an empty unit vanish from the dropdown, and the lecturer would
 * have no way to confirm it IS empty rather than missing.
 *
 * Search covers unit code as well as name and student number: a
 * lecturer looking at all subjects usually narrows by typing the code,
 * and assuming they will spot the separate dropdown is optimistic.
 */
export default function StudentsFilterBar({
  search,
  onSearchChange,
  units,
  unitId,
  onUnitChange,
  resultCount,
}: StudentsFilterBarProps) {
  return (
    <div className="flex flex-wrap items-center gap-3">
      <div className="relative min-w-[240px] flex-1">
        <Search
          className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-stone-400"
          aria-hidden="true"
        />

        <input
          type="search"
          value={search}
          onChange={(event) => onSearchChange(event.target.value)}
          placeholder="Search by name, ID or subject..."
          aria-label="Search students"
          className="w-full rounded-xl border border-stone-200 bg-white py-2.5 pl-10 pr-9 text-sm text-stone-900 placeholder:text-stone-400 focus:border-stone-400 focus:outline-none focus:ring-2 focus:ring-stone-200"
        />

        {/* Native type="search" only renders a clear button in some
            browsers, so an explicit one keeps the behaviour consistent. */}
        {search !== "" && (
          <button
            type="button"
            onClick={() => onSearchChange("")}
            aria-label="Clear search"
            className="absolute right-2.5 top-1/2 -translate-y-1/2 rounded-full p-1 text-stone-400 transition hover:bg-stone-100 hover:text-stone-600"
          >
            <X className="h-3.5 w-3.5" aria-hidden="true" />
          </button>
        )}
      </div>

      <div className="flex items-center gap-2">
        <Filter className="h-4 w-4 shrink-0 text-stone-400" aria-hidden="true" />

        <select
          value={unitId === null ? "all" : String(unitId)}
          onChange={(event) =>
            onUnitChange(event.target.value === "all" ? null : Number(event.target.value))
          }
          aria-label="Filter by subject"
          className="rounded-xl border border-stone-200 bg-white px-3 py-2.5 text-sm font-medium text-stone-700 focus:border-stone-400 focus:outline-none focus:ring-2 focus:ring-stone-200"
        >
          <option value="all">All Subjects</option>
          {units.map((unit) => (
            <option key={unit.id} value={unit.id}>
              {unit.unit_code}
            </option>
          ))}
        </select>
      </div>

      {/* aria-live so a screen reader hears the count change as the
          lecturer types, instead of the filtering happening silently. */}
      <p className="text-sm tabular-nums text-stone-400" aria-live="polite">
        {resultCount} result{resultCount === 1 ? "" : "s"}
      </p>
    </div>
  );
}