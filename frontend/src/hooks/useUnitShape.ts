import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import axios from "axios";
import { unitShapeService } from "../services/unitShapeService";
import type { UnitShapeInput } from "../types/unitShape";

/**
 * React Query bindings for the unit-composition API (T1 + T2).
 *
 * WHY THE ERROR HANDLING HERE IS NOT THE useUnits.ts PATTERN
 * ----------------------------------------------------------
 * `useUnits` toasts every failure. That is right for a list screen
 * where the error has nowhere else to go. It is wrong here, because
 * this form's two expected refusals each have a place on screen and an
 * action attached to them:
 *
 *   400  a composition rule was broken -> printed under the total, next
 *        to the number the coordinator has to change
 *   409  the unit is locked            -> opens the unlock dialog
 *
 * A toast for either is a message that disappears while the user is
 * still looking for what to fix. So the hook lets those two through
 * untouched and toasts only the unexpected ones: a 500, a dropped
 * connection, an expired token.
 *
 * 422 is deliberately in the toasted group. A malformed payload from a
 * form that validates before it submits is a bug in this file, not
 * something the coordinator can correct.
 */

export const UNIT_SHAPE_KEY = "unit-shape";

export function unitShapeKey(unitId: number) {
  return [UNIT_SHAPE_KEY, unitId];
}

/** HTTP status of a failed request, or null if it never reached the server. */
export function statusOf(error: unknown): number | null {
  return axios.isAxiosError(error) ? error.response?.status ?? null : null;
}

/**
 * The backend's own message. FastAPI puts it in `detail`, and for a
 * 422 that is a list of validation objects rather than a string — hence
 * the type check instead of blindly rendering it.
 */
export function detailOf(error: unknown, fallback: string): string {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail;
    if (typeof detail === "string") return detail;
  }
  return fallback;
}

/**
 * One unit's shape, marks, pass marks and lock state.
 *
 * `enabled` exists because this is called from two places with very
 * different appetites: the dialog wants it immediately, and the row
 * badge wants it for every unit in the table. Passing `false` keeps a
 * closed dialog from fetching.
 *
 * NOTE ON COST: the badge mounts one of these per row, and each is a
 * separate unit id and therefore a separate request — React Query
 * dedupes identical keys, not similar ones. `staleTime` keeps the table
 * from refetching them on every focus; a `configured` flag on the units
 * list would remove the fan-out entirely and is worth adding when that
 * endpoint is next touched.
 */
export function useUnitShape(
  unitId: number | null,
  enabled = true,
  staleTime = 60_000
) {
  return useQuery({
    queryKey: unitShapeKey(unitId ?? 0),
    queryFn: () => unitShapeService.get(unitId as number),
    enabled: enabled && unitId !== null,
    // The badge and the dialog share this key, and share the cached
    // answer — which is what makes the dialog paint instantly. They do
    // NOT share the tolerance for a stale one: a badge a minute out of
    // date is cosmetic, while a stale `lock` opens an editable form on
    // a unit that locked in the meantime and turns the first save into
    // a 409. So the dialog passes 0 and re-reads on open.
    staleTime,
  });
}

/** What an unlock will cost. Fetched only while the dialog is open. */
export function useUnlockPreview(unitId: number | null, enabled: boolean) {
  return useQuery({
    queryKey: ["unit-unlock-preview", unitId ?? 0],
    queryFn: () => unitShapeService.unlockPreview(unitId as number),
    enabled: enabled && unitId !== null,
    // Never cached: the cost is a live count of valid verdicts, and a
    // stale number here is a sentence that misstates the damage.
    staleTime: 0,
    gcTime: 0,
  });
}

export function useReplaceUnitShape(unitId: number | null) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (body: UnitShapeInput) =>
      unitShapeService.replace(unitId as number, body),
    onSuccess: () => {
      // The shape, the badge and the lock state all come from the same
      // GET, so one invalidation refreshes every one of them.
      queryClient.invalidateQueries({ queryKey: unitShapeKey(unitId ?? 0) });
      queryClient.invalidateQueries({ queryKey: ["unit-unlock-preview", unitId ?? 0] });
      toast.success("Criteria saved");
    },
    onError: (error) => {
      const status = statusOf(error);
      // 400 and 409 are rendered in the form and the unlock dialog
      // respectively — see the file docstring.
      if (status === 400 || status === 409) return;
      toast.error(detailOf(error, "Could not save the criteria. Please try again."));
    },
  });
}

export function useUnlockUnitShape(unitId: number | null) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (unitCode: string) =>
      unitShapeService.unlock(unitId as number, unitCode),
    onSuccess: (result) => {
      queryClient.invalidateQueries({ queryKey: unitShapeKey(unitId ?? 0) });
      // The server's own sentence: it distinguishes "unlocked for one
      // edit" from "this unit was already in draft, nothing to unlock",
      // and only the server can tell those apart.
      toast.success(result.detail);
    },
    onError: (error) => {
      // 400 here means the typed unit code did not match, which belongs
      // under the input the user is still looking at.
      if (statusOf(error) === 400) return;
      toast.error(detailOf(error, "Could not unlock this unit."));
    },
  });
}