import api from "./api";
import type { LecturerDashboardResponse } from "../types/dashboard";

/**
 * Read-only access to the lecturer analytics dashboard.
 *
 * Exactly one call. Both dashboard filters (unit and risk level) are
 * applied client-side against this payload, so changing a filter never
 * triggers another request — that is what makes the cross-filtering
 * feel instant rather than laggy.
 */
export const dashboardService = {
  /**
   * @param checkpointWeek Which checkpoint's risk picture to load.
   *   Only week 8 is populated today; the parameter exists so adding
   *   more checkpoints later needs no change to this service.
   */
  get: async (checkpointWeek = 8): Promise<LecturerDashboardResponse> => {
    const res = await api.get<LecturerDashboardResponse>("/lecturer/dashboard", {
      params: { checkpoint_week: checkpointWeek },
    });
    return res.data;
  },
};