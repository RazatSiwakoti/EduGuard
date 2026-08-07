import { createUserManagementService } from "./userManagementService";

// Super Admin -> Admin lifecycle management
export const adminService = createUserManagementService(
  "/super-admin/admins"
);