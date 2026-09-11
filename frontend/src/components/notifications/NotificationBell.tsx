import * as DropdownMenu from "@radix-ui/react-dropdown-menu";
import { Bell } from "lucide-react";
import { Link } from "react-router-dom";
import { useMarkNotificationsSeen, useNotifications } from "../../hooks/useNotifications";
import NotificationRow from "./NotificationRow";

export default function NotificationBell() {
  const feed = useNotifications();
  const markSeen = useMarkNotificationsSeen();
  const unreadCount = feed.data?.unread_count ?? 0;

  return (
    <DropdownMenu.Root onOpenChange={(open) => open && markSeen.mutate()}>
      <DropdownMenu.Trigger asChild>
        <button
          type="button"
          className="relative rounded-full p-2 text-stone-500 transition hover:bg-stone-100"
          aria-label={unreadCount ? `${unreadCount} unread notifications` : "Notifications"}
        >
          <Bell className="h-5 w-5" />
          {unreadCount > 0 && (
            <span className="absolute -right-1 -top-1 min-w-4 rounded-full bg-red-500 px-1 text-center text-[0.625rem] font-semibold leading-4 text-white">
              {unreadCount > 9 ? "9+" : unreadCount}
            </span>
          )}
        </button>
      </DropdownMenu.Trigger>
      <DropdownMenu.Portal>
        <DropdownMenu.Content
          align="end"
          sideOffset={8}
          className="w-80 max-h-[26rem] overflow-y-auto rounded-md border border-stone-200 bg-white shadow-lg"
        >
          <div className="sticky top-0 z-10 flex items-center justify-between border-b border-stone-200 bg-white px-4 py-3">
            <h2 className="text-sm font-semibold text-stone-900">Notifications</h2>
            <button
              type="button"
              onClick={() => markSeen.mutate()}
              className="text-xs font-medium text-brand hover:underline"
            >
              Mark all read
            </button>
          </div>
          {feed.isLoading ? (
            <p className="px-4 py-8 text-center text-sm text-stone-500">Loading notifications…</p>
          ) : feed.isError ? (
            <p className="px-4 py-8 text-center text-sm text-stone-500">Couldn&apos;t load notifications.</p>
          ) : feed.data?.items.length ? (
            feed.data.items.map((item) => <NotificationRow key={item.id} item={item} />)
          ) : (
            <p className="px-4 py-8 text-center text-sm text-stone-500">You&apos;re all caught up.</p>
          )}
          <div className="sticky bottom-0 border-t border-stone-200 bg-white px-4 py-3 text-center">
            <Link to="/notifications" className="text-xs font-medium text-brand hover:underline">
              See all activity
            </Link>
          </div>
        </DropdownMenu.Content>
      </DropdownMenu.Portal>
    </DropdownMenu.Root>
  );
}
