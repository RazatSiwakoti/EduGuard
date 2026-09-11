import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import type { createUserManagementService, CreateUserRequest } from "../services/userManagementService";

type UserManagementService = ReturnType<typeof createUserManagementService>;

// Generates the useList/useCreate/useDeactivate/useReactivate/useDelete
// hook set for a given service + cache key + display label (label is
// only used in toast text, e.g. "Admin" vs "Lecturer").
export function createUserManagementHooks(
  queryKeyName: string,
  service: UserManagementService,
  label: string
) {
  const KEY = [queryKeyName];

  function useList(includeInactive: boolean) {
    return useQuery({
      queryKey: [...KEY, includeInactive],
      queryFn: () => service.list(includeInactive),
    });
  }

  function useCreate() {
    const queryClient = useQueryClient();
    return useMutation({
      mutationFn: (data: CreateUserRequest) => service.create(data),
      onSuccess: () => {
        queryClient.invalidateQueries({ queryKey: KEY });
        toast.success(`${label} created successfully`);
      },
      onError: () => toast.error(`Failed to create ${label.toLowerCase()}`),
    });
  }

  function useDeactivate() {
    const queryClient = useQueryClient();
    return useMutation({
      mutationFn: (id: number) => service.deactivate(id),
      onSuccess: () => {
        queryClient.invalidateQueries({ queryKey: KEY });
        toast.success(`${label} deactivated`);
      },
      onError: () =>
        toast.error(`Failed to deactivate ${label.toLowerCase()}`),
    });
  }

  function useReactivate() {
    const queryClient = useQueryClient();
    return useMutation({
      mutationFn: (id: number) => service.reactivate(id),
      onSuccess: () => {
        queryClient.invalidateQueries({ queryKey: KEY });
        toast.success(`${label} reactivated`);
      },
      onError: () =>
        toast.error(`Failed to reactivate ${label.toLowerCase()}`),
    });
  }

  function useDelete() {
    const queryClient = useQueryClient();
    return useMutation({
      mutationFn: (id: number) => service.remove(id),
      onSuccess: () => {
        queryClient.invalidateQueries({ queryKey: KEY });
        toast.success(`${label} deleted successfully`);
      },
      onError: () => toast.error(`Failed to delete ${label.toLowerCase()}`),
    });
  }

  return { useList, useCreate, useDeactivate, useReactivate, useDelete };
}