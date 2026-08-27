import api from "./api";
import type { AnalysisRunResult, UnitAnalysisResult } from "../types/analysis";

/**
 * Run Analysis (section E1).
 *
 * Scoped server-side to the signed-in lecturer. The client never sends
 * a lecturer id — this endpoint writes risk scores for a whole cohort,
 * so ownership is resolved in SQL from the validated JWT.
 */
export const analysisService = {
  /**
   * What a run WOULD cover, without running anything.
   *
   * Feeds the confirmation dialog: a lecturer about to re-score a
   * cohort should be told how many students and how many standing
   * review decisions are at stake BEFORE they press the button.
   */
  preview: async (unitId?: number | null): Promise<UnitAnalysisResult[]> => {
    const res = await api.get<UnitAnalysisResult[]>("/lecturer/analysis/preview", {
      params: unitId ? { unit_id: unitId } : undefined,
    });
    return res.data;
  },

  /**
   * Recompute rule + ML + hybrid. Omit unitId to cover every active
   * unit the lecturer teaches.
   *
   * No timeout override is set here: the axios instance has none, and
   * a cohort of a few hundred takes seconds, not minutes. If that ever
   * changes the fix is a background job, not a longer timeout.
   */
  run: async (
    unitId?: number | null,
    checkpointWeek?: number | null,
  ): Promise<AnalysisRunResult> => {
    const res = await api.post<AnalysisRunResult>(
      "/lecturer/analysis/run",
      null,
      {
        params: {
          ...(unitId ? { unit_id: unitId } : {}),
          ...(checkpointWeek ? { checkpoint_week: checkpointWeek } : {}),
        },
      },
    );
    return res.data;
  },
};