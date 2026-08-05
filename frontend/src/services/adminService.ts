import api from "./api";
import type { AdminUser, CreateAdminRequest } from "../types/admin";

// GET /super-admin/admins?include_inactive=true|false
export async function listAdmins(
  includeInactive: boolean
): Promise<AdminUser[]> {
  const response = await api.get<AdminUser[]>("/super-admin/admins", {
    params: { include_inactive: includeInactive },
  });
  return response.data;
}

// POST /super-admin/admins
// ASSUMPTION: returns the created admin object, matching the pattern of
// every other mutation endpoint here. Confirm against Swagger — if it
// instead returns {detail: string}, change the return type to match.
export async function createAdmin(
  data: CreateAdminRequest
): Promise<AdminUser> {
  const response = await api.post<AdminUser>("/super-admin/admins", data);
  return response.data;
}

// PATCH /super-admin/admins/{admin_id}/deactivate
export async function deactivateAdmin(adminId: number): Promise<AdminUser> {
  const response = await api.patch<AdminUser>(
    `/super-admin/admins/${adminId}/deactivate`
  );
  return response.data;
}

// PATCH /super-admin/admins/{admin_id}/reactivate
export async function reactivateAdmin(adminId: number): Promise<AdminUser> {
  const response = await api.patch<AdminUser>(
    `/super-admin/admins/${adminId}/reactivate`
  );
  return response.data;
}

// DELETE /super-admin/admins/{admin_id}
export async function deleteAdmin(
  adminId: number
): Promise<{ detail: string }> {
  const response = await api.delete<{ detail: string }>(
    `/super-admin/admins/${adminId}`
  );
  return response.data;
}