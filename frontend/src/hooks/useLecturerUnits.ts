import { useQuery } from "@tanstack/react-query";
import { lecturerUnitService } from "../services/lecturerUnitService";
import { criteriaService } from "../services/criteriaService";

const UNITS_KEY = ["lecturer-units"];
const CRITERIA_KEY = ["unit-criteria"];

/**
 * Every unit the signed-in lecturer is assigned to.
 *
 * staleTime is deliberately long: unit assignment is an administrative
 * action that happens once a semester, not something that changes while
 * a lecturer is working. Refetching it on every navigation between the
 * units list and a unit workspace would be pure waste.
 */
export function useLecturerUnits() {
  return useQuery({
    queryKey: UNITS_KEY,
    queryFn: () => lecturerUnitService.list(),
    staleTime: 5 * 60_000,
    refetchOnWindowFocus: false,
  });
}

/**
 * One unit's assessment criteria.
 *
 * `enabled` guards against React Query firing with `unitId: 0`, which
 * is what a failed `Number(params.unitId)` parse produces. Without the
 * guard a malformed URL like /units/abc would fire a request for unit 0
 * and surface a 404 as though the app were broken.
 */
export function useUnitCriteria(unitId: number) {
  return useQuery({
    queryKey: [...CRITERIA_KEY, unitId],
    queryFn: () => criteriaService.list(unitId),
    enabled: Number.isFinite(unitId) && unitId > 0,
    staleTime: 60_000,
    refetchOnWindowFocus: false,
  });
}