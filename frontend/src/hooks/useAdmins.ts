import { adminService } from "../services/adminService";
import { createUserManagementHooks } from "./createUserManagementHooks";

// Same hook names as before — SuperAdminDashboard.tsx doesn't need any changes.
export const {
  useList: useAdminsList,
  useCreate: useCreateAdmin,
  useDeactivate: useDeactivateAdmin,
  useReactivate: useReactivateAdmin,
  useDelete: useDeleteAdmin,
} = createUserManagementHooks("admins", adminService, "Admin");