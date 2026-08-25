import api from "./api";
import type { DashboardUnit } from "../types/dashboard";

/**
 * The lecturer's own units, without any cohort data attached.
 *
 * Separate from dashboardService because the two answer different
 * questions. /lecturer/dashboard returns every enrolled student and
 * their criterion scores — the right payload for the analytics page,
 * and a wasteful one when all you need is a list of unit codes for a
 * navigation list or a page header.
 *
 * Reuses the DashboardUnit type rather than declaring a near-identical
 * one, since the backend deliberately serves both endpoints from the
 * same _unit_to_dict helper.
 */
export const lecturerUnitService = {
  list: async (): Promise<DashboardUnit[]> => {
    const res = await api.get<DashboardUnit[]>("/lecturer/units");
    return res.data;
  },
};