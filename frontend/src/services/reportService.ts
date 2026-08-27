import api from "./api";
import type { ReportCheckpoint, ReportResponse } from "../types/reports";

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

  /**
   * The checkpoint weeks this unit has actually been analysed at.
   *
   * The week selector is built from these rather than from a fixed
   * 1-14 range: offering thirteen weeks that all render "no analysis
   * has been run" is a menu of dead ends.
   */
  getCheckpoints: async (unitId: number): Promise<ReportCheckpoint[]> => {
    const res = await api.get<ReportCheckpoint[]>(
      `/lecturer/reports/unit/${unitId}/checkpoints`,
    );
    return res.data;
  },

  /**
   * The PDF, as a blob.
   *
   * WHY NOT A PLAIN <a href>. The API is authenticated with a Bearer
   * token held in localStorage and attached by the axios interceptor.
   * A link navigation carries cookies, not headers, so it would arrive
   * unauthenticated and 401 — and the browser would render the JSON
   * error as a downloaded file called "pdf".
   *
   * So the request goes through the same axios instance as everything
   * else, and the bytes are handed to the user via an object URL.
   */
  downloadPdf: async (
    unitId: number,
    checkpointWeek?: number | null,
  ): Promise<{ blob: Blob; filename: string }> => {
    const res = await api.get<Blob>(`/lecturer/reports/unit/${unitId}/pdf`, {
      params: checkpointWeek ? { checkpoint_week: checkpointWeek } : undefined,
      responseType: "blob",
    });

    return {
      blob: res.data,
      // The server already names the file. Parsing its header rather
      // than rebuilding the name here keeps ONE naming scheme: a second
      // one in the browser would drift the first time either changed.
      filename:
        filenameFrom(res.headers["content-disposition"]) ?? "report.pdf",
    };
  },
};

/** Pulls `filename="…"` out of a Content-Disposition header. */
function filenameFrom(header: unknown): string | null {
  if (typeof header !== "string") return null;
  const match = /filename\*?=(?:UTF-8'')?"?([^";]+)"?/i.exec(header);
  return match ? decodeURIComponent(match[1]) : null;
}