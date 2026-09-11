import { useMutation } from "@tanstack/react-query";
import { toast } from "sonner";
import { useAuth } from "../context/AuthContext";
import { changePassword, deleteAvatar, updateProfile, uploadAvatar } from "../services/authService";

export function useUpdateProfile() {
  const { applyUser } = useAuth();
  return useMutation({ mutationFn: (fullName: string) => updateProfile(fullName), onSuccess: applyUser });
}

export function useChangePassword() {
  return useMutation({
    mutationFn: ({ currentPassword, newPassword }: { currentPassword: string; newPassword: string }) =>
      changePassword(currentPassword, newPassword),
    onSuccess: () => toast.success("Password changed successfully."),
  });
}

export function useUploadAvatar() {
  const { applyUser } = useAuth();
  return useMutation({ mutationFn: (dataUrl: string) => uploadAvatar(dataUrl), onSuccess: applyUser });
}

export function useDeleteAvatar() {
  const { applyUser } = useAuth();
  return useMutation({ mutationFn: () => deleteAvatar(), onSuccess: applyUser });
}
