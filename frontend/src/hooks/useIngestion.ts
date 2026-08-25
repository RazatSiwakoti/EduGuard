import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import axios from "axios";
import { ingestionService } from "../services/ingestionService";
import type { BulkIngestionMapping, ManualEntryCreate } from "../types/ingestion";

/**
 * Pulls the backend's real error message out of a failed request.
 *
 * Ingestion has genuinely informative rejections — "File must be .csv,
 * .xlsx, or .xls", "You are not the assigned lecturer for this unit",
 * "Invalid mapping JSON" — and hiding those behind a generic message
 * would leave a lecturer with no idea what to change.
 */
function getErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail;
    if (typeof detail === "string") return detail;
    // FastAPI validation errors arrive as an array of objects.
    if (Array.isArray(detail) && detail.length > 0) {
      const first = detail[0];
      if (typeof first?.msg === "string") return first.msg;
    }
  }
  return "Something went wrong. Please try again.";
}

/**
 * Reads a file's columns without storing anything.
 *
 * A mutation rather than a query despite being read-only: it is
 * triggered by an explicit user action with a file as its input, not by
 * a component rendering. Modelling it as a query would mean inventing a
 * cache key for a File object, which has no stable identity.
 */
export function usePreviewFile(unitId: number) {
  return useMutation({
    mutationFn: (file: File) => ingestionService.preview(unitId, file),
    onError: (error) => toast.error(getErrorMessage(error)),
  });
}

/**
 * Uploads the file with its mapping, storing the data and running the
 * risk analysis for every student it touched.
 *
 * On success it invalidates BOTH the dashboard and the units list. The
 * dashboard's risk numbers have changed, and so has each unit's
 * enrolled_count — leaving either cached would show a lecturer stale
 * figures immediately after they watched an import succeed.
 *
 * Deliberately no success toast here: the wizard replaces the whole
 * screen with a detailed result report, and a toast saying "done" over
 * the top of a report that says considerably more is just noise.
 */
export function useBulkImport(unitId: number) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ file, mapping }: { file: File; mapping: BulkIngestionMapping }) =>
      ingestionService.bulk(unitId, file, mapping),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["lecturer-dashboard"] });
      queryClient.invalidateQueries({ queryKey: ["lecturer-units"] });
    },
    onError: (error) => toast.error(getErrorMessage(error)),
  });
}

/**
 * Adds one student by hand and scores them immediately.
 *
 * Same cache invalidation as bulk import — a single new student still
 * changes the dashboard's counts and the unit's enrolled_count, and
 * leaving either cached would show stale figures right after the
 * lecturer watched the student get added.
 *
 * No success toast: the form replaces itself with the engine's verdict
 * for that student, which says far more than "saved" would.
 */
export function useManualEntry(unitId: number) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: ManualEntryCreate) =>
      ingestionService.manual(unitId, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["lecturer-dashboard"] });
      queryClient.invalidateQueries({ queryKey: ["lecturer-units"] });
    },
    onError: (error) => toast.error(getErrorMessage(error)),
  });
}