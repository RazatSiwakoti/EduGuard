import { createUserManagementService } from "./userManagementService";

// Admin -> Lecturer lifecycle management
export const lecturerService = createUserManagementService(
  "/admin/lecturers"
);