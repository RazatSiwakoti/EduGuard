import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import axios from "axios";
import { unitService } from "../services/unitService";
import type { CreateUnitRequest, UpdateUnitRequest } from "../types/unit";

const KEY = ["units"];

// Pulls the backend's actual error message out of a failed request when
// available (e.g. "Unit name already exists for this teaching period"),
// falling back to a generic message only if the backend didn't send one.
// This matters specifically for Units, which has real business-rule
// rejections we don't want to hide behind a vague error.
function getErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail;
    if (typeof detail === "string") return detail;
  }
  return "Something went wrong. Please try again.";
}

export function useUnitsList(includeInactive: boolean) {
  return useQuery({
    queryKey: [...KEY, includeInactive],
    queryFn: () => unitService.list(includeInactive),
  });
}

export function useCreateUnit() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: CreateUnitRequest) => unitService.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: KEY });
      toast.success("Unit created successfully");
    },
    onError: (error) => toast.error(getErrorMessage(error)),
  });
}

export function useUpdateUnit() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: UpdateUnitRequest }) =>
      unitService.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: KEY });
      toast.success("Unit updated successfully");
    },
    onError: (error) => toast.error(getErrorMessage(error)),
  });
}

export function useArchiveUnit() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => unitService.archive(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: KEY });
      toast.success("Unit archived");
    },
    onError: (error) => toast.error(getErrorMessage(error)),
  });
}

export function useReactivateUnit() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => unitService.reactivate(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: KEY });
      toast.success("Unit reactivated");
    },
    onError: (error) => toast.error(getErrorMessage(error)),
  });
}

export function useAssignLecturer() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, lecturerId }: { id: number; lecturerId: number }) =>
      unitService.assignLecturer(id, lecturerId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: KEY });
      toast.success("Lecturer assigned");
    },
    onError: (error) => toast.error(getErrorMessage(error)),
  });
}

export function useUnassignLecturer() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => unitService.unassignLecturer(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: KEY });
      toast.success("Lecturer unassigned");
    },
    onError: (error) => toast.error(getErrorMessage(error)),
  });
}