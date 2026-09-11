import { lecturerService } from "../services/lecturerService";
import { createUserManagementHooks } from "./createUserManagementHooks";

export const {
  useList: useLecturersList,
  useCreate: useCreateLecturer,
  useDeactivate: useDeactivateLecturer,
  useReactivate: useReactivateLecturer,
  useDelete: useDeleteLecturer,
} = createUserManagementHooks("lecturers", lecturerService, "Lecturer");