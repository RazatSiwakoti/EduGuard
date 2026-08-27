import api from "./api";
import type { ReportResponse } from "../types/reports";

/**
 * The Reports endpoint (Phase 7.9).
 *
 * One call returns the whole finished document. There is deliberately
 * no /distribution, /criteria or /at-risk: splitting it would hand the
 * browser three payloads to stitch together and reopen the divergence
 * between the screen and the PDF that computing once, server-side, is
 * there to close.
 *
 * Scoped server-side to the signed-in lecturer. A unit the caller does
 * not teach returns 404, never 403 — a 403 would confirm it exists.
 */
export const reportService = {
  getUnitReport: async (
    unitId: number,
    checkpointWeek?: number | null,
  ): Promise<ReportResponse> => {
    const res = await api.get<ReportResponse>(
      `/lecturer/reports/unit/${unitId}`,
      {
        params: checkpointWeek ? { checkpoint_week: checkpointWeek } : undefined,
      },
    );
    return res.data;
  },
};