import api from "./api";
import type { Criterion } from "../types/criteria";

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
};