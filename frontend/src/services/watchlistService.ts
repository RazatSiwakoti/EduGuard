import api from "./api";

export interface WatchlistItem {
  student_id: number;
  student_number: string;
  student_name: string;
  unit_id: number;
  unit_code: string;
  added_at: string | null;
  reason: string | null;
}

export const watchlistService = {
  list: async () => (await api.get<WatchlistItem[]>("/lecturer/watchlist")).data,
  add: async (studentId: number, unitId: number) =>
    (await api.post<WatchlistItem>("/lecturer/watchlist", { student_id: studentId, unit_id: unitId })).data,
  remove: async (studentId: number, unitId: number) => {
    await api.delete("/lecturer/watchlist", { params: { student_id: studentId, unit_id: unitId } });
  },
};
