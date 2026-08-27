import api from "./api";
import type {
  AlertLogPage, AlertPreview, AlertQueue, AlertStatus, AlertSummary,
  EmailTemplate, Placeholder, SendRequest, SendResult, TemplateSave,
} from "../types/alerts";

export const alertService = {
  getSummary: async (): Promise<AlertSummary> => (await api.get("/lecturer/alerts/summary")).data,
  getQueue: async (unitId?: number | null): Promise<AlertQueue> => (await api.get("/lecturer/alerts/queue", { params: unitId ? { unit_id: unitId } : undefined })).data,
  getLog: async (params: { status?: AlertStatus | null; search?: string; page?: number; pageSize?: number }): Promise<AlertLogPage> => (await api.get("/lecturer/alerts/log", { params: { status: params.status ?? undefined, search: params.search?.trim() || undefined, page: params.page ?? 1, page_size: params.pageSize ?? 20 } })).data,
  preview: async (payload: SendRequest): Promise<AlertPreview> => (await api.post("/lecturer/alerts/preview", payload)).data,
  send: async (payload: SendRequest): Promise<SendResult> => (await api.post("/lecturer/alerts/send", payload)).data,
  sendBulk: async (items: SendRequest[]): Promise<SendResult> => (await api.post("/lecturer/alerts/send-bulk", { items })).data,
  runSweep: async (): Promise<SendResult> => (await api.post("/lecturer/alerts/run-sweep")).data,
  getTemplates: async (): Promise<EmailTemplate[]> => (await api.get("/lecturer/alerts/templates")).data,
  getPlaceholders: async (): Promise<Placeholder[]> => (await api.get("/lecturer/alerts/placeholders")).data,
  createTemplate: async (payload: TemplateSave): Promise<EmailTemplate> => (await api.post("/lecturer/alerts/templates", payload)).data,
  updateTemplate: async (id: number, payload: TemplateSave): Promise<EmailTemplate> => (await api.put(`/lecturer/alerts/templates/${id}`, payload)).data,
  deleteTemplate: async (id: number): Promise<void> => { await api.delete(`/lecturer/alerts/templates/${id}`); },
};
