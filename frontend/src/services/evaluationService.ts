import api from "./api";

export interface ModelEvaluation {
  coverage: { resolved: number; total: number; percentage: number };
  confusion_matrix: { tp: number; fp: number; tn: number; fn: number; tier_vs_outcome: Record<string, Record<string, number>> };
  metrics: Record<string, number | boolean | string>;
  per_engine_metrics: Record<string, Record<string, number | boolean | string>>;
  lead_time: number[];
  calibration: { predicted: number; observed: number }[];
}

export const evaluationService = {
  get: async (checkpointWeek = 8, unitIds: number[] = []) => {
    const response = await api.get<ModelEvaluation>("/admin/model", {
      params: { checkpoint_week: checkpointWeek, unit_ids: unitIds },
    });
    return response.data;
  },
};
