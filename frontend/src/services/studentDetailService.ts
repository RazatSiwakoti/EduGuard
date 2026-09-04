import api from "./api";
import type {
  StudentDetailResponse,
  StudentNoteDetail,
  StudentReviewSubmit,
  StudentEditPayload,
} from "../types/studentDetail";

/**
 * The per-student card endpoints (Phase 7.6b).
 *
 * `unitId` is a required argument on both calls, not an optional one.
 * Risk is computed per unit, so a student enrolled in two of a
 * lecturer's units has two different verdicts and there is no such
 * thing as "their" risk. Making it optional would invite a caller to
 * omit it and force the backend to pick one arbitrarily.
 */
export const studentDetailService = {
  get: async (
    studentId: number,
    unitId: number,
    checkpointWeek = 8,
  ): Promise<StudentDetailResponse> => {
    const res = await api.get<StudentDetailResponse>(
      `/lecturer/students/${studentId}`,
      { params: { unit_id: unitId, checkpoint_week: checkpointWeek } },
    );
    return res.data;
  },

  /**
   * Saves the lecturer's notes. PUT because it is idempotent — one note
   * per lecturer per student per unit, replaced wholesale each time.
   */
  saveNote: async (
    studentId: number,
    unitId: number,
    body: string,
  ): Promise<StudentNoteDetail> => {
    const res = await api.put<StudentNoteDetail>(
      `/lecturer/students/${studentId}/note`,
      { body },
      { params: { unit_id: unitId } },
    );
    return res.data;
  },

  /**
   * Records a decision on an engine disagreement.
   *
   * SENDS NO VERDICT ID. The server resolves the verdict from
   * (student, unit, checkpoint), because the id this page is holding
   * can be stale — a colleague clicking "Run Analysis" while the card
   * is open supersedes it, and the decision would land on a row nothing
   * reads.
   *
   * POST, not PATCH: reviews are append-only, so submitting again
   * records a NEW decision superseding the last rather than editing it.
   * Returns the whole refreshed card payload in one round trip.
   */
  submitReview: async (
    studentId: number,
    unitId: number,
    payload: StudentReviewSubmit,
    checkpointWeek = 8,
  ): Promise<StudentDetailResponse> => {
    const res = await api.post<StudentDetailResponse>(
      `/lecturer/students/${studentId}/review`,
      payload,
      { params: { unit_id: unitId, checkpoint_week: checkpointWeek } },
    );
    return res.data;
  },

  updateStudent: async (studentId: number, unitId: number, payload: StudentEditPayload) => {
    const res = await api.patch(`/lecturer/students/${studentId}`, payload, {
      params: { unit_id: unitId },
    });
    return res.data;
  },

  deleteStudent: async (studentId: number, unitId: number) => {
    await api.delete(`/lecturer/students/${studentId}`, { params: { unit_id: unitId } });
  },
};