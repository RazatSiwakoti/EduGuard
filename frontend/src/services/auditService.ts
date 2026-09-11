import api from "./api";
import type { AuditAction, AuditEventPage, AuditQuery } from "../types/audit";

export const auditService = {
  getActions: async (): Promise<AuditAction[]> =>
    (await api.get("/admin/audit/actions")).data,

  getEvents: async (query: AuditQuery): Promise<AuditEventPage> =>
    (
      await api.get("/admin/audit", {
        params: {
          action: query.action ?? undefined,
          search: query.search.trim() || undefined,
          days: query.days ?? undefined,
          page: query.page,
          page_size: 25,
        },
      })
    ).data,
};