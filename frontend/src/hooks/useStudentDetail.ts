import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { studentDetailService } from "../services/studentDetailService";
import type {
  StudentCardTarget,
  StudentDetailResponse,
  StudentNoteDetail,
  StudentReviewSubmit,
  StudentEditPayload,
} from "../types/studentDetail";

const KEY = ["lecturer-student-detail"];

/**
 * Loads one student's full picture for the card.
 *
 * `target` is null while no card is open, and `enabled` switches the
 * query off in that state — otherwise React Query would fire a request
 * for student `undefined` the moment the page mounts.
 *
 * The query key carries BOTH ids, so opening the same person's card in
 * a different unit is a different cache entry rather than stale data
 * from the other unit's verdict.
 *
 * staleTime matches the dashboard's: risk only changes when a lecturer
 * uploads data or re-runs the analysis, never continuously.
 */
export function useStudentDetail(target: StudentCardTarget | null, checkpointWeek = 8) {
  return useQuery({
    queryKey: [...KEY, target?.studentId, target?.unitId, checkpointWeek],
    queryFn: () =>
      studentDetailService.get(target!.studentId, target!.unitId, checkpointWeek),
    enabled: target !== null,
    staleTime: 60_000,
    refetchOnWindowFocus: false,
  });
}

/**
 * Saves the lecturer's notes.
 *
 * On success it writes the returned note straight into the cached
 * detail entry rather than invalidating it. Invalidating would refetch
 * the whole student — including both engines' scores and every
 * criterion — to reflect a change to one text field, and the card would
 * flash a loading state over data that did not change.
 */
export function useSaveStudentNote(target: StudentCardTarget | null, checkpointWeek = 8) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (body: string) =>
      studentDetailService.saveNote(target!.studentId, target!.unitId, body),

    onSuccess: (note: StudentNoteDetail) => {
      queryClient.setQueryData(
        [...KEY, target?.studentId, target?.unitId, checkpointWeek],
        (current: unknown) =>
          current && typeof current === "object"
            ? { ...(current as object), note }
            : current,
      );
    },
  });
}


/**
 * Records a lecturer's decision on an engine disagreement.
 *
 * Two cache writes on success, and both matter:
 *
 *  1. The detail entry is replaced with the payload the server returned,
 *     so the resolved tier, the new history row and the cleared prompt
 *     all render from one round trip.
 *  2. The DASHBOARD query is invalidated. The Students page's risk tabs
 *     are computed from that payload, so without this the "Needs Review"
 *     count would still say 3 after the lecturer had just cleared one —
 *     and they would reasonably conclude the decision had not saved.
 */
export function useSubmitReview(target: StudentCardTarget | null, checkpointWeek = 8) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: StudentReviewSubmit) =>
      studentDetailService.submitReview(
        target!.studentId,
        target!.unitId,
        payload,
        checkpointWeek,
      ),

    onSuccess: (detail: StudentDetailResponse) => {
      queryClient.setQueryData(
        [...KEY, target?.studentId, target?.unitId, checkpointWeek],
        detail,
      );
      queryClient.invalidateQueries({ queryKey: ["lecturer-dashboard"] });
    },
  });
}

export function useSubmitRowReview(studentId: number, unitId: number, checkpointWeek = 8) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: StudentReviewSubmit) =>
      studentDetailService.submitReview(studentId, unitId, payload, checkpointWeek),
    onSuccess: (detail) => {
      queryClient.setQueryData([...KEY, studentId, unitId, checkpointWeek], detail);
      queryClient.invalidateQueries({ queryKey: ["lecturer-dashboard"] });
      queryClient.invalidateQueries({ queryKey: ["student-detail", studentId, unitId] });
      queryClient.invalidateQueries({ queryKey: ["lecturer-alert-queue"] });
    },
  });
}

export function useUpdateStudent() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      studentId,
      unitId,
      payload,
    }: { studentId: number; unitId: number; payload: StudentEditPayload }) =>
      studentDetailService.updateStudent(studentId, unitId, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["lecturer-dashboard"] });
    },
  });
}

export function useDeleteStudent() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ studentId, unitId }: { studentId: number; unitId: number }) =>
      studentDetailService.deleteStudent(studentId, unitId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["lecturer-dashboard"] });
    },
  });
}