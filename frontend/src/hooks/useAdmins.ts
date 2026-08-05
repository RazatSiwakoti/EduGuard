import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import * as adminService from "../services/adminService";
import type { CreateAdminRequest } from "../types/admin";

// Shared cache key for the admin list — every mutation below invalidates
// this so the table refetches automatically after any change, instead of
// each mutation manually patching local state.
const ADMINS_KEY = ["admins"];

export function useAdminsList(includeInactive: boolean) {
  return useQuery({
    queryKey: [...ADMINS_KEY, includeInactive],
    queryFn: () => adminService.listAdmins(includeInactive),
  });
}

export function useCreateAdmin() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: CreateAdminRequest) => adminService.createAdmin(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ADMINS_KEY });
      toast.success("Admin created successfully");
    },
    onError: () => {
      toast.error("Failed to create admin");
    },
  });
}

export function useDeactivateAdmin() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (adminId: number) => adminService.deactivateAdmin(adminId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ADMINS_KEY });
      toast.success("Admin deactivated");
    },
    onError: () => {
      toast.error("Failed to deactivate admin");
    },
  });
}

export function useReactivateAdmin() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (adminId: number) => adminService.reactivateAdmin(adminId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ADMINS_KEY });
      toast.success("Admin reactivated");
    },
    onError: () => {
      toast.error("Failed to reactivate admin");
    },
  });
}

export function useDeleteAdmin() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (adminId: number) => adminService.deleteAdmin(adminId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ADMINS_KEY });
      toast.success("Admin deleted successfully");
    },
    onError: () => {
      toast.error("Failed to delete admin");
    },
  });
}