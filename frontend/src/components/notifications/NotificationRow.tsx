import {
  CircleAlert,
  MailOpen,
  MailX,
  Scale,
  Send,
  Settings2,
  CalendarClock,
  SlidersHorizontal,
  Upload,
  UserCheck,
  UserPlus,
  type LucideIcon,
} from "lucide-react";
import { Link } from "react-router-dom";
import { useBucketStyles } from "../dashboard/chartTheme";
import type { NotificationItem } from "../../types/notifications";
import { relativeTime } from "../../utils/relativeTime";

const ICONS: Record<NotificationItem["kind"], LucideIcon> = {
  alert_acknowledged: MailOpen,
  alert_failed: MailX,
  sweep_summary: Send,
  review_pending: Scale,
  missing_data: CircleAlert,
  import_complete: Upload,
  criteria_changed: SlidersHorizontal,
  verdict_overridden: UserCheck,
  unit_unassigned: UserPlus,
  unit_unconfigured: Settings2,
  follow_up_due: CalendarClock,
};

export default function NotificationRow({ item }: { item: NotificationItem }) {
  const styles = useBucketStyles();
  const style = styles[
    item.severity === "critical"
      ? "high_risk"
      : item.severity === "warning"
        ? "low_risk"
        : item.severity === "success"
          ? "safe"
          : "not_analysed"
  ];
  const Icon = ICONS[item.kind];
  const content = (
    <>
      <span className={`mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full ${style.pill}`}>
        <Icon className="h-4 w-4" aria-hidden="true" />
      </span>
      <span className="min-w-0 flex-1">
        <span className="block text-sm font-medium text-stone-800">{item.title}</span>
        {item.detail && <span className="mt-0.5 block truncate text-xs text-stone-500">{item.detail}</span>}
        <span className="mt-1 block text-[0.625rem] text-stone-400">{relativeTime(item.occurred_at)}</span>
      </span>
    </>
  );
  const className = `flex gap-3 border-b border-stone-100 px-4 py-3 text-left last:border-b-0 ${
    item.unread ? "border-l-2 border-l-brand bg-brand-wash/40" : "border-l-2 border-l-transparent"
  }`;

  return item.link ? (
    <Link to={item.link} className={`${className} hover:bg-stone-50`}>
      {content}
    </Link>
  ) : (
    <div className={className}>{content}</div>
  );
}
