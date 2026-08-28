import api from "./api";
import type {
  UnitShape,
  UnitShapeInput,
  UnlockPreview,
  UnlockResult,
} from "../types/unitShape";

/**
 * The coordinator's unit-composition API.
 *
 * TWO PREFIXES, ON PURPOSE — do not "tidy" them into one.
 *
 *   /admin/units/{id}/criteria    the SHAPE  (T2) — admin only
 *   /units/{id}/criteria/...      the LOCK   (T1) — lock-state is open
 *                                 to the assigned lecturer, unlock and
 *                                 unlock-preview are admin only
 *
 * They live on different routers because they answer different
 * questions, and the lock endpoints are declared BEFORE `/{criteria_id}`
 * in the backend router: that path parameter is typed `int`, so a
 * literal segment reaching it first returns 422 about an invalid
 * integer rather than falling through. Nothing here can fix that from
 * the client side, which is why it is written down.
 */

const SHAPE_BASE = (unitId: number) => `/admin/units/${unitId}/criteria`;
const LOCK_BASE = (unitId: number) => `/units/${unitId}/criteria`;

export const unitShapeService = {
  /**
   * The whole shape AND the lock state in one request.
   *
   * Deliberately one call. The form cannot render a single field
   * correctly without both — a disabled input and an editable one are
   * not the same screen, and a first paint that is wrong is worse than
   * one that is slow.
   */
  get: async (unitId: number): Promise<UnitShape> => {
    const res = await api.get<UnitShape>(SHAPE_BASE(unitId));
    return res.data;
  },

  /**
   * Replace the unit's assessments and tutorial setting.
   *
   * Whole-object replace: every composition rule is about the shape as
   * a whole (three items, one quiz cap, one 100% budget), so swapping a
   * 40% assignment for a 50% one is legal as one act and illegal in
   * either order as two.
   *
   * Three refusals, three status codes — the caller branches on the
   * code, never on the English message:
   *   400  the shape breaks a composition rule  -> message under a field
   *   409  the unit's shape is locked           -> the unlock dialog
   *   422  the payload is malformed             -> a bug, not a typo
   */
  replace: async (unitId: number, body: UnitShapeInput): Promise<UnitShape> => {
    const res = await api.put<UnitShape>(SHAPE_BASE(unitId), body);
    return res.data;
  },

  /** What an unlock will cost, fetched BEFORE the confirmation is asked for. */
  unlockPreview: async (unitId: number): Promise<UnlockPreview> => {
    const res = await api.get<UnlockPreview>(`${LOCK_BASE(unitId)}/unlock-preview`);
    return res.data;
  },

  /**
   * Open a one-shot edit window. The typed unit code is the
   * confirmation, and it is re-checked server-side — a confirmation
   * validated only in the dialog protects against a mis-click and
   * nothing else.
   */
  unlock: async (unitId: number, unitCode: string): Promise<UnlockResult> => {
    const res = await api.post<UnlockResult>(`${LOCK_BASE(unitId)}/unlock`, {
      unit_code: unitCode,
    });
    return res.data;
  },
};