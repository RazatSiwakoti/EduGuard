import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { alertService } from "../services/alertService";
import type { AlertStatus, SendRequest, TemplateSave } from "../types/alerts";

const SUMMARY_KEY = ["lecturer-alert-summary"];
const QUEUE_KEY = ["lecturer-alert-queue"];
const LOG_KEY = ["lecturer-alert-log"];
const TEMPLATES_KEY = ["lecturer-alert-templates"];
const PLACEHOLDERS_KEY = ["lecturer-alert-placeholders"];

function invalidateAlertViews(queryClient: ReturnType<typeof useQueryClient>) {
  queryClient.invalidateQueries({ queryKey: SUMMARY_KEY });
  queryClient.invalidateQueries({ queryKey: QUEUE_KEY });
  queryClient.invalidateQueries({ queryKey: LOG_KEY });
}

export function useAlertSummary() { return useQuery({ queryKey: SUMMARY_KEY, queryFn: alertService.getSummary, staleTime: 15_000 }); }
export function useAlertQueue(unitId: number | null) { return useQuery({ queryKey: [...QUEUE_KEY, unitId], queryFn: () => alertService.getQueue(unitId), staleTime: 15_000 }); }
export function useAlertLog(params: { status: AlertStatus | null; search: string; page: number }) {
  return useQuery({ queryKey: [...LOG_KEY, params.status, params.search, params.page], queryFn: () => alertService.getLog({ status: params.status, search: params.search, page: params.page }), staleTime: 15_000, placeholderData: (previous) => previous });
}
export function useTemplates() { return useQuery({ queryKey: TEMPLATES_KEY, queryFn: alertService.getTemplates, staleTime: 60_000 }); }
export function usePlaceholders() { return useQuery({ queryKey: PLACEHOLDERS_KEY, queryFn: alertService.getPlaceholders, staleTime: Infinity }); }

export function useSendAlert() {
  const queryClient = useQueryClient();
  return useMutation({ mutationFn: (payload: SendRequest) => alertService.send(payload), onSuccess: () => invalidateAlertViews(queryClient) });
}
export function useSendBulk() {
  const queryClient = useQueryClient();
  return useMutation({ mutationFn: (items: SendRequest[]) => alertService.sendBulk(items), onSuccess: () => invalidateAlertViews(queryClient) });
}
export function useRunSweep() {
  const queryClient = useQueryClient();
  return useMutation({ mutationFn: alertService.runSweep, onSuccess: () => invalidateAlertViews(queryClient) });
}
export function useSaveTemplate() {
  const queryClient = useQueryClient();
  return useMutation({ mutationFn: ({ id, payload }: { id: number | null; payload: TemplateSave }) => id === null ? alertService.createTemplate(payload) : alertService.updateTemplate(id, payload), onSuccess: () => queryClient.invalidateQueries({ queryKey: TEMPLATES_KEY }) });
}
export function useDeleteTemplate() {
  const queryClient = useQueryClient();
  return useMutation({ mutationFn: (id: number) => alertService.deleteTemplate(id), onSuccess: () => queryClient.invalidateQueries({ queryKey: TEMPLATES_KEY }) });
}
