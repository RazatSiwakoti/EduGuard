import api from "./api";
import type {
  NotificationFeed,
  NotificationKindOption,
  NotificationKind,
} from "../types/notifications";

interface FeedOptions {
  limit?: number;
  kind?: NotificationKind;
}

export const notificationService = {
  async getFeed({ limit = 6, kind }: FeedOptions = {}): Promise<NotificationFeed> {
    const response = await api.get<NotificationFeed>("/notifications", {
      params: {
        limit,
        kind: kind ?? undefined,
      },
    });
    return response.data;
  },

  async markSeen(): Promise<void> {
    await api.post("/notifications/seen");
  },

  async getKinds(): Promise<NotificationKindOption[]> {
    const response = await api.get<NotificationKindOption[]>("/notifications/kinds");
    return response.data;
  },
};

export type { FeedOptions };
