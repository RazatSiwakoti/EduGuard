import { useQuery } from "@tanstack/react-query";
import { reportService } from "../services/reportService";

const REPORT_KEY = ["lecturer-report"];

/**
 * One unit's report at one checkpoint.
 *
 * `enabled` guards against firing with a null unit before the lecturer
 * has picked one, and against `unitId: 0`, which is what a failed
 * Number() parse produces.
 *
 * staleTime is long. A report is a snapshot of an analysis run, and
 * analysis runs are a deliberate action a lecturer takes — not
 * something that changes while they read the page. Refetching on focus
 * would mean the figures a lecturer is quoting in a meeting silently
 * change under them, which is worse than being a minute out of date.
 * The `last_analysed_at` field and the staleness caveat are how age is
 * communicated, not a refetch.
 */
export function useUnitReport(
  unitId: number | null,
  checkpointWeek?: number | null,
) {
  return useQuery({
    queryKey: [...REPORT_KEY, unitId, checkpointWeek ?? null],
    queryFn: () => reportService.getUnitReport(unitId!, checkpointWeek),
    enabled: Number.isFinite(unitId) && (unitId ?? 0) > 0,
    staleTime: 5 * 60_000,
    refetchOnWindowFocus: false,
    // A 404 here means "you do not teach this unit", which retrying
    // cannot fix. Retrying it three times just delays the message.
    retry: false,
  });
}