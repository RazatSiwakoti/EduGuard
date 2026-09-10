import { useMemo, useState } from "react";
import NotificationRow from "../components/notifications/NotificationRow";
import { useNotificationKinds, useNotifications } from "../hooks/useNotifications";
import type { NotificationKind, NotificationItem } from "../types/notifications";

function groupLabel(value: string): string {
  const date = new Date(value);
  const today = new Date();
  const startOfToday = new Date(today.getFullYear(), today.getMonth(), today.getDate());
  const startOfDate = new Date(date.getFullYear(), date.getMonth(), date.getDate());
  const daysAgo = Math.round((startOfToday.getTime() - startOfDate.getTime()) / 86400000);
  if (daysAgo === 0) return "Today";
  if (daysAgo === 1) return "Yesterday";
  return "Earlier";
}

export default function NotificationsPage() {
  const [kind, setKind] = useState<NotificationKind | undefined>();
  const kinds = useNotificationKinds();
  const feed = useNotifications(50, kind);
  const groups = useMemo(() => {
    const grouped = new Map<string, NotificationItem[]>();
    for (const item of feed.data?.items ?? []) {
      const label = groupLabel(item.occurred_at);
      const current = grouped.get(label) ?? [];
      current.push(item);
      grouped.set(label, current);
    }
    return ["Today", "Yesterday", "Earlier"]
      .filter((label) => grouped.has(label))
      .map((label) => ({ label, items: grouped.get(label) ?? [] }));
  }, [feed.data?.items]);

  return (
    <div className="px-6 py-8">
      <div className="mx-auto max-w-3xl">
        <h1 className="text-xl font-semibold text-stone-900">Activity</h1>
        <p className="mt-1 text-sm text-stone-500">Recent activity relevant to your account.</p>

        <div className="mt-5 flex flex-wrap gap-2" aria-label="Filter notifications">
          <button
            type="button"
            onClick={() => setKind(undefined)}
            className={`rounded-full border px-3 py-1.5 text-xs font-medium ${kind === undefined ? "border-stone-900 bg-stone-900 text-white" : "border-stone-200 text-stone-600 hover:bg-stone-50"}`}
          >
            All
          </button>
          {kinds.data?.map((option) => (
            <button
              key={option.key}
              type="button"
              onClick={() => setKind(option.key)}
              className={`rounded-full border px-3 py-1.5 text-xs font-medium ${kind === option.key ? "border-stone-900 bg-stone-900 text-white" : "border-stone-200 text-stone-600 hover:bg-stone-50"}`}
            >
              {option.label}
            </button>
          ))}
        </div>

        <section className="mt-6 rounded-lg border border-stone-200 bg-white">
          {feed.isLoading ? (
            <p className="p-8 text-center text-sm text-stone-500">Loading activity…</p>
          ) : feed.isError ? (
            <p className="p-8 text-center text-sm text-stone-500">Couldn&apos;t load activity.</p>
          ) : groups.length ? (
            groups.map((group) => (
              <div key={group.label}>
                <h2 className="border-b border-stone-100 bg-stone-50 px-4 py-2 text-xs font-semibold uppercase tracking-wide text-stone-500">
                  {group.label}
                </h2>
                {group.items.map((item) => <NotificationRow key={item.id} item={item} />)}
              </div>
            ))
          ) : (
            <p className="p-8 text-center text-sm text-stone-500">No activity matches this filter.</p>
          )}
        </section>
      </div>
    </div>
  );
}
