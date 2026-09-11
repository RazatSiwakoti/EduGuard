import api from "./api";
import type { User } from "../types/auth";

// Shared shape for creating any user-management entity
// (admins, lecturers) — both take the same three fields.
export interface CreateUserRequest {
  email: string;
  full_name: string;
  password: string;
}

// Factory for the CRUD pattern shared by Super Admin managing Admins
// and Admin managing Lecturers — both APIs are structurally identical
// (list/create/deactivate/reactivate/delete against a User-shaped
// object), so this exists in one place instead of two copies that
// could quietly drift apart later.
export function createUserManagementService(basePath: string) {
  return {
    list: async (includeInactive: boolean): Promise<User[]> => {
      const response = await api.get<User[]>(basePath, {
        params: { include_inactive: includeInactive },
      });
      return response.data;
    },
    create: async (data: CreateUserRequest): Promise<User> => {
      const response = await api.post<User>(basePath, data);
      return response.data;
    },
    deactivate: async (id: number): Promise<User> => {
      const response = await api.patch<User>(`${basePath}/${id}/deactivate`);
      return response.data;
    },
    reactivate: async (id: number): Promise<User> => {
      const response = await api.patch<User>(`${basePath}/${id}/reactivate`);
      return response.data;
    },
    remove: async (id: number): Promise<{ detail: string }> => {
      const response = await api.delete<{ detail: string }>(
        `${basePath}/${id}`
      );
      return response.data;
    },
  };
}