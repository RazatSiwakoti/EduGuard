import api from "./api";
import type { Criterion } from "../types/criteria";
import type { LecturerUnitShape, ThresholdUpdate } from "../types/unitShape";

/**
 * Assessment criteria for one unit.
 *
 * Every route here is nested under a unit id because criteria are
 * defined per unit — that is exactly what lets ICT729 with four
 * assignments and ICT301 with two quizzes share one ingestion pipeline.
 *
 * The backend gates these on "you are the assigned lecturer for this
 * unit", not merely "you are a lecturer", so a wrong unit id returns
 * 403 rather than someone else's criteria.
 */
export const criteriaService = {
  list: async (unitId: number): Promise<Criterion[]> => {
    const res = await api.get<Criterion[]>(`/units/${unitId}/criteria`);
    return res.data;
  },

  /**
   * The coordinator's shape plus the lecturer's pass bars, in ONE
   * request (section T4).
   *
   * Deliberately not two calls. The composition table and the sliders
   * are views of the same rows, and fetching them separately means a
   * first paint where the pass marks shown next to each item were
   * computed from a threshold the sliders have not loaded yet.
   */
  shape: async (unitId: number): Promise<LecturerUnitShape> => {
    const res = await api.get<LecturerUnitShape>(`/units/${unitId}/criteria/shape`);
    return res.data;
  },

  /**
   * Move the pass bar for one or both adjustable categories.
   *
   * Returns the whole shape back, not just the thresholds — the derived
   * pass mark beside every item changes with the bar, so anything less
   * would leave the table showing numbers the slider has already
   * invalidated.
   */
  updateThresholds: async (
    unitId: number,
    changes: ThresholdUpdate,
  ): Promise<LecturerUnitShape> => {
    const res = await api.patch<LecturerUnitShape>(
      `/units/${unitId}/criteria/thresholds`,
      changes,
    );
    return res.data;
  },
};