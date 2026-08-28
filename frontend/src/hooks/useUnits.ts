import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import axios from "axios";
import { unitService } from "../services/unitService";
import { useAuth } from "../context/AuthContext";
import type { CreateUnitRequest, UpdateUnitRequest } from "../types/unit";

const KEY = ["units"];

/**
 * Re-reads /auth/me after any mutation that can change WHO HOLDS A UNIT
 * — T5.
 *
 * An admin assigning a unit to themselves becomes "also a lecturer" in
 * that instant, and archiving their last unit stops them being one. The
 * sidebar and the landing redirect both read `holds_units` off the
 * cached user, so without this the admin panel would silently leave
 * them one refresh behind their own permissions.
 *
 * Applied to create / assign / unassign / archive / reactivate, and NOT
 * to useUpdateUnit — renaming a unit or moving its start date cannot
 * change who holds it, and firing a request that can never change
 * anything is exactly the dead call this project keeps finding.
 */
function useHoldingRefresh() {
  const { refreshUser } = useAuth();
  return refreshUser;
}

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
  const refreshHolding = useHoldingRefresh();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: CreateUnitRequest) => unitService.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: KEY });
      void refreshHolding();
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
  const refreshHolding = useHoldingRefresh();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => unitService.archive(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: KEY });
      void refreshHolding();
      toast.success("Unit archived");
    },
    onError: (error) => toast.error(getErrorMessage(error)),
  });
}

export function useReactivateUnit() {
  const refreshHolding = useHoldingRefresh();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => unitService.reactivate(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: KEY });
      void refreshHolding();
      toast.success("Unit reactivated");
    },
    onError: (error) => toast.error(getErrorMessage(error)),
  });
}

export function useAssignLecturer() {
  const refreshHolding = useHoldingRefresh();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, lecturerId }: { id: number; lecturerId: number }) =>
      unitService.assignLecturer(id, lecturerId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: KEY });
      void refreshHolding();
      toast.success("Unit assigned");
    },
    onError: (error) => toast.error(getErrorMessage(error)),
  });
}

export function useUnassignLecturer() {
  const refreshHolding = useHoldingRefresh();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => unitService.unassignLecturer(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: KEY });
      void refreshHolding();
      toast.success("Unit unassigned");
    },
    onError: (error) => toast.error(getErrorMessage(error)),
  });
}