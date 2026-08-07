import type { User } from "./auth";

export type UnitStatus = "ASSIGNED" | "UNASSIGNED";

export interface Unit {
  id: number;
  unit_code: string;
  unit_name: string;
  start_date: string;
  year: number | null;
  teaching_period: string | null;
  level: string | null;
  lecturer_id: number | null;
  status: UnitStatus;
  is_active: boolean;
  lecturer: User | null;
  enrolled_count: number;
}

// Body for POST /admin/units
export interface CreateUnitRequest {
  unit_code: string;
  unit_name: string;
  start_date: string;
  year?: number | null;
  teaching_period?: string | null;
  level?: string | null;
  lecturer_id?: number | null;
}

// Body for PATCH /admin/units/{id} — only these 3 fields are editable
export interface UpdateUnitRequest {
  unit_name: string;
  start_date: string;
  level?: string | null;
}