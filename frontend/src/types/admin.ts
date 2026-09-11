// Admins returned by the Super Admin endpoints share the exact same shape
// as the logged-in User (id, email, full_name, role, is_active, etc.),
// so we reuse that type rather than duplicating the field list.
export type { User as AdminUser } from "./auth";

// Body sent to POST /super-admin/admins
export interface CreateAdminRequest {
  email: string;
  full_name: string;
  password: string;
}