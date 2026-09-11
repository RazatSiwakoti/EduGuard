import api from "./api";
import type {
  UnitShape,
  UnitShapeInput,
  UnlockPreview,
  UnlockResult,
} from "../types/unitShape";

const SHAPE_BASE = (unitId: number) => `/admin/units/${unitId}/criteria`;
const LOCK_BASE = (unitId: number) => `/units/${unitId}/criteria`;

export const unitShapeService = {
  get: async (unitId: number): Promise<UnitShape> => {
    const res = await api.get<UnitShape>(SHAPE_BASE(unitId));
    return res.data;
  },
  replace: async (unitId: number, body: UnitShapeInput): Promise<UnitShape> => {
    const res = await api.put<UnitShape>(SHAPE_BASE(unitId), body);
    return res.data;
  },
  unlockPreview: async (unitId: number): Promise<UnlockPreview> => {
    const res = await api.get<UnlockPreview>(`${LOCK_BASE(unitId)}/unlock-preview`);
    return res.data;
  },
  unlock: async (unitId: number, unitCode: string): Promise<UnlockResult> => {
    const res = await api.post<UnlockResult>(`${LOCK_BASE(unitId)}/unlock`, {
      unit_code: unitCode,
    });
    return res.data;
  },
};
