import api from "./api";
import type { Unit, CreateUnitRequest, UpdateUnitRequest } from "../types/unit";

const BASE = "/admin/units";

export const unitService = {
  list: async (includeInactive: boolean): Promise<Unit[]> => {
    const res = await api.get<Unit[]>(BASE, {
      params: { include_inactive: includeInactive },
    });
    return res.data;
  },
  create: async (data: CreateUnitRequest): Promise<Unit> => {
    const res = await api.post<Unit>(BASE, data);
    return res.data;
  },
  update: async (id: number, data: UpdateUnitRequest): Promise<Unit> => {
    const res = await api.patch<Unit>(`${BASE}/${id}`, data);
    return res.data;
  },
  // "Delete" always archives — there is no hard-delete endpoint for units.
  archive: async (id: number): Promise<{ detail: string }> => {
    const res = await api.delete<{ detail: string }>(`${BASE}/${id}`);
    return res.data;
  },
  reactivate: async (id: number): Promise<Unit> => {
    const res = await api.patch<Unit>(`${BASE}/${id}/reactivate`);
    return res.data;
  },
  assignLecturer: async (id: number, lecturerId: number): Promise<Unit> => {
    const res = await api.patch<Unit>(`${BASE}/${id}/assign-lecturer`, {
      lecturer_id: lecturerId,
    });
    return res.data;
  },
  unassignLecturer: async (id: number): Promise<Unit> => {
    const res = await api.patch<Unit>(`${BASE}/${id}/unassign-lecturer`);
    return res.data;
  },
};