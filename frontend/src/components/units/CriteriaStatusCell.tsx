import { useUnitShape } from "../../hooks/useUnitShape";

interface CriteriaStatusCellProps {
  unitId: number;
}

/**
 * The "not configured" badge on a Units row.
 *
 * WHAT `configured` MEANS, AND WHY IT IS NOT "HAS ANY CRITERIA"
 * ------------------------------------------------------------
 * Every unit is born with attendance and Moodle criteria from
 * `seed_default_criteria`. A badge keyed on "does this unit have
 * criteria" would therefore be true from the moment the unit was
 * created and would never appear — a badge nobody ever sees. The server
 * computes `configured` from the coordinator's own decisions only: at
 * least one assessment, or tutorials switched on.
 *
 * COST, STATED RATHER THAN HIDDEN
 * -------------------------------
 * Each row queries its own unit id, so a table of N units issues N
 * requests. React Query dedupes identical keys, not similar ones, and
 * there is no bulk endpoint — `GET /admin/units` returns nothing about
 * criteria. `useUnitShape` sets a 60s `staleTime` so the table does not
 * re-fan-out on every window focus. Adding `configured` to the units
 * list response would remove the fan-out outright and is the right fix
 * the next time that endpoint is touched.
 */
export default function CriteriaStatusCell({ unitId }: CriteriaStatusCellProps) {
  const { data, isLoading, isError } = useUnitShape(unitId);

  if (isLoading) {
    return <span className="text-xs text-stone-400">…</span>;
  }

  // An unreadable status is not a "not configured" status. Saying
  // "unknown" is worse-looking and more honest than a badge that tells
  // a coordinator to go and configure a unit that may already be done.
  if (isError || !data) {
    return <span className="text-xs text-stone-400">unknown</span>;
  }

  if (!data.configured) {
    return (
      <span
        className="whitespace-nowrap rounded-full bg-amber-50 px-2 py-0.5 text-xs font-medium text-amber-700"
        data-testid={`criteria-badge-${unitId}`}
      >
        Not configured
      </span>
    );
  }

  return (
    <span
      className="whitespace-nowrap text-xs text-stone-600"
      data-testid={`criteria-badge-${unitId}`}
    >
      {data.total_percentage}%
      {data.lock.locked && (
        <span className="ml-1 rounded bg-stone-100 px-1.5 py-0.5 text-[11px] font-medium text-stone-600">
          locked
        </span>
      )}
    </span>
  );
}