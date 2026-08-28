import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import axios from "axios";
import { criteriaService } from "../services/criteriaService";
import { unitShapeService } from "../services/unitShapeService";
import type {
  LecturerUnitShape,
  ThresholdUpdate,
  UnitShape,
  UnitShapeInput,
} from "../types/unitShape";

const SHAPE_KEY = ["unit-shape"];

/**
 * Pulls the backend's own sentence out of a failed request.
 *
 * It matters more here than almost anywhere else in this app: a
 * threshold refusal is never generic. "Threshold cannot be set below
 * 45% (proposed: 30%)" tells a lecturer exactly which number to change;
 * "Something went wrong" tells them the app is broken.
 */
export function getThresholdErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail;
    if (typeof detail === "string") return detail;
  }
  return "Couldn't save the pass mark. Please try again.";
}

export const UNIT_SHAPE_KEY = "unit-shape";
export function unitShapeKey(unitId: number) {
  return [UNIT_SHAPE_KEY, unitId];
}

export function statusOf(error: unknown): number | null {
  return axios.isAxiosError(error) ? error.response?.status ?? null : null;
}

export function detailOf(error: unknown, fallback: string): string {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail;
    if (typeof detail === "string") return detail;
  }
  return fallback;
}

/**
 * What the coordinator set for this unit, and where the bars sit.
 *
 * `staleTime: 0`. The badge-style caching used elsewhere in this app is
 * wrong for this screen: the shape can change under a lecturer at any
 * time (the coordinator owns it through a different surface entirely),
 * and a stale read means sliders rendered against percentages that no
 * longer exist and pass marks that are quietly wrong. One extra request
 * per visit is the correct price.
 */
export function useUnitShape(unitId: number): ReturnType<typeof useQuery<LecturerUnitShape>>;
export function useUnitShape(
  unitId: number | null,
  enabled?: boolean,
  staleTime?: number,
): ReturnType<typeof useQuery<UnitShape>>;
export function useUnitShape(
  unitId: number | null,
  enabled?: boolean,
  staleTime?: number,
) {
  const legacy = enabled !== undefined || staleTime !== undefined;
  return useQuery({
    queryKey: legacy ? unitShapeKey(unitId ?? 0) : [...SHAPE_KEY, unitId],
    queryFn: () => legacy
      ? unitShapeService.get(unitId as number)
      : criteriaService.shape(unitId as number),
    enabled: unitId !== null && Number.isFinite(unitId) && unitId > 0,
    staleTime: legacy ? staleTime : 0,
    refetchOnWindowFocus: legacy ? undefined : false,
  });
}

export function useUnlockPreview(unitId: number | null, enabled: boolean) {
  return useQuery({
    queryKey: ["unit-unlock-preview", unitId ?? 0],
    queryFn: () => unitShapeService.unlockPreview(unitId as number),
    enabled: enabled && unitId !== null,
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
      queryClient.invalidateQueries({ queryKey: unitShapeKey(unitId ?? 0) });
      queryClient.invalidateQueries({
        queryKey: ["unit-unlock-preview", unitId ?? 0],
      });
      toast.success("Criteria saved");
    },
    onError: (error) => {
      const status = statusOf(error);
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
      toast.success(result.detail);
    },
    onError: (error) => {
      if (statusOf(error) === 400) return;
      toast.error(detailOf(error, "Could not unlock this unit."));
    },
  });
}

/**
 * Moving the pass bar.
 *
 * INVALIDATES EVERYTHING, like the analysis run does, and for the same
 * reason. `calculate_badness(actual, threshold)` reads the bar
 * directly, so lowering it changes every rule-based score in the unit —
 * which changes the blend, the tiers, the dashboard charts, the
 * students table and the report. Invalidating only this page would
 * leave a lecturer looking at an at-risk count that no longer follows
 * from the bar they can see on screen.
 *
 * The server writes the returned shape straight into the cache first,
 * so the sliders and the derived pass marks settle immediately rather
 * than flickering through a refetch.
 */
export function useUpdateThresholds(unitId: number) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (changes: ThresholdUpdate) =>
      criteriaService.updateThresholds(unitId, changes),
    onSuccess: (shape) => {
      queryClient.setQueryData([...SHAPE_KEY, unitId], shape);
      queryClient.invalidateQueries();
    },
  });
}