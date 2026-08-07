import type { UserRole } from "../types/auth";

// Central place mapping each role to its landing page after login.
// Add a case here whenever a new role-specific dashboard is built —
// keeps this logic in one spot instead of duplicated across pages.
export function getRedirectPath(role: UserRole): string {
  switch (role) {
    case "super_admin":
      return "/super-admin";
    case "admin":
      return "/admin"; // placeholder until AdminDashboard exists
    case "lecturer":
      return "/dashboard"; // placeholder until LecturerDashboard exists
    case "student":
      return "/dashboard"; // placeholder until StudentDashboard exists
    default:
      return "/dashboard";
  }
}